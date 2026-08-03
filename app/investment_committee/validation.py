"""Deterministic post-run validation and recommendation enforcement."""

from __future__ import annotations

import re
from decimal import Decimal

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
    DueDiligencePriority,
    DueDiligenceTiming,
    InvestmentCommitteeOutput,
    InvestmentRecommendation,
    MissingInformationMateriality,
    RecommendationPolicyDecision,
    RequiredCondition,
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
_GENERIC_BOILERPLATE_PATTERNS = (
    re.compile(r"(?is)\bdo more research\b"),
    re.compile(r"(?is)\bfurther due diligence\b"),
    re.compile(r"(?is)\bconsult (?:a|an|the)? ?(?:expert|professional|specialist)\b"),
    re.compile(r"(?is)\breview all documents\b"),
    re.compile(r"(?is)\bverify everything\b"),
    re.compile(r"(?is)\bmake sure everything\b"),
    re.compile(r"(?is)\bperform (?:general|standard|basic) due diligence\b"),
)
_MEASURABLE_CUE_PATTERN = re.compile(
    r"(?is)(\d|at least|at most|no more than|no less than|within|below|above|under|over|"
    r"maintain|remain|hold|threshold|verified|documented|resolved|confirm)"
)
_STOPWORDS = {
    "about",
    "above",
    "across",
    "after",
    "against",
    "along",
    "also",
    "among",
    "around",
    "because",
    "before",
    "below",
    "between",
    "buyer",
    "cash",
    "closing",
    "could",
    "current",
    "during",
    "field",
    "from",
    "have",
    "into",
    "listing",
    "make",
    "more",
    "must",
    "need",
    "needs",
    "offer",
    "only",
    "period",
    "price",
    "property",
    "remain",
    "seller",
    "should",
    "than",
    "that",
    "their",
    "them",
    "there",
    "these",
    "this",
    "those",
    "through",
    "under",
    "verified",
    "with",
}


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


def _text_tokens(*parts: str | None) -> set[str]:
    tokens: set[str] = set()
    for part in parts:
        if not part:
            continue
        for token in re.findall(r"[a-z0-9]+", part.lower()):
            if len(token) < 4 or token in _STOPWORDS:
                continue
            tokens.add(token)
    return tokens


def _has_meaningful_overlap(text: str, anchors: list[str]) -> bool:
    candidate_tokens = _text_tokens(text)
    if not candidate_tokens:
        return False
    return any(candidate_tokens & _text_tokens(anchor) for anchor in anchors)


def _contains_generic_boilerplate(*parts: str | None) -> bool:
    for part in parts:
        if not part:
            continue
        for pattern in _GENERIC_BOILERPLATE_PATTERNS:
            if pattern.search(part):
                return True
    return False


def _allowed_monetary_values(prepared_input: CommitteeModelInput) -> set[Decimal]:
    values: set[Decimal] = set()

    def collect(value: str | int | Decimal | bool | None) -> None:
        if isinstance(value, bool) or value is None:
            return
        if isinstance(value, Decimal):
            values.add(value)
            return
        if isinstance(value, int):
            values.add(Decimal(value))

    for field in prepared_input.property_fields:
        collect(field.final_value)
        collect(field.extracted_value)
    for assumption in prepared_input.assumptions:
        collect(assumption.value)
    for metric in prepared_input.underwriting_metrics:
        collect(metric.value)
    for metric in prepared_input.maximum_offer:
        collect(metric.value)
    for scenario in prepared_input.scenarios:
        for metric in scenario.metrics:
            collect(metric.value)
    for stress_test in prepared_input.stress_tests:
        for assumption in stress_test.changed_assumptions:
            collect(assumption.value)
        for metric in stress_test.metrics:
            collect(metric.value)
    return values


