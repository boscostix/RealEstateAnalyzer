"""Deterministic policy helpers for investment-committee recommendations."""

from __future__ import annotations

from decimal import Decimal

from app.agent_research.models import ConflictMateriality, ConflictResolutionStatus
from app.investment_committee.exceptions import (
    ConfidencePolicyViolationError,
    RecommendationPolicyViolationError,
    UnsupportedOfferValueError,
)
from app.investment_committee.models import (
    CommitteeMissingItem,
    ConfidencePolicyResult,
    DeterministicOfferRange,
    InvestmentCommitteeInput,
    InvestmentCommitteeOutput,
    InvestmentRecommendation,
    MissingInformationMateriality,
    OfferRangeBasis,
    ReasonImportance,
    RecommendationPolicyDecision,
)

_DECIMAL_ZERO = Decimal("0")
_DECIMAL_ONE = Decimal("1")
_CONFIDENCE_FLOOR = Decimal("0.20")

_MISSING_INFORMATION_RULES: tuple[
    tuple[tuple[str, ...], MissingInformationMateriality, ReasonImportance, bool, str],
    ...,
] = (
    (
        ("expected rent", "market rent", "rent comparable", "rental comp", "rent support"),
        MissingInformationMateriality.DECISION_CRITICAL,
        ReasonImportance.DECISIVE,
        True,
        "The underwriting rent support is too weak to defend a final recommendation.",
    ),
    (
        ("insurance", "insurance quote"),
        MissingInformationMateriality.DECISION_CRITICAL,
        ReasonImportance.HIGH,
        True,
        "Insurance materially affects operating expenses and stress resilience.",
    ),
    (
        ("hoa", "leasing rule", "rental restriction", "lease restriction"),
        MissingInformationMateriality.DECISION_CRITICAL,
        ReasonImportance.HIGH,
        True,
        "HOA or leasing restrictions can block the intended strategy.",
    ),
    (
        ("property tax", "tax estimate", "taxes"),
        MissingInformationMateriality.IMPORTANT,
        ReasonImportance.HIGH,
        False,
        "Taxes materially affect cash flow and offer support.",
    ),
    (
        ("flood", "fema", "flood insurance"),
        MissingInformationMateriality.IMPORTANT,
        ReasonImportance.HIGH,
        False,
        "Flood exposure can materially change cost and risk assumptions.",
    ),
    (
        ("foundation", "roof age", "hvac", "plumbing", "electrical"),
        MissingInformationMateriality.IMPORTANT,
        ReasonImportance.MEDIUM,
        False,
        "Major system uncertainty can change near-term capex or inspection risk.",
    ),
)


def classify_missing_information(item: str) -> CommitteeMissingItem:
    """Classify one missing-information string into deterministic committee severity."""

    normalized = item.strip().lower()
    for keywords, materiality, importance, blocks, impact in _MISSING_INFORMATION_RULES:
        if any(keyword in normalized for keyword in keywords):
            return CommitteeMissingItem(
                item=item,
                materiality=materiality,
                importance=importance,
                reason_needed="The missing item affects a decision-relevant assumption or risk.",
                decision_impact=impact,
                recommended_source=None,
                blocks_recommendation=blocks,
            )
    return CommitteeMissingItem(
        item=item,
        materiality=MissingInformationMateriality.NON_MATERIAL,
        importance=ReasonImportance.LOW,
        reason_needed="The item is currently informational rather than decision-critical.",
        decision_impact="It does not independently block a recommendation at this stage.",
        recommended_source=None,
        blocks_recommendation=False,
    )


def classify_missing_information_list(items: list[str]) -> list[CommitteeMissingItem]:
    """Classify and de-duplicate missing-information strings."""

    seen: dict[str, CommitteeMissingItem] = {}
    for item in items:
        key = item.strip().lower()
        if key:
            seen[key] = classify_missing_information(item)
    return list(seen.values())


