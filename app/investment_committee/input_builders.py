"""Deterministic input builder for the investment-committee model payload."""

from __future__ import annotations

from decimal import Decimal

from app.agent_research.evidence import build_property_key
from app.agent_research.models import AgentResearchOutput, EvidenceReference, EvidenceSourceType
from app.investment_committee.input_models import (
    CommitteeModelInput,
    CommitteePreparedAgentSummary,
    CommitteePreparedAssumption,
    CommitteePreparedConflict,
    CommitteePreparedConflictValue,
    CommitteePreparedField,
    CommitteePreparedFinding,
    CommitteePreparedMetric,
    CommitteePreparedResearch,
    CommitteePreparedScenario,
    CommitteePreparedStressTest,
)
from app.investment_committee.models import InvestmentCommitteeInput
from app.investment_committee.policies import (
    build_recommendation_policy,
    classify_missing_information_list,
)
from app.investment_committee.sanitization import sanitize_committee_value


def _dedupe_evidence(evidence: list[EvidenceReference]) -> list[EvidenceReference]:
    deduped: dict[tuple[str, str, str | None, str | None], EvidenceReference] = {}
    for reference in evidence:
        key = (
            reference.source_id,
            reference.source_type,
            reference.citation_id,
            reference.field_path,
        )
        deduped[key] = reference
    return list(deduped.values())


def _verified_property_source_id(property_key: str) -> str:
    return f"{property_key}:verified_property"


def _underwriting_source_id(property_key: str) -> str:
    return f"{property_key}:underwriting"


def _property_fields(
    input_data: InvestmentCommitteeInput,
    property_key: str,
) -> list[CommitteePreparedField]:
    prepared: list[CommitteePreparedField] = []
    for field_name, field_value in sorted(
        input_data.property.model_dump(mode="python").items(),
        key=lambda item: item[0],
    ):
        if field_name in {"source_url", "provider"}:
            continue
        if not isinstance(field_value, dict):
            continue
        prepared.append(
            CommitteePreparedField(
                field_name=field_name,
                final_value=field_value.get("final_value"),
                extracted_value=field_value.get("extracted_value"),
                status=str(field_value.get("status")),
                source=field_value.get("source"),
                confidence=field_value.get("confidence"),
                source_path=f"verified_property.{field_name}",
                evidence=[
                    EvidenceReference(
                        source_id=_verified_property_source_id(property_key),
                        source_type=EvidenceSourceType.VERIFIED_PROPERTY,
                        field_path=f"verified_property.{field_name}.final_value",
                    )
                ],
            )
        )
    return prepared


def _flatten_model(
    value: object,
    *,
    prefix: str,
) -> list[CommitteePreparedAssumption]:
    flattened: list[CommitteePreparedAssumption] = []
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="python")
        if isinstance(dumped, dict):
            for key, item in sorted(dumped.items(), key=lambda entry: entry[0]):
                flattened.extend(_flatten_model(item, prefix=f"{prefix}.{key}"))
        return flattened
    if isinstance(value, dict):
        for key, item in sorted(value.items(), key=lambda entry: str(entry[0])):
            flattened.extend(_flatten_model(item, prefix=f"{prefix}.{key}"))
        return flattened
    if isinstance(value, list):
        for index, item in enumerate(value):
            flattened.extend(_flatten_model(item, prefix=f"{prefix}[{index}]"))
        return flattened
    flattened.append(
        CommitteePreparedAssumption(
            name=prefix.rsplit(".", maxsplit=1)[-1],
            value=value if isinstance(value, (str, int, Decimal)) or value is None else str(value),
            source_path=prefix,
        )
    )
    return flattened


def _metric(
    *,
    property_key: str,
    metric_name: str,
    value: str | int | Decimal | bool | None,
    source_path: str,
    description: str,
) -> CommitteePreparedMetric:
    return CommitteePreparedMetric(
        metric_name=metric_name,
        value=value,
        source_path=source_path,
        description=description,
        evidence=[
            EvidenceReference(
                source_id=_underwriting_source_id(property_key),
                source_type=EvidenceSourceType.UNDERWRITING,
                field_path=source_path,
            )
        ],
    )


