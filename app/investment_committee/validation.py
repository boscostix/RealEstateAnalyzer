"""Deterministic post-run validation and recommendation enforcement."""

from __future__ import annotations

import re

from app.agent_research.models import (
    ConflictMateriality,
    ConflictResolutionStatus,
    EvidenceReference,
)
from app.investment_committee.exceptions import (
    CommitteeOutputValidationError,
    RecommendationPolicyViolationError,
    UnsupportedOfferValueError,
)
from app.investment_committee.input_models import CommitteeModelInput
from app.investment_committee.models import (
    InvestmentCommitteeOutput,
    InvestmentRecommendation,
    MissingInformationMateriality,
    RecommendationPolicyDecision,
)
from app.investment_committee.policies import (
    validate_offer_value,
    validate_recommendation,
    validate_recommendation_confidence,
)

_DOWNGRADE_ORDER: tuple[InvestmentRecommendation, ...] = (
    InvestmentRecommendation.INSUFFICIENT_INFORMATION,
    InvestmentRecommendation.PASS,
    InvestmentRecommendation.WATCH,
    InvestmentRecommendation.NEGOTIATE,
    InvestmentRecommendation.BUY_ONLY_BELOW,
    InvestmentRecommendation.BUY,
    InvestmentRecommendation.STRONG_BUY,
)

_PROHIBITED_PATTERNS = (
    re.compile(r"(?is)\bguaranteed?\b|\bno risk\b|\bwill definitely\b"),
    re.compile(r"(?is)\binspection (?:proved|shows|confirmed)\b"),
    re.compile(r"(?is)\blegal advice\b|\btax advice\b|\blending advice\b"),
)


def _allowed_evidence(
    prepared_input: CommitteeModelInput,
) -> set[tuple[str, str, str | None, str | None]]:
    allowed: set[tuple[str, str, str | None, str | None]] = set()

    def collect(references: list[EvidenceReference]) -> None:
        for reference in references:
            allowed.add(
                (
                    reference.source_id,
                    reference.source_type,
                    reference.citation_id,
                    reference.field_path,
                )
            )

    for field in prepared_input.property_fields:
        collect(field.evidence)
    for assumption in prepared_input.assumptions:
        collect(assumption.evidence)
    for metric in prepared_input.underwriting_metrics:
        collect(metric.evidence)
    for metric in prepared_input.maximum_offer:
        collect(metric.evidence)
    for scenario in prepared_input.scenarios:
        for metric in scenario.metrics:
            collect(metric.evidence)
    for stress_test in prepared_input.stress_tests:
        for assumption in stress_test.changed_assumptions:
            collect(assumption.evidence)
        for metric in stress_test.metrics:
            collect(metric.evidence)
    for finding in prepared_input.research.consolidated_findings:
        collect(finding.evidence)
    collect(prepared_input.research.evidence_index)
    return allowed


def validate_evidence_references(
    output: InvestmentCommitteeOutput,
    prepared_input: CommitteeModelInput,
) -> None:
    """Reject references that are not present in the prepared deterministic evidence set."""

    allowed = _allowed_evidence(prepared_input)
    references: list[EvidenceReference] = list(output.evidence_references)
    for reason in output.reasons_to_proceed:
        references.extend(reason.evidence)
    for reason in output.reasons_not_to_proceed:
        references.extend(reason.evidence)
    for assumption in [*output.key_assumptions, *output.fragile_assumptions]:
        references.extend(assumption.evidence)
    for risk in output.material_risks:
        references.extend(risk.evidence)
    for condition in output.what_must_be_true:
        references.extend(condition.evidence)
    for item in output.due_diligence_checklist:
        references.extend(item.evidence)
    for point in output.negotiation_points:
        references.extend(point.evidence)

    for reference in references:
        key = (
            reference.source_id,
            reference.source_type,
            reference.citation_id,
            reference.field_path,
        )
        if key not in allowed:
            raise CommitteeOutputValidationError(
                message="Investment committee output referenced unsupported evidence."
            )


def validate_offer_range(
    output: InvestmentCommitteeOutput,
    policy: RecommendationPolicyDecision,
) -> None:
    if output.supported_offer_low is not None:
        validate_offer_value(output.supported_offer_low, policy.offer_range)
    if output.supported_offer_high is not None:
        validate_offer_value(output.supported_offer_high, policy.offer_range)
    for basis in output.recommended_offer_basis:
        validate_offer_value(basis.value, policy.offer_range)
        if not any(
            candidate.source_metric == basis.source_metric
            and candidate.source_path == basis.source_path
            and candidate.value == basis.value
            for candidate in policy.offer_range.basis
        ):
            raise UnsupportedOfferValueError(
                message="Offer basis must map to an existing deterministic source value."
            )