def build_offer_range(input_data: InvestmentCommitteeInput) -> DeterministicOfferRange:
    """Return a deterministic offer range sourced only from existing maximum-offer values."""

    maximum_offer = input_data.underwriting.maximum_offer
    asking_price = input_data.property.asking_price.final_value
    if asking_price is None:
        return DeterministicOfferRange(
            warnings=["asking_price_missing"],
        )

    source_candidates = (
        (
            maximum_offer.break_even_cash_flow_price,
            "break_even_cash_flow_price",
            "underwriting.maximum_offer.break_even_cash_flow_price",
            "Maximum purchase price that still keeps monthly cash flow at or above break-even.",
        ),
        (
            maximum_offer.target_monthly_cash_flow_price,
            "target_monthly_cash_flow_price",
            "underwriting.maximum_offer.target_monthly_cash_flow_price",
            "Maximum purchase price that still satisfies the monthly cash-flow target.",
        ),
        (
            maximum_offer.target_cap_rate_price,
            "target_cap_rate_price",
            "underwriting.maximum_offer.target_cap_rate_price",
            "Maximum purchase price that still satisfies the cap-rate target.",
        ),
        (
            maximum_offer.target_cash_on_cash_price,
            "target_cash_on_cash_price",
            "underwriting.maximum_offer.target_cash_on_cash_price",
            "Maximum purchase price that still satisfies the cash-on-cash target.",
        ),
        (
            maximum_offer.target_dscr_price,
            "target_dscr_price",
            "underwriting.maximum_offer.target_dscr_price",
            "Maximum purchase price that still satisfies the DSCR target.",
        ),
        (
            maximum_offer.binding_maximum_price,
            "binding_maximum_price",
            "underwriting.maximum_offer.binding_maximum_price",
            "Most restrictive deterministic maximum-offer threshold across supported targets.",
        ),
    )
    basis = [
        OfferRangeBasis(
            value=value,
            source_metric=metric,
            source_path=source_path,
            description=description,
        )
        for value, metric, source_path, description in source_candidates
        if value is not None
    ]
    if not basis:
        return DeterministicOfferRange(
            warnings=["no_deterministic_offer_thresholds_available"],
        )

    unique_values = sorted({item.value for item in basis})
    if asking_price <= unique_values[0]:
        return DeterministicOfferRange(
            supported_offer_low=asking_price,
            supported_offer_high=asking_price,
            basis=basis,
            allowed_values=[*unique_values, asking_price],
            valid_threshold_exists=True,
        )

    supported_high = min(unique_values[-1], asking_price)
    supported_low = unique_values[0]
    return DeterministicOfferRange(
        supported_offer_low=supported_low,
        supported_offer_high=supported_high,
        basis=basis,
        allowed_values=unique_values,
        valid_threshold_exists=True,
    )


def validate_offer_value(value: Decimal, offer_range: DeterministicOfferRange) -> None:
    """Reject offer values that are not explicitly supported by deterministic thresholds."""

    if value not in offer_range.allowed_values:
        raise UnsupportedOfferValueError(
            message="Offer values must match existing deterministic committee thresholds."
        )


