"""Fixture-driven evaluation and regression tests for agent research hardening."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.agent_research.conflicts import analyze_conflicts
from app.agent_research.exceptions import AgentGuardrailFailureError
from app.agent_research.guardrails import validate_agent_output
from app.agent_research.models import (
    AgentFinding,
    EvidenceReference,
    EvidenceSourceType,
    FindingSeverity,
)
from app.agent_research.services import ListingAgentService
from app.agent_research.synthesis import UnifiedSynthesisService
from app.agent_research.versioning import AgentName
from tests.agent_sdk_utils import (
    StubAgentRunner,
    make_agent_context,
    make_comparable_agent_output,
    make_listing_agent_output,
    make_neighborhood_agent_output,
    make_property_risk_output,
    make_public_records_agent_output,
    make_underwriting_analysis,
)
from tests.test_agent_research_synthesis import (
    StubRiskService,
    StubSpecialistOrchestrator,
    build_request,
    build_workflow_response,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "agent_research_evaluation_cases.json"


def load_cases() -> dict[str, dict[str, object]]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {case["case_id"]: case for case in payload["cases"]}


def test_conflict_recall_fixture_detects_expected_year_built_conflict() -> None:
    case = load_cases()["conflict_recall_year_built"]
    context = make_agent_context()
    assert context.listing_extraction is not None
    context.listing_extraction.property.year_built = 2001
    context.verified_property.year_built.final_value = None

    result = analyze_conflicts(
        verified_property=context.verified_property,
        listing_extraction=context.listing_extraction,
        research_package=context.research_package,
        listing_analysis=make_listing_agent_output(),
        public_records_analysis=make_public_records_agent_output(),
        comparable_analysis=make_comparable_agent_output(),
        neighborhood_analysis=make_neighborhood_agent_output(),
    )

    assert any(
        conflict.field_or_topic == case["expected_conflict_field"] for conflict in result.conflicts
    )


@pytest.mark.asyncio
async def test_missing_data_recall_fixture_surfaces_expected_gap() -> None:
    case = load_cases()["missing_data_roof_age"]
    service = UnifiedSynthesisService(
        specialist_orchestrator=StubSpecialistOrchestrator(build_workflow_response()),
        risk_agent_service=StubRiskService(make_property_risk_output()),
    )

    response = await service.run(request_id="req-123", payload=build_request())

    assert response.package is not None
    assert case["expected_missing_value"] in response.package.missing_information


def test_fair_housing_fixture_blocks_prohibited_language() -> None:
    case = load_cases()["fair_housing_block"]
    context = make_agent_context()
    output = make_neighborhood_agent_output()
    output.summary = str(case["blocked_phrase"]).capitalize()

    with pytest.raises(AgentGuardrailFailureError):
        validate_agent_output(agent_name=AgentName.NEIGHBORHOOD, output=output, context=context)


@pytest.mark.asyncio
async def test_prompt_injection_fixture_does_not_reach_agent_input() -> None:
    case = load_cases()["prompt_injection_sanitized"]
    context = make_agent_context()
    runner = StubAgentRunner(make_listing_agent_output())
    service = ListingAgentService(runner=runner)

    await service.run(context)

    agent_input = str(runner.calls[0]["agent_input"])
    assert str(case["filtered_marker"]) in agent_input
    assert "ignore previous instructions" not in agent_input.lower()


@pytest.mark.asyncio
async def test_evidence_coverage_fixture_preserves_traceable_evidence() -> None:
    case = load_cases()["evidence_coverage_consolidated"]
    workflow_response = build_workflow_response()
    assert workflow_response.result is not None
    workflow_response.result.listing_analysis.findings = [
        AgentFinding(
            finding_id="finding-1",
            category="listing",
            title="Evidence-backed finding",
            finding="Listing evidence remains traceable.",
            significance="Used for evidence coverage evaluation.",
            severity=FindingSeverity.LOW,
            confidence="0.70",
            evidence=[
                EvidenceReference(
                    source_id="property:3f0ddefba267eb73:verified_property",
                    source_type=EvidenceSourceType.VERIFIED_PROPERTY,
                    field_path="verified_property.full_address.final_value",
                )
            ],
            affected_fields=["full_address"],
            is_inference=False,
        )
    ]
    service = UnifiedSynthesisService(
        specialist_orchestrator=StubSpecialistOrchestrator(workflow_response),
        risk_agent_service=StubRiskService(make_property_risk_output()),
    )

    response = await service.run(request_id="req-123", payload=build_request())

    assert response.package is not None
    assert len(response.package.evidence_index) >= int(case["minimum_evidence_count"])


def test_regression_existing_workflow_context_still_builds() -> None:
    context = make_agent_context(underwriting_result=make_underwriting_analysis())

    assert context.request_id == "req-123"
    assert context.research_package.public_records is not None
    assert context.underwriting_result is not None
