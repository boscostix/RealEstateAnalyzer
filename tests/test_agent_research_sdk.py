"""Tests for the mockable OpenAI Agents SDK wrapper."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.agent_research.config import AgentRuntimeConfig
from app.agent_research.context import AgentRunContext, ResearchServiceContainer
from app.agent_research.definitions import build_specialist_agents
from app.agent_research.exceptions import InvalidStructuredAgentOutputError
from app.agent_research.sdk import OpenAIAgentRunner
from app.agent_research.tracing import build_run_config
from app.agent_research.versioning import AgentName
from app.models.public_records import (
    BuildingCharacteristics,
    BuildingValidation,
    FloodZoneInfo,
    OwnershipRecord,
    ParcelInfo,
    PublicRecordsData,
    TaxHistoryRecord,
    ValidationComparison,
)
from app.models.research import (
    CacheStatus,
    ConfidenceScore,
    ResearchDomain,
    ResearchField,
    ResearchMetadata,
    ResearchResult,
)
from app.models.research_package import ResearchPackage, ResearchPackageMetadata
from app.models.verification import VerificationStatus, VerifiedField, VerifiedPropertySnapshot
from tests.agent_sdk_utils import MockRunResult, make_agent_output


def make_context() -> AgentRunContext:
    retrieved_at = datetime.now(UTC)
    property_snapshot = VerifiedPropertySnapshot(
        source_url="https://example.com/listing",
        provider="zillow",
        full_address=VerifiedField(
            extracted_value="123 Main St, Dallas, TX 75001",
            final_value="123 Main St, Dallas, TX 75001",
            status=VerificationStatus.VERIFIED,
            source="user",
            confidence=Decimal("1"),
        ),
        asking_price=VerifiedField(
            extracted_value=Decimal("300000"),
            final_value=Decimal("300000"),
            status=VerificationStatus.VERIFIED,
            source="user",
            confidence=Decimal("1"),
        ),
        bedrooms=VerifiedField(
            extracted_value=Decimal("3"),
            final_value=Decimal("3"),
            status=VerificationStatus.VERIFIED,
            source="user",
            confidence=Decimal("1"),
        ),
        bathrooms=VerifiedField(
            extracted_value=Decimal("2"),
            final_value=Decimal("2"),
            status=VerificationStatus.VERIFIED,
            source="user",
            confidence=Decimal("1"),
        ),
        square_feet=VerifiedField(
            extracted_value=1800,
            final_value=1800,
            status=VerificationStatus.VERIFIED,
            source="user",
            confidence=Decimal("1"),
        ),
    )
    public_records_data = PublicRecordsData(
        tax_history=ResearchField[list[TaxHistoryRecord]](
            value=[],
            confidence=ConfidenceScore(value=Decimal("0")),
        ),
        assessed_value=ResearchField[Decimal | None](
            value=Decimal("285000"),
            confidence=ConfidenceScore(value=Decimal("0.8")),
        ),
        ownership=ResearchField[list[OwnershipRecord]](
            value=[],
            confidence=ConfidenceScore(value=Decimal("0")),
        ),
        parcel=ResearchField[ParcelInfo | None](
            value=ParcelInfo(parcel_number="123"),
            confidence=ConfidenceScore(value=Decimal("0.8")),
        ),
        flood_zone=ResearchField[FloodZoneInfo | None](
            value=FloodZoneInfo(flood_zone="X"),
            confidence=ConfidenceScore(value=Decimal("0.7")),
        ),
        building_characteristics=ResearchField[BuildingCharacteristics | None](
            value=BuildingCharacteristics(square_feet=1800, year_built=1999),
            confidence=ConfidenceScore(value=Decimal("0.8")),
        ),
        validations=ResearchField[BuildingValidation | None](
            value=BuildingValidation(
                year_built=ValidationComparison[int](
                    listing_value=1999, public_record_value=1999, matches=True
                ),
                square_feet=ValidationComparison[int](
                    listing_value=1800, public_record_value=1800, matches=True
                ),
            ),
            confidence=ConfidenceScore(value=Decimal("0.9")),
        ),
    )
    public_records_result = ResearchResult[PublicRecordsData](
        provider="county_records",
        retrieved_at=retrieved_at,
        metadata=ResearchMetadata(
            provider="county_records",
            domain=ResearchDomain.PUBLIC_RECORDS,
            retrieved_at=retrieved_at,
            provider_latency_ms=12,
            cache_status=CacheStatus.MISS,
        ),
        confidence=ConfidenceScore(value=Decimal("0.8")),
        data=public_records_data,
    )
    package = ResearchPackage(
        property=property_snapshot,
        public_records=public_records_result,
        metadata=ResearchPackageMetadata(total_duration_ms=12),
    )
    return AgentRunContext(
        request_id="req-123",
        analysis_id="analysis-1",
        verified_property=property_snapshot,
        underwriting_result=None,
        research_package=package,
        research_services=ResearchServiceContainer(),
        agent_config=AgentRuntimeConfig(),
    )


@pytest.mark.asyncio
async def test_openai_agent_runner_uses_runner_run(monkeypatch: pytest.MonkeyPatch) -> None:
    context = make_context()
    agents = build_specialist_agents(context.agent_config.model)
    expected_output = make_agent_output()

    async def fake_run(*args: object, **kwargs: object) -> MockRunResult:
        assert args[0] is agents[AgentName.LISTING]
        assert args[1] == "Summarize the listing."
        assert kwargs["context"] is context
        return MockRunResult(expected_output)

    from agents import Runner

    monkeypatch.setattr(Runner, "run", fake_run)

    runner = OpenAIAgentRunner()
    result = await runner.run(
        agent=agents[AgentName.LISTING],
        agent_input="Summarize the listing.",
        context=context,
        run_config=build_run_config(context.agent_config, request_id=context.request_id),
        output_type=type(expected_output),
    )

    assert result == expected_output


@pytest.mark.asyncio
async def test_openai_agent_runner_raises_structured_output_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = make_context()
    agents = build_specialist_agents(context.agent_config.model)

    async def fake_run(*args: object, **kwargs: object) -> MockRunResult:
        return MockRunResult({"not": "structured"})

    from agents import Runner

    monkeypatch.setattr(Runner, "run", fake_run)

    runner = OpenAIAgentRunner()
    with pytest.raises(InvalidStructuredAgentOutputError):
        await runner.run(
            agent=agents[AgentName.LISTING],
            agent_input="Summarize the listing.",
            context=context,
            run_config=build_run_config(context.agent_config, request_id=context.request_id),
            output_type=type(make_agent_output()),
        )
