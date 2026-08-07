"""Tests for unified agent-research synthesis."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import cast

import pytest

from app.agent_research.api_models import AgentResearchRunRequest
from app.agent_research.evidence import build_property_key
from app.agent_research.models import EvidenceReference, EvidenceSourceType, FindingSeverity
from app.agent_research.orchestration_models import (
    AgentRunRecord,
    AgentRunStatus,
    AgentUsageSummary,
    SpecialistWorkflowMetadata,
    SpecialistWorkflowResponse,
    SpecialistWorkflowResult,
    WorkflowStatus,
)
from app.agent_research.orchestrator import SpecialistAgentOrchestrator
from app.agent_research.risk_models import (
    InspectionPriority,
    PropertyRiskAgentOutput,
    RiskCategory,
    RiskFinding,
)
from app.agent_research.services import PropertyRiskAgentService, ServiceRunResult
from app.agent_research.specialist_models import (
    ComparableAgentOutput,
    ListingAgentOutput,
    NeighborhoodAgentOutput,
    PublicRecordsAgentOutput,
)
from app.agent_research.synthesis import UnifiedSynthesisService
from app.agent_research.versioning import AgentName
from tests.agent_sdk_utils import (
    make_agent_context,
    make_comparable_agent_output,
    make_listing_agent_output,
    make_neighborhood_agent_output,
    make_property_risk_output,
    make_public_records_agent_output,
    make_underwriting_analysis,
)


def build_request() -> AgentResearchRunRequest:
    context = make_agent_context(underwriting_result=make_underwriting_analysis())
    return AgentResearchRunRequest(
        verified_property=context.verified_property,
        listing_extraction=context.listing_extraction,
        research_package=context.research_package,
        underwriting_result=context.underwriting_result,
        analysis_id=context.analysis_id,
    )


def build_workflow_response(
    *,
    listing: bool = True,
    public_records: bool = True,
    comparable: bool = True,
    neighborhood: bool = True,
) -> SpecialistWorkflowResponse:
    outputs = {
        AgentName.LISTING: make_listing_agent_output() if listing else None,
        AgentName.PUBLIC_RECORDS: make_public_records_agent_output() if public_records else None,
        AgentName.COMPARABLE: make_comparable_agent_output() if comparable else None,
        AgentName.NEIGHBORHOOD: make_neighborhood_agent_output() if neighborhood else None,
    }
    listing_output = cast(ListingAgentOutput | None, outputs[AgentName.LISTING])
    public_records_output = cast(
        PublicRecordsAgentOutput | None, outputs[AgentName.PUBLIC_RECORDS]
    )
    comparable_output = cast(ComparableAgentOutput | None, outputs[AgentName.COMPARABLE])
    neighborhood_output = cast(
        NeighborhoodAgentOutput | None, outputs[AgentName.NEIGHBORHOOD]
    )
    run_records = [
        AgentRunRecord(
            agent_name=agent_name,
            status=AgentRunStatus.COMPLETED if output is not None else AgentRunStatus.FAILED,
            duration_ms=5,
            output_available=output is not None,
            error_code=None if output is not None else "agent_model_failure",
        )
        for agent_name, output in outputs.items()
    ]
    metadata = SpecialistWorkflowMetadata(
        request_id="req-123",
        analysis_id="analysis-1",
        workflow_name="real_estate_agent_research",
        workflow_status=(
            WorkflowStatus.COMPLETED
            if all(output is not None for output in outputs.values())
            else WorkflowStatus.PARTIAL
        ),
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        total_duration_ms=20,
        completed_agents=[name for name, output in outputs.items() if output is not None],
        failed_agents=[name for name, output in outputs.items() if output is None],
        partial_failure=not all(output is not None for output in outputs.values()),
        usage=AgentUsageSummary(requests=4, input_tokens=400, output_tokens=200, total_tokens=600),
        trace_metadata={"request_id": "req-123", "prompt_version": "v1"},
        run_records=run_records,
    )
    return SpecialistWorkflowResponse(
        success=True,
        result=SpecialistWorkflowResult(
            listing_analysis=listing_output,
            public_records_analysis=public_records_output,
            comparable_analysis=comparable_output,
            neighborhood_analysis=neighborhood_output,
            metadata=metadata,
            warnings=[],
        ),
    )


class StubSpecialistOrchestrator:
    def __init__(self, response: SpecialistWorkflowResponse) -> None:
        self.response = response

    async def run(self, context: object) -> SpecialistWorkflowResponse:
        del context
        return self.response

    @property
    def _config(self) -> object:  # noqa: SLF001
        from app.agent_research.config import AgentRuntimeConfig

        return AgentRuntimeConfig()


class StubRiskService:
    def __init__(self, output: PropertyRiskAgentOutput) -> None:
        self.output = output

    async def run_with_record(
        self, context: object, *, built_input: object
    ) -> ServiceRunResult[PropertyRiskAgentOutput]:
        del context, built_input

        return ServiceRunResult(
            output=self.output,
            record=AgentRunRecord(
                agent_name=AgentName.PROPERTY_RISK,
                status=AgentRunStatus.COMPLETED,
                duration_ms=5,
                output_available=True,
            ),
        )


@pytest.mark.asyncio
async def test_unified_synthesis_service_returns_strict_package() -> None:
    request = build_request()
    property_key = build_property_key(request.verified_property)
    risk_output = make_property_risk_output()
    risk_output.risk_findings = [
        RiskFinding(
            risk_id="risk-1",
            category=RiskCategory.DATA_GAP,
            title="Roof age missing",
            summary="Roof age may be material because it is not documented.",
            significance="Missing roof-age data could delay scope validation.",
            severity=FindingSeverity.MEDIUM,
            confidence=Decimal("0.70"),
            evidence=[
                EvidenceReference(
                    source_id=f"{property_key}:verified_property",
                    source_type=EvidenceSourceType.VERIFIED_PROPERTY,
                    field_path="verified_property.full_address.final_value",
                )
            ],
            inspection_priority=InspectionPriority.ROUTINE,
            missing_information=["roof age"],
            is_missing_data_risk=True,
        )
    ]
    service = UnifiedSynthesisService(
        specialist_orchestrator=cast(
            SpecialistAgentOrchestrator,
            StubSpecialistOrchestrator(build_workflow_response()),
        ),
        risk_agent_service=cast(PropertyRiskAgentService, StubRiskService(risk_output)),
    )

    response = await service.run(request_id="req-123", payload=request)

    assert response.success is True
    assert response.package is not None
    assert response.package.listing_analysis is not None
    assert response.package.risk_analysis is not None
    assert response.package.execution_metadata.partial_failure is False
    assert response.package.execution_metadata.traced is True
    assert response.package.execution_metadata.usage_requests >= 4
    assert response.package.execution_metadata.prompt_version == "v1"
    assert response.package.overall_data_confidence > Decimal("0")


@pytest.mark.asyncio
async def test_unified_synthesis_service_exposes_partial_failures_and_skips_risk() -> None:
    service = UnifiedSynthesisService(
        specialist_orchestrator=cast(
            SpecialistAgentOrchestrator,
            StubSpecialistOrchestrator(build_workflow_response(neighborhood=False)),
        ),
        risk_agent_service=cast(
            PropertyRiskAgentService,
            StubRiskService(make_property_risk_output()),
        ),
    )

    response = await service.run(request_id="req-123", payload=build_request())

    assert response.success is True
    assert response.package is not None
    assert response.package.neighborhood_analysis is None
    assert response.package.risk_analysis is None
    assert response.package.execution_metadata.partial_failure is True
    assert "risk_agent_skipped_missing_upstream_agents" in response.package.warnings
