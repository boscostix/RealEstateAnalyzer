"""API routes for investment-committee analysis."""

import time

from fastapi import APIRouter, Depends, Request, status

from app.investment_committee.api_models import (
    InvestmentCommitteeAnalyzeRequest,
    InvestmentCommitteeAnalyzeResponse,
)
from app.investment_committee.models import InvestmentCommitteeInput
from app.investment_committee.services import InvestmentCommitteeService
from app.logging import logger

router = APIRouter()


def get_investment_committee_service() -> InvestmentCommitteeService:
    return InvestmentCommitteeService()


investment_committee_service_dependency = Depends(get_investment_committee_service)


@router.post(
    "/api/v1/investment-committee/analyze",
    response_model=InvestmentCommitteeAnalyzeResponse,
    status_code=status.HTTP_200_OK,
)
async def analyze_investment_committee(
    request: Request,
    payload: InvestmentCommitteeAnalyzeRequest,
    service: InvestmentCommitteeService = investment_committee_service_dependency,
) -> InvestmentCommitteeAnalyzeResponse:
    started_at = time.perf_counter()
    request_id = getattr(request.state, "request_id", "unknown")
    committee_input = InvestmentCommitteeInput(
        property=payload.property,
        assumptions=payload.assumptions,
        underwriting=payload.underwriting,
        agent_research=payload.agent_research,
        decision_context=payload.decision_context,
    )
    result = await service.analyze_with_details(
        request_id=request_id,
        committee_input=committee_input,
        analysis_id=payload.analysis_id,
    )
    logger.info(
        "investment_committee_completed request_id=%s analysis_id=%s recommendation=%s "
        "confidence=%s warning_count=%s retry_count=%s duration_ms=%s",
        request_id,
        payload.analysis_id,
        result.output.recommendation,
        result.output.recommendation_confidence,
        len(result.warnings),
        result.execution_metadata.retry_count,
        int((time.perf_counter() - started_at) * 1000),
    )
    return InvestmentCommitteeAnalyzeResponse(
        success=True,
        committee_output=result.output,
        execution_metadata=result.execution_metadata,
        usage_metadata=result.usage_metadata,
        warnings=result.warnings,
    )