def _underwriting_metrics(
    input_data: InvestmentCommitteeInput,
    property_key: str,
) -> list[CommitteePreparedMetric]:
    metrics = input_data.underwriting.metrics
    return [
        _metric(
            property_key=property_key,
            metric_name="noi",
            value=metrics.noi,
            source_path="underwriting.metrics.noi",
            description="Net operating income from deterministic underwriting.",
        ),
        _metric(
            property_key=property_key,
            metric_name="monthly_pre_tax_cash_flow",
            value=metrics.monthly_pre_tax_cash_flow,
            source_path="underwriting.metrics.monthly_pre_tax_cash_flow",
            description="Expected monthly pre-tax cash flow.",
        ),
        _metric(
            property_key=property_key,
            metric_name="annual_pre_tax_cash_flow",
            value=metrics.annual_pre_tax_cash_flow,
            source_path="underwriting.metrics.annual_pre_tax_cash_flow",
            description="Expected annual pre-tax cash flow.",
        ),
        _metric(
            property_key=property_key,
            metric_name="cap_rate",
            value=metrics.cap_rate,
            source_path="underwriting.metrics.cap_rate",
            description="Cap rate from deterministic underwriting.",
        ),
        _metric(
            property_key=property_key,
            metric_name="cash_on_cash_return",
            value=metrics.cash_on_cash_return,
            source_path="underwriting.metrics.cash_on_cash_return",
            description="Cash-on-cash return from deterministic underwriting.",
        ),
        _metric(
            property_key=property_key,
            metric_name="dscr",
            value=metrics.dscr,
            source_path="underwriting.metrics.dscr",
            description="Debt-service coverage ratio from deterministic underwriting.",
        ),
    ]


def _maximum_offer_metrics(
    input_data: InvestmentCommitteeInput,
    property_key: str,
) -> list[CommitteePreparedMetric]:
    maximum_offer = input_data.underwriting.maximum_offer
    definitions = [
        (
            "break_even_cash_flow_price",
            maximum_offer.break_even_cash_flow_price,
            "underwriting.maximum_offer.break_even_cash_flow_price",
            "Maximum price that preserves break-even monthly cash flow.",
        ),
        (
            "target_monthly_cash_flow_price",
            maximum_offer.target_monthly_cash_flow_price,
            "underwriting.maximum_offer.target_monthly_cash_flow_price",
            "Maximum price that preserves the target monthly cash flow.",
        ),
        (
            "target_cap_rate_price",
            maximum_offer.target_cap_rate_price,
            "underwriting.maximum_offer.target_cap_rate_price",
            "Maximum price that preserves the target cap rate.",
        ),
        (
            "target_cash_on_cash_price",
            maximum_offer.target_cash_on_cash_price,
            "underwriting.maximum_offer.target_cash_on_cash_price",
            "Maximum price that preserves the target cash-on-cash return.",
        ),
        (
            "target_dscr_price",
            maximum_offer.target_dscr_price,
            "underwriting.maximum_offer.target_dscr_price",
            "Maximum price that preserves the target DSCR.",
        ),
        (
            "binding_maximum_price",
            maximum_offer.binding_maximum_price,
            "underwriting.maximum_offer.binding_maximum_price",
            "Most restrictive deterministic maximum-offer ceiling.",
        ),
        (
            "asking_price_gap",
            maximum_offer.asking_price_gap,
            "underwriting.maximum_offer.asking_price_gap",
            "Gap between the current asking price and the binding maximum price.",
        ),
        (
            "asking_price_satisfies_break_even",
            maximum_offer.asking_price_satisfies_break_even,
            "underwriting.maximum_offer.asking_price_satisfies_break_even",
            "Whether the asking price satisfies the break-even threshold.",
        ),
        (
            "asking_price_satisfies_target_monthly_cash_flow",
            maximum_offer.asking_price_satisfies_target_monthly_cash_flow,
            "underwriting.maximum_offer.asking_price_satisfies_target_monthly_cash_flow",
            "Whether the asking price satisfies the cash-flow target threshold.",
        ),
        (
            "asking_price_satisfies_target_cap_rate",
            maximum_offer.asking_price_satisfies_target_cap_rate,
            "underwriting.maximum_offer.asking_price_satisfies_target_cap_rate",
            "Whether the asking price satisfies the cap-rate target threshold.",
        ),
        (
            "asking_price_satisfies_target_cash_on_cash",
            maximum_offer.asking_price_satisfies_target_cash_on_cash,
            "underwriting.maximum_offer.asking_price_satisfies_target_cash_on_cash",
            "Whether the asking price satisfies the cash-on-cash target threshold.",
        ),
        (
            "asking_price_satisfies_target_dscr",
            maximum_offer.asking_price_satisfies_target_dscr,
            "underwriting.maximum_offer.asking_price_satisfies_target_dscr",
            "Whether the asking price satisfies the DSCR target threshold.",
        ),
    ]
    return [
        _metric(
            property_key=property_key,
            metric_name=name,
            value=value,
            source_path=source_path,
            description=description,
        )
        for name, value, source_path, description in definitions
    ]


