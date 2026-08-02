"""Tests for strict agent-research contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.agent_research.models import (
    AgentExecutionMetadata,
    AgentFinding,
    AgentResearchOutput,
    ConflictMateriality,
    ConflictResolutionStatus,
    ConflictValue,
    EvidenceReference,
    EvidenceSourceType,
    FindingSeverity,
    ResearchConflict,
    UnifiedAgentResearchPackage,
)
from tests.agent_sdk_utils import make_agent_output, make_execution_metadata


def make_evidence_reference() -> EvidenceReference:
    return EvidenceReference(
        source_id="source-1",
        source_type=EvidenceSourceType.RESEARCH_SOURCE,
        citation_id="citation-1",
    )


def test_agent_finding_requires_evidence() -> None:
    with pytest.raises(ValidationError):
        AgentFinding(
            finding_id="finding-1",
            category="condition",
            title="Missing roof age",
            finding="Roof age is not disclosed.",
            significance="Could affect near-term capital expenditures.",
            severity=FindingSeverity.MEDIUM,
            confidence=Decimal("0.7"),
            evidence=[],
            is_inference=True,
        )


def test_evidence_reference_requires_locator() -> None:
    with pytest.raises(ValidationError):
        EvidenceReference(
            source_id="source-1",
            source_type=EvidenceSourceType.RESEARCH_SOURCE,
        )


def test_unified_package_accepts_strict_structured_outputs() -> None:
    output = make_agent_output()
    conflict = ResearchConflict(
        conflict_id="conflict-1",
        field_or_topic="year_built",
        values=[
            ConflictValue(
                value=1999,
                source_id="listing_source",
                source_type="listing",
                confidence=Decimal("0.60"),
            ),
            ConflictValue(
                value=2001,
                source_id="records_source",
                source_type="public_records",
                confidence=Decimal("0.85"),
            ),
        ],
        materiality=ConflictMateriality.MEDIUM,
        resolution_status=ConflictResolutionStatus.UNRESOLVED,
        requires_user_review=True,
    )

    package = UnifiedAgentResearchPackage(
        listing_analysis=output,
        public_records_analysis=make_agent_output("public_records_agent"),
        comparable_analysis=make_agent_output("comparable_agent"),
        neighborhood_analysis=make_agent_output("neighborhood_agent"),
        risk_analysis=make_agent_output("property_risk_agent"),
        consolidated_findings=[
            AgentFinding(
                finding_id="finding-1",
                category="records",
                title="Year built differs",
                finding="Listing year built differs from public records.",
                significance="The discrepancy requires confirmation before analysis proceeds.",
                severity=FindingSeverity.MEDIUM,
                confidence=Decimal("0.75"),
                evidence=[make_evidence_reference()],
                affected_fields=["year_built"],
                missing_information=["authoritative year built"],
                recommended_next_actions=["Confirm year built with county assessor records."],
                is_inference=False,
            )
        ],
        conflicts=[conflict],
        evidence_index=[make_evidence_reference()],
        overall_data_confidence=Decimal("0.78"),
        execution_metadata=make_execution_metadata(),
    )

    assert package.overall_data_confidence == Decimal("0.78")
    assert package.conflicts[0].requires_user_review is True


def test_agent_execution_metadata_rejects_negative_latency() -> None:
    started_at = datetime.now(UTC)
    with pytest.raises(ValidationError):
        AgentExecutionMetadata(
            request_id="req-123",
            workflow_name="real_estate_agent_research",
            workflow_version="v1",
            prompt_version="v1",
            model_name="gpt-5-mini",
            started_at=started_at,
            completed_at=started_at,
            total_duration_ms=1,
            agent_latencies_ms={"listing_agent": -1},
        )


def test_agent_output_rejects_confidence_above_one() -> None:
    with pytest.raises(ValidationError):
        AgentResearchOutput(
            agent_name="listing_agent",
            agent_version="listing_agent:v1",
            prompt_version="v1",
            summary="Summary",
            overall_confidence=Decimal("1.01"),
        )