def _topic_anchors(
    prepared_input: CommitteeModelInput,
    output: InvestmentCommitteeOutput,
    policy: RecommendationPolicyDecision,
) -> list[str]:
    anchors: list[str] = []
    anchors.extend(field.field_name for field in prepared_input.property_fields)
    anchors.extend(assumption.name for assumption in prepared_input.assumptions)
    anchors.extend(metric.metric_name for metric in prepared_input.underwriting_metrics)
    anchors.extend(metric.metric_name for metric in prepared_input.maximum_offer)
    anchors.extend(item.item for item in output.missing_information)
    anchors.extend(item.item for item in policy.critical_missing_items)
    anchors.extend(item.reason_needed for item in output.missing_information)
    anchors.extend(finding.title for finding in prepared_input.research.consolidated_findings)
    anchors.extend(finding.finding for finding in prepared_input.research.consolidated_findings)
    for finding in prepared_input.research.consolidated_findings:
        anchors.extend(finding.affected_fields)
        anchors.extend(finding.missing_information)
    anchors.extend(conflict.field_or_topic for conflict in prepared_input.research.conflicts)
    anchors.extend(prepared_input.research.due_diligence_questions)
    anchors.extend(risk.title for risk in output.material_risks)
    anchors.extend(risk.category for risk in output.material_risks)
    anchors.extend(risk.explanation for risk in output.material_risks)
    anchors.extend(condition.condition for condition in output.what_must_be_true)
    anchors.extend(condition.threshold_or_requirement for condition in output.what_must_be_true)
    return [anchor for anchor in anchors if anchor]


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


def validate_due_diligence_specificity(
    output: InvestmentCommitteeOutput,
    policy: RecommendationPolicyDecision,
    prepared_input: CommitteeModelInput,
) -> None:
    anchors = _topic_anchors(prepared_input, output, policy)
    critical_missing = [item.item for item in policy.critical_missing_items]
    unresolved_topics = [
        conflict.field_or_topic
        for conflict in prepared_input.research.conflicts
        if conflict.resolution_status != ConflictResolutionStatus.RESOLVED_DETERMINISTICALLY
    ]
    for item in output.due_diligence_checklist:
        if _contains_generic_boilerplate(item.action, item.reason):
            raise CommitteeOutputValidationError(
                message="Due-diligence items must be property-specific, not boilerplate."
            )
        if not _has_meaningful_overlap(f"{item.action} {item.reason}", anchors):
            raise CommitteeOutputValidationError(
                message="Due-diligence items must tie to actual risks or missing information."
            )
        if (
            _has_meaningful_overlap(f"{item.action} {item.reason}", critical_missing)
            or _has_meaningful_overlap(f"{item.action} {item.reason}", unresolved_topics)
        ) and item.priority not in {
            DueDiligencePriority.HIGH,
            DueDiligencePriority.CRITICAL,
        }:
            raise CommitteeOutputValidationError(
                message="Decision-critical diligence items must have high or critical priority."
            )
        if (
            _has_meaningful_overlap(f"{item.action} {item.reason}", critical_missing)
            or _has_meaningful_overlap(f"{item.action} {item.reason}", unresolved_topics)
        ) and item.timing not in {
            DueDiligenceTiming.BEFORE_OFFER,
            DueDiligenceTiming.DURING_OPTION_PERIOD,
        }:
            raise CommitteeOutputValidationError(
                message=(
                    "Decision-critical diligence items must occur before offer or during option."
                )
            )


def validate_negotiation_points(
    output: InvestmentCommitteeOutput,
    policy: RecommendationPolicyDecision,
    prepared_input: CommitteeModelInput,
) -> None:
    anchors = _topic_anchors(prepared_input, output, policy)
    allowed_values = _allowed_monetary_values(prepared_input)
    for point in output.negotiation_points:
        if _contains_generic_boilerplate(point.issue, point.negotiation_request, point.rationale):
            raise CommitteeOutputValidationError(
                message="Negotiation points must be specific to the property and evidence."
            )
        if not _has_meaningful_overlap(
            f"{point.issue} {point.negotiation_request} {point.rationale}",
            anchors,
        ):
            raise CommitteeOutputValidationError(
                message="Negotiation points must tie to actual supported issues."
            )
        if point.estimated_value is not None and point.estimated_value not in allowed_values:
            raise UnsupportedOfferValueError(
                message="Negotiation values must come from existing deterministic data."
            )


