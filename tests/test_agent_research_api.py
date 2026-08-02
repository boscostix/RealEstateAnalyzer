"""API integration tests for the unified agent-research endpoint."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.agent_research.api_models import AgentResearchRunRequest, AgentResearchRunResponse
from app.agent_research.models import AgentExecutionMetadata, UnifiedAgentResearchPackage
from app.api.agent_research_routes import get_unified_synthesis_service
from app.exceptions import AppError
from app.main import app
from tests.agent_sdk_utils import (
    make_agent_context,
    make_comparable_agent_output,
    make_listing_agent_output,
    make_neighborhood_agent_output,
    make_property_risk_output,
    make_public_records_agent_output,
)

client = TestClient(app, raise_server_exceptions=False)


def build_request() -> AgentResearchRunRequest:
    context = make_agent_context()
    return AgentResearchRunRequest(
        verified_property=context.verified_property,
        listing_extraction=context.listing_extraction,
        research_package=context.research_package,
        analysis_id=context.analysis_id,
    )


class StubSynthesisService:
    async def run(
        self,
        *,
        request_id: str,
        payload: AgentResearchRunRequest,
    ) -> AgentResearchRunResponse:
        del request_id, payload
        package = UnifiedAgentResearchPackage(
            listing_analysis=make_listing_agent_output(),
            public_records_analysis=make_public_records_agent_output(),
            comparable_analysis=make_comparable_agent_output(),
            neighborhood_analysis=make_neighborhood_agent_output(),
            risk_analysis=make_property_risk_output(),
            overall_data_confidence="0.78",
            warnings=["partial-data-warning"],
            execution_metadata=AgentExecutionMetadata(
                request_id="req-123",
                workflow_name="real_estate_agent_research",
                workflow_version="v1",
                prompt_version="v1",
                model_name="gpt-5-mini",
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                total_duration_ms=25,
                partial_failure=True,
                warnings=["partial-data-warning"],
            ),
        )
        return AgentResearchRunResponse(
            success=True,
            package=package,
            warnings=["partial-data-warning"],
        )


class BrokenSynthesisService:
    async def run(
        self,
        *,
        request_id: str,
        payload: AgentResearchRunRequest,
    ) -> AgentResearchRunResponse:
        del request_id, payload
        raise AppError(code="agent_synthesis_failure", message="Synthesis failed.", status_code=502)


def test_agent_research_endpoint_returns_structured_package() -> None:
    app.dependency_overrides[get_unified_synthesis_service] = lambda: StubSynthesisService()
    try:
        response = client.post(
            "/api/v1/agent-research/run",
            json=build_request().model_dump(mode="json"),
            headers={"X-Request-ID": "req-123"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["package"]["listing_analysis"]["agent_name"] == "listing_agent"
    assert body["package"]["execution_metadata"]["partial_failure"] is True
    assert body["warnings"] == ["partial-data-warning"]
    assert response.headers["X-Request-ID"] == "req-123"


def test_agent_research_endpoint_returns_structured_error() -> None:
    app.dependency_overrides[get_unified_synthesis_service] = lambda: BrokenSynthesisService()
    try:
        response = client.post(
            "/api/v1/agent-research/run",
            json=build_request().model_dump(mode="json"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json() == {
        "success": False,
        "error": {
            "code": "agent_synthesis_failure",
            "message": "Synthesis failed.",
            "retryable": False,
        },
    }