def _scenario_references(
    input_data: InvestmentCommitteeInput,
    property_key: str,
) -> list[CommitteePreparedScenario]:
    scenarios: list[CommitteePreparedScenario] = []
    for index, scenario in enumerate(
        sorted(input_data.underwriting.scenarios, key=lambda item: item.name)
    ):
        source_prefix = f"underwriting.scenarios[{index}]"
        scenarios.append(
            CommitteePreparedScenario(
                name=scenario.name,
                source_path=source_prefix,
                metrics=[
                    _metric(
                        property_key=property_key,
                        metric_name="monthly_pre_tax_cash_flow",
                        value=scenario.metrics.monthly_pre_tax_cash_flow,
                        source_path=f"{source_prefix}.metrics.monthly_pre_tax_cash_flow",
                        description=f"{scenario.name} scenario monthly pre-tax cash flow.",
                    ),
                    _metric(
                        property_key=property_key,
                        metric_name="cap_rate",
                        value=scenario.metrics.cap_rate,
                        source_path=f"{source_prefix}.metrics.cap_rate",
                        description=f"{scenario.name} scenario cap rate.",
                    ),
                    _metric(
                        property_key=property_key,
                        metric_name="cash_on_cash_return",
                        value=scenario.metrics.cash_on_cash_return,
                        source_path=f"{source_prefix}.metrics.cash_on_cash_return",
                        description=f"{scenario.name} scenario cash-on-cash return.",
                    ),
                    _metric(
                        property_key=property_key,
                        metric_name="dscr",
                        value=scenario.metrics.dscr,
                        source_path=f"{source_prefix}.metrics.dscr",
                        description=f"{scenario.name} scenario DSCR.",
                    ),
                ],
                warnings=list(dict.fromkeys(scenario.warnings)),
            )
        )
    return scenarios


def _stress_test_references(
    input_data: InvestmentCommitteeInput,
    property_key: str,
) -> list[CommitteePreparedStressTest]:
    prepared: list[CommitteePreparedStressTest] = []
    for index, stress_test in enumerate(input_data.underwriting.stress_tests):
        source_prefix = f"underwriting.stress_tests[{index}]"
        prepared.append(
            CommitteePreparedStressTest(
                identifier=stress_test.identifier,
                description=stress_test.description,
                source_path=source_prefix,
                changed_assumptions=[
                    CommitteePreparedAssumption(
                        name=name,
                        value=value
                        if isinstance(value, (str, int, Decimal)) or value is None
                        else str(value),
                        source_path=f"{source_prefix}.changed_assumptions.{name}",
                        evidence=[
                            EvidenceReference(
                                source_id=_underwriting_source_id(property_key),
                                source_type=EvidenceSourceType.UNDERWRITING,
                                field_path=f"{source_prefix}.changed_assumptions.{name}",
                            )
                        ],
                    )
                    for name, value in sorted(
                        stress_test.changed_assumptions.items(),
                        key=lambda item: item[0],
                    )
                ],
                metrics=[
                    _metric(
                        property_key=property_key,
                        metric_name="change_in_monthly_cash_flow",
                        value=stress_test.change_in_monthly_cash_flow,
                        source_path=f"{source_prefix}.change_in_monthly_cash_flow",
                        description="Stress-test delta for monthly pre-tax cash flow.",
                    ),
                    _metric(
                        property_key=property_key,
                        metric_name="change_in_annual_cash_flow",
                        value=stress_test.change_in_annual_cash_flow,
                        source_path=f"{source_prefix}.change_in_annual_cash_flow",
                        description="Stress-test delta for annual pre-tax cash flow.",
                    ),
                    _metric(
                        property_key=property_key,
                        metric_name="stressed_dscr",
                        value=stress_test.stressed_metrics.dscr,
                        source_path=f"{source_prefix}.stressed_metrics.dscr",
                        description="Stress-test DSCR after applying the changed assumption set.",
                    ),
                ],
                cash_flow_remains_positive=stress_test.cash_flow_remains_positive,
                additional_cash_required=stress_test.additional_cash_required,
                warnings=list(dict.fromkeys(stress_test.warnings)),
            )
        )
    return prepared