def compute_confidence_limit(input_data: InvestmentCommitteeInput) -> ConfidencePolicyResult:
    """Compute a deterministic maximum confidence from evidence quality and uncertainty."""

    maximum = min(Decimal("0.95"), input_data.agent_research.overall_data_confidence)
    reasons = [
        f"base_research_confidence:{input_data.agent_research.overall_data_confidence}",
    ]

    if input_data.agent_research.execution_metadata.partial_failure:
        maximum -= Decimal("0.10")
        reasons.append("partial_agent_failure")

    missing_items = classify_missing_information_list(input_data.agent_research.missing_information)
    for missing_item in missing_items:
        if missing_item.materiality == MissingInformationMateriality.DECISION_CRITICAL:
            maximum -= Decimal("0.12")
            reasons.append(f"decision_critical_missing:{missing_item.item}")
        elif missing_item.materiality == MissingInformationMateriality.IMPORTANT:
            maximum -= Decimal("0.05")
            reasons.append(f"important_missing:{missing_item.item}")

    for conflict in input_data.agent_research.conflicts:
        if conflict.resolution_status == ConflictResolutionStatus.RESOLVED_DETERMINISTICALLY:
            continue
        if conflict.materiality == ConflictMateriality.HIGH:
            maximum -= Decimal("0.15")
            reasons.append(f"unresolved_high_conflict:{conflict.field_or_topic}")
        elif conflict.materiality == ConflictMateriality.MEDIUM:
            maximum -= Decimal("0.08")
            reasons.append(f"unresolved_medium_conflict:{conflict.field_or_topic}")
        else:
            maximum -= Decimal("0.04")
            reasons.append(f"unresolved_low_conflict:{conflict.field_or_topic}")

    if input_data.underwriting.maximum_offer.binding_maximum_price is None:
        maximum -= Decimal("0.06")
        reasons.append("binding_maximum_offer_unavailable")

    if input_data.underwriting.stress_tests:
        failed_stress_tests = sum(
            1
            for item in input_data.underwriting.stress_tests
            if not item.cash_flow_remains_positive
        )
        if failed_stress_tests:
            maximum -= min(Decimal("0.15"), Decimal("0.03") * failed_stress_tests)
            reasons.append(f"stress_test_failures:{failed_stress_tests}")

    maximum = max(_CONFIDENCE_FLOOR, min(_DECIMAL_ONE, maximum))
    return ConfidencePolicyResult(maximum_confidence=maximum, reasons=reasons)