def validate_metric_preservation(
    output: InvestmentCommitteeOutput,
    prepared_input: CommitteeModelInput,
) -> None:
    asking_price = next(
        (
            field.final_value
            for field in prepared_input.property_fields
            if field.field_name == "asking_price"
        ),
        None,
    )
    if output.asking_price != asking_price:
        raise CommitteeOutputValidationError(
            message="The investment committee cannot change deterministic asking-price values."
        )


def validate_conflict_preservation(
    output: InvestmentCommitteeOutput,
    prepared_input: CommitteeModelInput,
) -> None:
    required_topics = {
        conflict.field_or_topic.lower()
        for conflict in prepared_input.research.conflicts
        if conflict.resolution_status != ConflictResolutionStatus.RESOLVED_DETERMINISTICALLY
        and conflict.materiality == ConflictMateriality.HIGH
    }
    output_topics = {item.strip().lower() for item in output.unresolved_conflicts}
    missing = {topic for topic in required_topics if topic not in output_topics}
    if missing:
        raise CommitteeOutputValidationError(
            message="Unresolved high-materiality conflicts cannot disappear from the output."
        )


def validate_missing_information(
    output: InvestmentCommitteeOutput,
    policy: RecommendationPolicyDecision,
) -> None:
    required_items = {
        item.item.lower()
        for item in policy.critical_missing_items
        if item.materiality == MissingInformationMateriality.DECISION_CRITICAL
    }
    output_items = {item.item.lower() for item in output.missing_information}
    if not required_items.issubset(output_items):
        raise CommitteeOutputValidationError(
            message="Decision-critical missing information cannot disappear from the output."
        )


def validate_due_diligence(
    output: InvestmentCommitteeOutput,
    policy: RecommendationPolicyDecision,
    prepared_input: CommitteeModelInput,
) -> None:
    requires_due_diligence = bool(policy.critical_missing_items) or any(
        conflict.resolution_status != ConflictResolutionStatus.RESOLVED_DETERMINISTICALLY
        for conflict in prepared_input.research.conflicts
    )
    if requires_due_diligence and not output.due_diligence_checklist:
        raise CommitteeOutputValidationError(
            message="Material uncertainty requires at least one due-diligence item."
        )


def validate_reasons(output: InvestmentCommitteeOutput) -> None:
    if not output.reasons_to_proceed or not output.reasons_not_to_proceed:
        raise CommitteeOutputValidationError(
            message="Committee output must include reasons for and reasons against."
        )


def validate_prohibited_language(output: InvestmentCommitteeOutput) -> None:
    texts: list[str] = [
        output.recommendation_summary,
        output.investment_thesis,
        output.strongest_upside,
        output.strongest_downside,
    ]
    texts.extend(reason.explanation for reason in output.reasons_to_proceed)
    texts.extend(reason.explanation for reason in output.reasons_not_to_proceed)
    texts.extend(risk.explanation for risk in output.material_risks)
    texts.extend(item.reason for item in output.due_diligence_checklist)
    for text in texts:
        for pattern in _PROHIBITED_PATTERNS:
            if pattern.search(text):
                raise CommitteeOutputValidationError(
                    message="Committee output contains prohibited recommendation language."
                )


def _downgrade_recommendation(
    output: InvestmentCommitteeOutput,
    policy: RecommendationPolicyDecision,
) -> InvestmentCommitteeOutput:
    """Deterministically downgrade to the most conservative allowed label.

    Priority order is:
    insufficient_information -> pass -> watch -> negotiate -> buy_only_below -> buy -> strong_buy
    """

    for candidate in _DOWNGRADE_ORDER:
        if candidate in policy.allowed_recommendations:
            if candidate == output.recommendation:
                return output
            return output.model_copy(
                update={
                    "recommendation": candidate,
                    "warnings": [
                        *output.warnings,
                        f"recommendation_downgraded:{output.recommendation}->{candidate}",
                    ],
                }
            )
    raise RecommendationPolicyViolationError(
        message="No allowed deterministic recommendation is available for downgrade."
    )


def validate_and_enforce_output(
    output: InvestmentCommitteeOutput,
    *,
    prepared_input: CommitteeModelInput,
) -> InvestmentCommitteeOutput:
    """Validate a committee output and enforce deterministic recommendation policy."""

    policy = prepared_input.policy
    try:
        validate_recommendation(output.recommendation, policy)
    except RecommendationPolicyViolationError:
        output = _downgrade_recommendation(output, policy)

    validate_recommendation_confidence(output, policy)
    validate_offer_range(output, policy)
    validate_metric_preservation(output, prepared_input)
    validate_evidence_references(output, prepared_input)
    validate_conflict_preservation(output, prepared_input)
    validate_missing_information(output, policy)
    validate_due_diligence(output, policy, prepared_input)
    validate_reasons(output)
    validate_prohibited_language(output)
    return output
