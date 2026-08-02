"""Output guardrails and deterministic validations for specialist agents."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from agents import Agent, GuardrailFunctionOutput, RunContextWrapper, output_guardrail

from app.agent_research.context import AgentRunContext
from app.agent_research.evidence import (
    build_evidence_index,
    validate_evidence_references,
    validate_source_ownership,
)
from app.agent_research.exceptions import AgentGuardrailFailureError
from app.agent_research.models import AgentResearchOutput, FindingSeverity
from app.agent_research.risk_models import PropertyRiskAgentOutput, RiskCategory
from app.agent_research.specialist_models import (
    GuardrailReport,
    NeighborhoodAgentOutput,
    NeighborhoodGuardrailReport,
)
from app.agent_research.versioning import AgentName

RECOMMENDATION_PHRASES = (
    "buy this property",
    "pass on this property",
    "negotiate this property",
    "you should buy",
    "you should pass",
    "you should negotiate",
    "final recommendation",
    "recommend buying",
    "recommend passing",
)

FAIR_HOUSING_TERMS = (
    "race",
    "ethnicity",
    "religion",
    "nationality",
    "family status",
    "disability",
    "gender",
    "sex",
    "families",
    "christian",
    "muslim",
    "jewish",
    "black",
    "white",
    "asian",
    "hispanic",
)

FAIR_HOUSING_PHRASES = (
    "good for families",
    "great for families",
    "safe for children",
    "good area for raising kids",
    "best area for immigrants",
    "suitable for retirees",
    "ideal for young professionals",
)

RISK_QUALIFIERS = (
    "may",
    "could",
    "possible",
    "possibly",
    "potential",
    "potentially",
    "appears",
    "appears to",
    "suggests",
    "not verified",
    "not confirmed",
    "requires inspection",
    "subject to inspection",
    "further review",
)

DIAGNOSTIC_PHRASES = (
    "is failing",
    "has failed",
    "is defective",
    "has mold",
    "contains asbestos",
    "has structural damage",
    "is unsafe",
    "needs full replacement",
)


def _collect_output_text(output: AgentResearchOutput) -> str:
    parts = [
        output.summary,
        *output.missing_information,
        *output.due_diligence_questions,
        *output.warnings,
    ]
    for finding in output.findings:
        parts.extend(
            [
                finding.title,
                finding.finding,
                finding.significance,
                *finding.missing_information,
                *finding.recommended_next_actions,
            ]
        )
    for conflict in output.conflicts:
        parts.extend([conflict.field_or_topic, conflict.description, *conflict.values_or_claims])
    if isinstance(output, PropertyRiskAgentOutput):
        for risk in output.risk_findings:
            parts.extend(
                [
                    risk.title,
                    risk.summary,
                    risk.significance,
                    *risk.recommended_next_actions,
                    *risk.missing_information,
                ]
            )
        for item in output.inspection_priorities:
            parts.extend([item.title, item.rationale])
        for question in output.seller_questions:
            parts.extend([question.question, question.rationale])
    return " ".join(part.lower() for part in parts if part)


def _recommendation_hits(output: AgentResearchOutput) -> list[str]:
    haystack = _collect_output_text(output)
    return [phrase for phrase in RECOMMENDATION_PHRASES if phrase in haystack]


def _fair_housing_report(output: NeighborhoodAgentOutput) -> NeighborhoodGuardrailReport:
    haystack = _collect_output_text(output)
    blocked_terms = [term for term in FAIR_HOUSING_TERMS if term in haystack]
    blocked_phrases = [phrase for phrase in FAIR_HOUSING_PHRASES if phrase in haystack]
    return NeighborhoodGuardrailReport(
        blocked_terms=blocked_terms,
        blocked_phrases=blocked_phrases,
    )


def bounded_confidence_limit(output: AgentResearchOutput) -> Decimal:
    evidence_count = sum(len(finding.evidence) for finding in output.findings)
    if evidence_count >= 6:
        return Decimal("0.95")
    if evidence_count >= 3:
        return Decimal("0.90")
    if evidence_count >= 1:
        return Decimal("0.85")
    return Decimal("0.60")


def _risk_guardrail_report(output: PropertyRiskAgentOutput) -> dict[str, list[str]]:
    unqualified_physical_risk_ids: list[str] = []
    unsupported_financial_risk_ids: list[str] = []
    diagnostic_claim_ids: list[str] = []

    for risk in output.risk_findings:
        combined_text = " ".join(
            [
                risk.title,
                risk.summary,
                risk.significance,
                *risk.recommended_next_actions,
            ]
        ).lower()
        if risk.category == RiskCategory.PHYSICAL_CONDITION:
            if any(phrase in combined_text for phrase in DIAGNOSTIC_PHRASES):
                diagnostic_claim_ids.append(risk.risk_id)
            if not any(qualifier in combined_text for qualifier in RISK_QUALIFIERS):
                unqualified_physical_risk_ids.append(risk.risk_id)
        if risk.category == RiskCategory.FINANCIAL_FRAGILITY and not any(
            evidence.source_type.value == "underwriting"
            or evidence.source_id.endswith(":underwriting")
            or (evidence.field_path or "").startswith("underwriting.")
            for evidence in risk.evidence
        ):
            unsupported_financial_risk_ids.append(risk.risk_id)

    return {
        "unqualified_physical_risk_ids": unqualified_physical_risk_ids,
        "unsupported_financial_risk_ids": unsupported_financial_risk_ids,
        "diagnostic_claim_ids": diagnostic_claim_ids,
    }


def validate_agent_output(
    *,
    agent_name: AgentName,
    output: AgentResearchOutput,
    context: AgentRunContext,
) -> GuardrailReport:
    """Run deterministic output validation after a specialist agent returns."""

    recommendation_hits = _recommendation_hits(output)
    if recommendation_hits:
        raise AgentGuardrailFailureError(
            message="Agent output included a prohibited investment recommendation.",
        )

    index = build_evidence_index(context)
    invalid_sources: list[str] = []
    invalid_conflict_sources: list[str] = []
    unsupported_material_findings: list[str] = []
    maximum_confidence = bounded_confidence_limit(output)

    for finding in output.findings:
        try:
            validate_evidence_references(finding.evidence, index)
        except Exception as exc:
            raise AgentGuardrailFailureError(message=str(exc)) from exc
        if (
            finding.severity
            in {
                FindingSeverity.MEDIUM,
                FindingSeverity.HIGH,
                FindingSeverity.CRITICAL,
            }
            and not finding.evidence
        ):
            unsupported_material_findings.append(finding.finding_id)
        if finding.confidence > maximum_confidence:
            finding.confidence = maximum_confidence
    if output.overall_confidence > maximum_confidence:
        output.overall_confidence = maximum_confidence

    if isinstance(output, PropertyRiskAgentOutput):
        for risk in output.risk_findings:
            try:
                validate_evidence_references(risk.evidence, index)
            except Exception as exc:
                raise AgentGuardrailFailureError(message=str(exc)) from exc
            if risk.confidence > maximum_confidence:
                risk.confidence = maximum_confidence
        for item in output.inspection_priorities:
            try:
                validate_evidence_references(item.evidence, index)
            except Exception as exc:
                raise AgentGuardrailFailureError(message=str(exc)) from exc
        for question in output.seller_questions:
            try:
                validate_evidence_references(question.evidence, index)
            except Exception as exc:
                raise AgentGuardrailFailureError(message=str(exc)) from exc

    for source_id in output.sources_used:
        try:
            validate_source_ownership(source_id, index)
        except Exception:
            invalid_sources.append(source_id)
    if invalid_sources:
        raise AgentGuardrailFailureError(message="Agent output referenced unsupported source IDs.")

    for conflict in output.conflicts:
        for source_id in conflict.source_ids:
            try:
                validate_source_ownership(source_id, index)
            except Exception:
                invalid_conflict_sources.append(source_id)
    if invalid_conflict_sources:
        raise AgentGuardrailFailureError(
            message="Agent output referenced invalid conflict source IDs.",
        )

    neighborhood_report: NeighborhoodGuardrailReport | None = None
    risk_report: dict[str, list[str]] | None = None
    if agent_name == AgentName.NEIGHBORHOOD:
        neighborhood_output = output if isinstance(output, NeighborhoodAgentOutput) else None
        if neighborhood_output is None:
            raise AgentGuardrailFailureError(
                message="Neighborhood agent output did not match the expected contract.",
            )
        neighborhood_report = _fair_housing_report(neighborhood_output)
        if neighborhood_report.blocked_terms or neighborhood_report.blocked_phrases:
            raise AgentGuardrailFailureError(
                message="Neighborhood agent output violated fair-housing restrictions.",
            )
    if agent_name == AgentName.PROPERTY_RISK:
        risk_output = output if isinstance(output, PropertyRiskAgentOutput) else None
        if risk_output is None:
            raise AgentGuardrailFailureError(
                message="Property Risk agent output did not match the expected contract.",
            )
        risk_report = _risk_guardrail_report(risk_output)
        if risk_report["unqualified_physical_risk_ids"]:
            raise AgentGuardrailFailureError(
                message="Property Risk agent output included unqualified physical-risk claims.",
            )
        if risk_report["unsupported_financial_risk_ids"]:
            raise AgentGuardrailFailureError(
                message="Property Risk financial-risk findings lacked underwriting evidence.",
            )
        if risk_report["diagnostic_claim_ids"]:
            raise AgentGuardrailFailureError(
                message="Property Risk agent output included unsupported defect diagnoses.",
            )

    return GuardrailReport(
        recommendation_phrases=recommendation_hits,
        invalid_sources=invalid_sources,
        invalid_conflict_sources=invalid_conflict_sources,
        unsupported_material_findings=unsupported_material_findings,
        neighborhood=neighborhood_report,
        risk=risk_report,
        maximum_confidence_applied=maximum_confidence,
    )


@output_guardrail(name="no_final_recommendations")
def no_final_recommendations_guardrail(
    context: RunContextWrapper[AgentRunContext],
    agent: Agent[Any],
    agent_output: AgentResearchOutput,
) -> GuardrailFunctionOutput:
    hits = _recommendation_hits(agent_output)
    return GuardrailFunctionOutput(
        output_info={
            "blocked_phrases": hits,
            "agent": agent.name,
            "request_id": context.context.request_id,
        },
        tripwire_triggered=bool(hits),
    )


@output_guardrail(name="neighborhood_fair_housing")
def neighborhood_fair_housing_guardrail(
    context: RunContextWrapper[AgentRunContext],
    agent: Agent[Any],
    agent_output: NeighborhoodAgentOutput,
) -> GuardrailFunctionOutput:
    report = _fair_housing_report(agent_output)
    return GuardrailFunctionOutput(
        output_info={
            "blocked_terms": report.blocked_terms,
            "blocked_phrases": report.blocked_phrases,
            "agent": agent.name,
            "request_id": context.context.request_id,
        },
        tripwire_triggered=bool(report.blocked_terms or report.blocked_phrases),
    )


AGENT_OUTPUT_GUARDRAILS = {
    AgentName.LISTING: [no_final_recommendations_guardrail],
    AgentName.PUBLIC_RECORDS: [no_final_recommendations_guardrail],
    AgentName.COMPARABLE: [no_final_recommendations_guardrail],
    AgentName.NEIGHBORHOOD: [
        no_final_recommendations_guardrail,
        neighborhood_fair_housing_guardrail,
    ],
    AgentName.PROPERTY_RISK: [no_final_recommendations_guardrail],
}


def guardrails_for_agent(agent_name: AgentName) -> list[Any]:
    """Return SDK output guardrails configured for a specialist agent."""

    return AGENT_OUTPUT_GUARDRAILS.get(agent_name, [no_final_recommendations_guardrail])