def build_recommendation_policy(
    input_data: InvestmentCommitteeInput,
) -> RecommendationPolicyDecision:
    """Compute allowed recommendation labels from deterministic underwriting and evidence."""

    allowed = set(InvestmentRecommendation)
    disallowed: dict[InvestmentRecommendation, str] = {}
    warnings: list[str] = []

    offer_range = build_offer_range(input_data)
    confidence_limit = compute_confidence_limit(input_data)
    missing_items = classify_missing_information_list(input_data.agent_research.missing_information)
    critical_missing = [
        item
        for item in missing_items
        if item.materiality == MissingInformationMateriality.DECISION_CRITICAL
    ]
    unresolved_high_conflicts = [
        conflict
        for conflict in input_data.agent_research.conflicts
        if conflict.resolution_status != ConflictResolutionStatus.RESOLVED_DETERMINISTICALLY
        and conflict.materiality == ConflictMateriality.HIGH
    ]

    asking_price = input_data.property.asking_price.final_value
    binding_maximum = input_data.underwriting.maximum_offer.binding_maximum_price
    asking_supported = (
        asking_price is not None and binding_maximum is not None and asking_price <= binding_maximum
    )

    metrics = input_data.underwriting.metrics
    targets = input_data.assumptions.targets
    expected_targets: list[bool] = []
    if targets.monthly_cash_flow is not None:
        expected_targets.append(metrics.monthly_pre_tax_cash_flow >= targets.monthly_cash_flow)
    if targets.cap_rate_percent is not None and metrics.cap_rate is not None:
        expected_targets.append(metrics.cap_rate >= (targets.cap_rate_percent / Decimal("100")))
    if targets.cash_on_cash_percent is not None and metrics.cash_on_cash_return is not None:
        expected_targets.append(
            metrics.cash_on_cash_return >= (targets.cash_on_cash_percent / Decimal("100"))
        )
    if targets.dscr is not None and metrics.dscr is not None:
        expected_targets.append(metrics.dscr >= targets.dscr)
    expected_targets_met = (
        all(expected_targets)
        if expected_targets
        else metrics.monthly_pre_tax_cash_flow >= _DECIMAL_ZERO
    )

    conservative = next(
        (
            scenario
            for scenario in input_data.underwriting.scenarios
            if scenario.name == "conservative"
        ),
        None,
    )
    conservative_resilient = (
        conservative is not None
        and conservative.metrics.monthly_pre_tax_cash_flow >= _DECIMAL_ZERO
        and (conservative.metrics.dscr is None or conservative.metrics.dscr >= Decimal("1"))
    )
    stress_resilient = (
        all(item.cash_flow_remains_positive for item in input_data.underwriting.stress_tests)
        if input_data.underwriting.stress_tests
        else False
    )

    if critical_missing:
        for recommendation in (
            InvestmentRecommendation.STRONG_BUY,
            InvestmentRecommendation.BUY,
        ):
            allowed.discard(recommendation)
            disallowed[recommendation] = (
                "Decision-critical missing information blocks a confident positive recommendation."
            )
        warnings.append("decision_critical_missing_information_present")

    if unresolved_high_conflicts:
        allowed.discard(InvestmentRecommendation.STRONG_BUY)
        disallowed[InvestmentRecommendation.STRONG_BUY] = (
            "Strong buy is not allowed while a high-materiality conflict remains unresolved."
        )
        warnings.append("unresolved_high_materiality_conflict_present")

    if not expected_targets_met:
        for recommendation in (
            InvestmentRecommendation.STRONG_BUY,
            InvestmentRecommendation.BUY,
        ):
            allowed.discard(recommendation)
            disallowed[recommendation] = (
                "Expected underwriting performance does not satisfy the configured targets."
            )

    if not asking_supported:
        for recommendation in (
            InvestmentRecommendation.STRONG_BUY,
            InvestmentRecommendation.BUY,
        ):
            allowed.discard(recommendation)
            disallowed[recommendation] = (
                "The current asking price exceeds the supported deterministic maximum offer."
            )

    if (
        input_data.agent_research.execution_metadata.partial_failure
        or confidence_limit.maximum_confidence < Decimal("0.85")
        or not conservative_resilient
        or not stress_resilient
    ):
        allowed.discard(InvestmentRecommendation.STRONG_BUY)
        disallowed[InvestmentRecommendation.STRONG_BUY] = (
            "Strong buy requires high confidence, resilient downside cases, "
            "and no major workflow gaps."
        )

    if not offer_range.valid_threshold_exists or asking_price is None or asking_supported:
        allowed.discard(InvestmentRecommendation.BUY_ONLY_BELOW)
        disallowed[InvestmentRecommendation.BUY_ONLY_BELOW] = (
            "Buy-only-below requires a valid deterministic threshold below "
            "the current asking price."
        )

    if critical_missing or confidence_limit.maximum_confidence < Decimal("0.40"):
        allowed.add(InvestmentRecommendation.INSUFFICIENT_INFORMATION)

    if not allowed:
        allowed.add(InvestmentRecommendation.PASS)

    return RecommendationPolicyDecision(
        allowed_recommendations=sorted(allowed, key=lambda item: item.value),
        disallowed_recommendations=disallowed,
        critical_missing_items=critical_missing,
        offer_range=offer_range,
        confidence_limit=confidence_limit,
        warnings=warnings,
    )


def validate_recommendation(
    recommendation: InvestmentRecommendation,
    policy: RecommendationPolicyDecision,
) -> None:
    """Reject recommendation labels that are outside the allowed deterministic set."""

    if recommendation not in policy.allowed_recommendations:
        reason = policy.disallowed_recommendations.get(
            recommendation,
            "The recommendation is not allowed by deterministic committee policy.",
        )
        raise RecommendationPolicyViolationError(message=reason)


def validate_recommendation_confidence(
    output: InvestmentCommitteeOutput,
    policy: RecommendationPolicyDecision,
) -> None:
    """Reject agent confidence values that exceed the deterministic ceiling."""

    if output.recommendation_confidence > policy.confidence_limit.maximum_confidence:
        raise ConfidencePolicyViolationError(
            message=("Recommendation confidence exceeds the deterministic committee maximum.")
        )
