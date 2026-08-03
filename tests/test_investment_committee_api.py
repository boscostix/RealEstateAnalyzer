"""API integration tests for the investment-committee workflow."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from app.api.investment_committee_routes import get_investment_committee_service
from app.exceptions import AppError
from app.investment_committee.api_models import (
    InvestmentCommitteeAnalyzeRequest,
)
from app.investment_committee.models import (
    CommitteeExecutionMetadata,
    CommitteeMissingItem,
    CommitteeUsageMetadata,
    InvestmentCommitteeAnalysisResult,
    InvestmentCommitteeInput,
    InvestmentRecommendation,
    MissingInformationMateriality,
    ReasonImportance,
)
from app.main import app
from tests.test_investment_committee_agent import make_committee_output
from tests.test_investment_committee_policies import make_committee_input

client = TestClient(app, raise_server_exceptions=False)


def build_request() -> InvestmentCommitteeAnalyzeRequest:
    committee_input = make_committee_input()
    return InvestmentCommitteeAnalyzeRequest(
        property=committee_input.property,
        assumptions=committee_input.assumptions,
        underwriting=committee_input.underwriting,
        agent_research=committee_input.agent_research,
        decision_context=committee_input.decision_context,
        analysis_id="analysis-1",
    )


class StubCommitteeService:
    async def analyze_with_details(
        self,
        *,
        request_id: str,
        committee_input: InvestmentCommitteeInput,
        analysis_id: str | None = None,
    ) -> InvestmentCommitteeAnalysisResult:
        del committee_input
        output = make_committee_output()
        started_at = datetime.now(UTC)
        return InvestmentCommitteeAnalysisResult(
            output=output,
            execution_metadata=CommitteeExecutionMetadata(
                request_id=request_id,
                workflow_name="investment_committee",
                agent_version="investment_committee_agent:v1",
                prompt_version="v1",
                input_format_version="v1",
                recommendation_policy_version="v1",
                offer_range_policy_version="v1",
                confidence_policy_version="v1",
                model="gpt-5-mini",
                traced=True,
                trace_metadata={
                    "request_id": request_id,
                    "analysis_id": analysis_id or "",
                },
                started_at=started_at,
                completed_at=started_at,
                duration_ms=12,
                retry_count=0,
                validation_status="passed",
                warning_count=0,
            ),
            usage_metadata=CommitteeUsageMetadata(
                requests=1,
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                response_count=1,
            ),
            warnings=[],
        )


class PartialCommitteeService:
    async def analyze_with_details(
        self,
        *,
        request_id: str,
        committee_input: InvestmentCommitteeInput,
        analysis_id: str | None = None,
    ) -> InvestmentCommitteeAnalysisResult:
        assert "Expected rent is unsupported" in committee_input.agent_research.missing_information
        started_at = datetime.now(UTC)
        output = make_committee_output().model_copy(
            update={
                "recommendation": InvestmentRecommendation.INSUFFICIENT_INFORMATION,
                "recommendation_confidence": Decimal("0.35"),
                "recommendation_confidence_reasons": [
                    "base_research_confidence:0.80",
                    "decision_critical_missing:Expected rent is unsupported",
                ],
                "missing_information": [
                    CommitteeMissingItem(
                        item="Expected rent is unsupported",
                        materiality=MissingInformationMateriality.DECISION_CRITICAL,
                        importance=ReasonImportance.DECISIVE,
                        reason_needed="Rent support is needed for income validation.",
                        decision_impact="Unsupported rent blocks a responsible recommendation.",
                        recommended_source="Rental comparable research",
                        blocks_recommendation=True,
                    )
                ],
                "warnings": ["partial_upstream_information"],
            }
        )
        return InvestmentCommitteeAnalysisResult(
            output=output,
            execution_metadata=CommitteeExecutionMetadata(
                request_id=request_id,
                workflow_name="investment_committee",
                agent_version="investment_committee_agent:v1",
                prompt_version="v1",
                input_format_version="v1",
                recommendation_policy_version="v1",
                offer_range_policy_version="v1",
                confidence_policy_version="v1",
                model="gpt-5-mini",
                traced=True,
                trace_metadata={
                    "request_id": request_id,
                    "analysis_id": analysis_id or "",
                },
                started_at=started_at,
                completed_at=started_at,
                duration_ms=10,
                retry_count=0,
                validation_status="passed",
                warning_count=1,
            ),
            usage_metadata=CommitteeUsageMetadata(
                requests=1,
                input_tokens=75,
                output_tokens=35,
                total_tokens=110,
                response_count=1,
            ),
            warnings=["partial_upstream_information"],
        )


class BrokenCommitteeService:
    async def analyze_with_details(
        self,
        *,
        request_id: str,
        committee_input: InvestmentCommitteeInput,
        analysis_id: str | None = None,
    ) -> InvestmentCommitteeAnalysisResult:
        del request_id, committee_input, analysis_id
        raise AppError(
            code="committee_model_failure",
            message="Committee run failed.",
            status_code=502,
            retryable=True,
        )


def test_investment_committee_endpoint_returns_structured_result() -> None:
    app.dependency_overrides[get_investment_committee_service] = lambda: StubCommitteeService()
    try:
        response = client.post(
            "/api/v1/investment-committee/analyze",
            json=build_request().model_dump(mode="json"),
            headers={"X-Request-ID": "req-123"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["committee_output"]["recommendation"] == "negotiate"
    assert body["committee_output"]["recommendation_confidence_reasons"]
    assert body["execution_metadata"]["request_id"] == "req-123"
    assert body["execution_metadata"]["traced"] is True
    assert body["usage_metadata"]["total_tokens"] == 150
    assert response.headers["X-Request-ID"] == "req-123"


def test_investment_committee_endpoint_handles_partial_upstream_inputs() -> None:
    request = build_request()
    request.agent_research = request.agent_research.model_copy(
        update={"missing_information": ["Expected rent is unsupported"]}
    )
    app.dependency_overrides[get_investment_committee_service] = lambda: PartialCommitteeService()
    try:
        response = client.post(
            "/api/v1/investment-committee/analyze",
            json=request.model_dump(mode="json"),
            headers={"X-Request-ID": "req-456"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["committee_output"]["recommendation"] == "insufficient_information"
    assert body["committee_output"]["recommendation_confidence_reasons"]
    assert body["committee_output"]["missing_information"][0]["item"] == (
        "Expected rent is unsupported"
    )
    assert body["warnings"] == ["partial_upstream_information"]


def test_investment_committee_endpoint_returns_structured_error() -> None:
    app.dependency_overrides[get_investment_committee_service] = lambda: BrokenCommitteeService()
    try:
        response = client.post(
            "/api/v1/investment-committee/analyze",
            json=build_request().model_dump(mode="json"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json() == {
        "success": False,
        "error": {
            "code": "committee_model_failure",
            "message": "Committee run failed.",
            "retryable": True,
        },
    }