def _prepared_findings(input_data: InvestmentCommitteeInput) -> list[CommitteePreparedFinding]:
    findings_by_id: dict[str, CommitteePreparedFinding] = {}
    agent_lookup = {
        finding.finding_id: output.agent_name
        for output in _agent_outputs(input_data)
        for finding in output.findings
    }
    for finding in input_data.agent_research.consolidated_findings:
        findings_by_id[finding.finding_id] = CommitteePreparedFinding(
            finding_id=finding.finding_id,
            source_agent=agent_lookup.get(finding.finding_id, "consolidated"),
            category=finding.category,
            title=finding.title,
            finding=finding.finding,
            significance=finding.significance,
            severity=finding.severity,
            confidence=finding.confidence,
            evidence=_dedupe_evidence(finding.evidence),
            affected_fields=sorted(dict.fromkeys(finding.affected_fields)),
            missing_information=sorted(dict.fromkeys(finding.missing_information)),
            recommended_next_actions=sorted(dict.fromkeys(finding.recommended_next_actions)),
            is_inference=finding.is_inference,
        )
    return list(findings_by_id.values())


def _prepared_conflicts(input_data: InvestmentCommitteeInput) -> list[CommitteePreparedConflict]:
    return [
        CommitteePreparedConflict(
            conflict_id=conflict.conflict_id,
            field_or_topic=conflict.field_or_topic,
            materiality=conflict.materiality,
            resolution_status=conflict.resolution_status,
            preferred_value=conflict.preferred_value,
            preferred_source_id=conflict.preferred_source_id,
            resolution_reason=conflict.resolution_reason,
            requires_user_review=conflict.requires_user_review,
            requires_synthesis=conflict.requires_synthesis,
            values=[
                CommitteePreparedConflictValue(
                    value=value.value,
                    source_id=value.source_id,
                    source_type=value.source_type,
                    confidence=value.confidence,
                    label=value.label,
                    field_path=value.field_path,
                    agent_name=value.agent_name,
                    authoritative=value.authoritative,
                    verified=value.verified,
                )
                for value in conflict.values
            ],
        )
        for conflict in input_data.agent_research.conflicts
    ]


def _agent_outputs(input_data: InvestmentCommitteeInput) -> list[AgentResearchOutput]:
    return [
        output
        for output in (
            input_data.agent_research.listing_analysis,
            input_data.agent_research.public_records_analysis,
            input_data.agent_research.comparable_analysis,
            input_data.agent_research.neighborhood_analysis,
            input_data.agent_research.risk_analysis,
        )
        if output is not None
    ]


def _agent_summaries(input_data: InvestmentCommitteeInput) -> list[CommitteePreparedAgentSummary]:
    outputs = _agent_outputs(input_data)
    return [
        CommitteePreparedAgentSummary(
            agent_name=output.agent_name,
            summary=output.summary,
            overall_confidence=output.overall_confidence,
            findings_count=len(output.findings),
            missing_information=sorted(dict.fromkeys(output.missing_information)),
            warnings=sorted(dict.fromkeys(output.warnings)),
        )
        for output in sorted(outputs, key=lambda item: item.agent_name)
    ]


def _research_section(input_data: InvestmentCommitteeInput) -> CommitteePreparedResearch:
    return CommitteePreparedResearch(
        overall_data_confidence=input_data.agent_research.overall_data_confidence,
        due_diligence_questions=sorted(
            dict.fromkeys(input_data.agent_research.due_diligence_questions)
        ),
        missing_information=classify_missing_information_list(
            input_data.agent_research.missing_information
        ),
        consolidated_findings=_prepared_findings(input_data),
        conflicts=_prepared_conflicts(input_data),
        agent_summaries=_agent_summaries(input_data),
        evidence_index=_dedupe_evidence(input_data.agent_research.evidence_index),
        warnings=sorted(dict.fromkeys(input_data.agent_research.warnings)),
        partial_failure=input_data.agent_research.execution_metadata.partial_failure,
    )


def build_committee_model_input(input_data: InvestmentCommitteeInput) -> CommitteeModelInput:
    """Build a stable, sanitized model-input payload for the committee agent."""

    property_key = build_property_key(input_data.property)
    model_input = CommitteeModelInput(
        property_key=property_key,
        property_fields=_property_fields(input_data, property_key),
        assumptions=_flatten_model(input_data.assumptions, prefix="assumptions"),
        underwriting_metrics=_underwriting_metrics(input_data, property_key),
        maximum_offer=_maximum_offer_metrics(input_data, property_key),
        scenarios=_scenario_references(input_data, property_key),
        stress_tests=_stress_test_references(input_data, property_key),
        research=_research_section(input_data),
        policy=build_recommendation_policy(input_data),
        warnings=[],
    )
    sanitized, warnings = sanitize_committee_value(model_input)
    sanitized.warnings = sorted(dict.fromkeys([*sanitized.warnings, *warnings]))
    return sanitized