def _validate_required_condition(condition: RequiredCondition, anchors: list[str]) -> None:
    if _contains_generic_boilerplate(
        condition.condition,
        condition.threshold_or_requirement,
        condition.consequence_if_false,
    ):
        raise CommitteeOutputValidationError(
            message="What-must-be-true conditions must be property-specific and non-generic."
        )
    if not _has_meaningful_overlap(
        (
            f"{condition.condition} {condition.threshold_or_requirement} "
            f"{condition.consequence_if_false}"
        ),
        anchors,
    ):
        raise CommitteeOutputValidationError(
            message="What-must-be-true conditions must tie to supported property facts or metrics."
        )
    if not _MEASURABLE_CUE_PATTERN.search(condition.threshold_or_requirement):
        raise CommitteeOutputValidationError(
            message="What-must-be-true conditions must be measurable when possible."
        )


def validate_conditions(
    output: InvestmentCommitteeOutput,
    policy: RecommendationPolicyDecision,
    prepared_input: CommitteeModelInput,
) -> None:
    anchors = _topic_anchors(prepared_input, output, policy)
    condition_anchors = [condition.condition for condition in output.what_must_be_true]
    condition_anchors.extend(
        condition.threshold_or_requirement for condition in output.what_must_be_true
    )
    for condition in output.what_must_be_true:
        _validate_required_condition(condition, anchors)
    for item in output.conditions_before_offer:
        if _contains_generic_boilerplate(item):
            raise CommitteeOutputValidationError(
                message="Conditions before offer must be property-specific."
            )
        if not _has_meaningful_overlap(item, anchors + condition_anchors):
            raise CommitteeOutputValidationError(
                message="Conditions before offer must tie to supported issues or thresholds."
            )
        if not _MEASURABLE_CUE_PATTERN.search(item):
            raise CommitteeOutputValidationError(
                message="Conditions before offer must be measurable where possible."
            )
    for item in output.conditions_before_closing:
        if _contains_generic_boilerplate(item):
            raise CommitteeOutputValidationError(
                message="Conditions before closing must be property-specific."
            )
        if not _has_meaningful_overlap(item, anchors + condition_anchors):
            raise CommitteeOutputValidationError(
                message="Conditions before closing must tie to supported issues or thresholds."
            )
        if not _MEASURABLE_CUE_PATTERN.search(item):
            raise CommitteeOutputValidationError(
                message="Conditions before closing must be measurable where possible."
            )


def validate_missing_information_specificity(output: InvestmentCommitteeOutput) -> None:
    for item in output.missing_information:
        if _contains_generic_boilerplate(item.reason_needed, item.decision_impact):
            raise CommitteeOutputValidationError(
                message="Missing-information impact must be specific to the property decision."
            )
        if not _has_meaningful_overlap(
            f"{item.reason_needed} {item.decision_impact}",
            [item.item],
        ):
            raise CommitteeOutputValidationError(
                message="Missing-information impact must reference the underlying missing item."
            )


def validate_recommendation_specificity(output: InvestmentCommitteeOutput) -> None:
    if _contains_generic_boilerplate(
        output.recommendation_summary,
        output.investment_thesis,
        output.strongest_upside,
        output.strongest_downside,
    ):
        raise CommitteeOutputValidationError(
            message="Committee recommendation language must not be generic boilerplate."
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
    validate_missing_information_specificity(output)
    validate_due_diligence(output, policy, prepared_input)
    validate_due_diligence_specificity(output, policy, prepared_input)
    validate_negotiation_points(output, policy, prepared_input)
    validate_conditions(output, policy, prepared_input)
    validate_reasons(output)
    validate_recommendation_specificity(output)
    validate_prohibited_language(output)
    return output
