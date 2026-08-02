"""Tests for deterministic conflict detection and confidence adjustment."""

from __future__ import annotations

from decimal import Decimal

from app.agent_research.conflicts import analyze_conflicts
from app.agent_research.models import (
    AgentConflictCandidate,
    AgentFinding,
    ConflictMateriality,
    ConflictResolutionStatus,
    EvidenceReference,
    EvidenceSourceType,
    FindingSeverity,
)
from app.models.verification import VerificationStatus, VerifiedField
from tests.agent_sdk_utils import (
    make_agent_context,
    make_comparable_agent_output,
    make_listing_agent_output,
    make_neighborhood_agent_output,
    make_public_records_agent_output,
)


def _evidence() -> list[EvidenceReference]:
    return [
        EvidenceReference(
            source_id="verified_property",
            source_type=EvidenceSourceType.VERIFIED_PROPERTY,
            field_path="verified_property.square_feet.final_value",
        )
    ]


def test_conflict_analysis_applies_verified_value_precedence() -> None:
    context = make_agent_context()
    context.verified_property.square_feet = VerifiedField[int](
        extracted_value=1800,
        final_value=1825,
        status=VerificationStatus.VERIFIED,
        source="user",
        confidence=Decimal("1"),
    )
    assert context.listing_extraction is not None
    context.listing_extraction.property.square_feet = 1800

    result = analyze_conflicts(
        verified_property=context.verified_property,
        listing_extraction=context.listing_extraction,
        research_package=context.research_package,
        listing_analysis=make_listing_agent_output(),
        public_records_analysis=make_public_records_agent_output(),
        comparable_analysis=make_comparable_agent_output(),
        neighborhood_analysis=make_neighborhood_agent_output(),
    )

    square_feet_conflict = next(
        conflict for conflict in result.conflicts if conflict.field_or_topic == "square_feet"
    )
    assert square_feet_conflict.resolution_status == (
        ConflictResolutionStatus.RESOLVED_DETERMINISTICALLY
    )
    assert square_feet_conflict.preferred_value == 1825
    assert square_feet_conflict.preferred_source_id == "verified_property"
    assert square_feet_conflict.source_precedence_applied is True
    assert len(square_feet_conflict.values) == 3


def test_conflict_analysis_preserves_unresolved_semantic_agent_conflicts() -> None:
    context = make_agent_context()
    listing_output = make_listing_agent_output()
    listing_output.conflicts = [
        AgentConflictCandidate(
            field_or_topic="roof_condition",
            values_or_claims=["Roof appears newer", "Roof age is unknown"],
            source_ids=["listing_extraction", "public_records"],
            description="Listing language and records disagree on roof age support.",
            materiality=ConflictMateriality.MEDIUM,
        )
    ]

    result = analyze_conflicts(
        verified_property=context.verified_property,
        listing_extraction=context.listing_extraction,
        research_package=context.research_package,
        listing_analysis=listing_output,
        public_records_analysis=make_public_records_agent_output(),
        comparable_analysis=make_comparable_agent_output(),
        neighborhood_analysis=make_neighborhood_agent_output(),
    )

    roof_conflict = next(
        conflict for conflict in result.conflicts if conflict.field_or_topic == "roof_condition"
    )
    assert roof_conflict.resolution_status == ConflictResolutionStatus.UNRESOLVED
    assert roof_conflict.requires_synthesis is True
    assert roof_conflict.requires_user_review is True
    assert [value.value for value in roof_conflict.values] == [
        "Roof appears newer",
        "Roof age is unknown",
    ]


def test_conflict_analysis_prefers_authoritative_public_records_when_unverified() -> None:
    context = make_agent_context()
    context.verified_property.year_built = VerifiedField[int](
        extracted_value=None,
        final_value=None,
        status=VerificationStatus.MISSING,
    )
    assert context.listing_extraction is not None
    context.listing_extraction.property.year_built = 2001

    result = analyze_conflicts(
        verified_property=context.verified_property,
        listing_extraction=context.listing_extraction,
        research_package=context.research_package,
        listing_analysis=make_listing_agent_output(),
        public_records_analysis=make_public_records_agent_output(),
        comparable_analysis=make_comparable_agent_output(),
        neighborhood_analysis=make_neighborhood_agent_output(),
    )

    year_built_conflict = next(
        conflict for conflict in result.conflicts if conflict.field_or_topic == "year_built"
    )
    assert year_built_conflict.resolution_status == (
        ConflictResolutionStatus.RESOLVED_DETERMINISTICALLY
    )
    assert year_built_conflict.preferred_value == 1999
    assert year_built_conflict.preferred_source_id == "public_records"


def test_conflict_analysis_detects_duplicate_findings() -> None:
    context = make_agent_context()
    duplicate_finding = AgentFinding(
        finding_id="finding-1",
        category="condition",
        title="Roof age missing",
        finding="Roof age is not documented in the available data.",
        significance="The roof may require near-term capex confirmation.",
        severity=FindingSeverity.MEDIUM,
        confidence=Decimal("0.70"),
        evidence=_evidence(),
        affected_fields=["roof_type"],
        is_inference=True,
    )
    listing_output = make_listing_agent_output()
    public_records_output = make_public_records_agent_output()
    listing_output.findings = [duplicate_finding]
    public_records_output.findings = [
        duplicate_finding.model_copy(update={"finding_id": "finding-2"})
    ]

    result = analyze_conflicts(
        verified_property=context.verified_property,
        listing_extraction=context.listing_extraction,
        research_package=context.research_package,
        listing_analysis=listing_output,
        public_records_analysis=public_records_output,
        comparable_analysis=make_comparable_agent_output(),
        neighborhood_analysis=make_neighborhood_agent_output(),
    )

    assert len(result.duplicate_findings) == 1
    duplicate_group = result.duplicate_findings[0]
    assert duplicate_group.canonical_finding_id == "finding-1"
    assert duplicate_group.duplicate_finding_ids == ["finding-2"]
    assert duplicate_group.agent_names == ["listing_agent", "public_records_agent"]


def test_conflict_analysis_caps_and_reduces_agent_confidence() -> None:
    context = make_agent_context()
    listing_output = make_listing_agent_output()
    listing_output.overall_confidence = Decimal("0.99")
    listing_output.findings = [
        AgentFinding(
            finding_id="finding-1",
            category="listing",
            title="Single support point",
            finding="Only one evidence point supports this finding.",
            significance="Confidence should be capped and then reduced.",
            severity=FindingSeverity.MEDIUM,
            confidence=Decimal("0.80"),
            evidence=_evidence(),
            affected_fields=["square_feet"],
            is_inference=True,
        )
    ]
    listing_output.conflicts = [
        AgentConflictCandidate(
            field_or_topic="roof_condition",
            values_or_claims=["Roof appears newer", "Roof age is unknown"],
            source_ids=["listing_extraction", "public_records"],
            description="Semantic disagreement remains unresolved.",
            materiality=ConflictMateriality.HIGH,
        )
    ]

    result = analyze_conflicts(
        verified_property=context.verified_property,
        listing_extraction=context.listing_extraction,
        research_package=context.research_package,
        listing_analysis=listing_output,
        public_records_analysis=make_public_records_agent_output(),
        comparable_analysis=make_comparable_agent_output(),
        neighborhood_analysis=make_neighborhood_agent_output(),
    )

    assert result.adjusted_agent_confidences["listing_agent"] == Decimal("0.75")
    assert result.overall_data_confidence < Decimal("0.75")
