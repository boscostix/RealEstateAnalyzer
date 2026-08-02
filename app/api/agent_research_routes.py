"""API routes for unified structured agent research runs."""

import time

from fastapi import APIRouter, Depends, Request, status

from app.agent_research.api_models import AgentResearchRunRequest, AgentResearchRunResponse
from app.agent_research.synthesis import UnifiedSynthesisService
from app.logging import logger

router = APIRouter()


def get_unified_synthesis_service() -> UnifiedSynthesisService:
    return UnifiedSynthesisService()


unified_synthesis_service_dependency = Depends(get_unified_synthesis_service)


@router.post(
    "/api/v1/agent-research/run",
    response_model=AgentResearchRunResponse,
    status_code=status.HTTP_200_OK,
)
async def run_agent_research(
    request: Request,
    payload: AgentResearchRunRequest,
    service: UnifiedSynthesisService = unified_synthesis_service_dependency,
) -> AgentResearchRunResponse:
    started_at = time.perf_counter()
    request_id = getattr(request.state, "request_id", "unknown")
    response = await service.run(request_id=request_id, payload=payload)
    logger.info(
        "agent_research_completed request_id=%s success=%s partial_failure=%s "
        "conflict_count=%s warning_count=%s duration_ms=%s",
        request_id,
        response.success,
        False if response.package is None else response.package.execution_metadata.partial_failure,
        0 if response.package is None else len(response.package.conflicts),
        len(response.warnings),
        int((time.perf_counter() - started_at) * 1000),
    )
    return response
