"""Tests for evidence indexing, lookup, and validation rules."""

from __future__ import annotations

import pytest

from app.agent_research.evidence import (
    build_evidence_index,
    build_property_key,
    citation_ids_for_source_ids,
    source_ids_for_label,
    validate_evidence_reference,
    validate_evidence_references,
    validate_source_ownership,
)
from app.agent_research.exceptions import EvidenceValidationFailureError
from app.agent_research.models import EvidenceReference, EvidenceSourceType
from tests.agent_sdk_utils import make_agent_context


def test_build_evidence_index_collects_sources_and_citations() -> None:
    context = make_agent_context()

    index = build_evidence_index(context)
    public_record_sources = source_ids_for_label(index, "research:public_records:source:")

    assert index.property_key == build_property_key(context.verified_property)
    assert public_record_sources
    assert citation_ids_for_source_ids(index, public_record_sources)
    assert "verified_property.full_address.final_value" in index.field_paths


def test_validate_evidence_reference_accepts_valid_verified_property_reference() -> None:
    context = make_agent_context()
    index = build_evidence_index(context)
    reference = EvidenceReference(
        source_id=f"{index.property_key}:verified_property",
        source_type=EvidenceSourceType.VERIFIED_PROPERTY,
        field_path="verified_property.asking_price.final_value",
    )

    validate_evidence_reference(reference, index)


def test_validate_evidence_references_rejects_cross_property_source() -> None:
    context = make_agent_context()
    index = build_evidence_index(context)
    reference = EvidenceReference(
        source_id="property:someone_else:verified_property",
        source_type=EvidenceSourceType.VERIFIED_PROPERTY,
        field_path="verified_property.asking_price.final_value",
    )

    with pytest.raises(EvidenceValidationFailureError):
        validate_source_ownership(reference.source_id, index)


def test_validate_evidence_reference_rejects_missing_citation() -> None:
    context = make_agent_context()
    index = build_evidence_index(context)
    public_record_source = source_ids_for_label(index, "research:public_records:source:")[0]
    reference = EvidenceReference(
        source_id=public_record_source,
        source_type=EvidenceSourceType.RESEARCH_SOURCE,
        citation_id=f"{public_record_source}:citation:999",
    )

    with pytest.raises(EvidenceValidationFailureError):
        validate_evidence_reference(reference, index)


def test_validate_evidence_references_rejects_invalid_field_path() -> None:
    context = make_agent_context()
    index = build_evidence_index(context)
    reference = EvidenceReference(
        source_id=f"{index.property_key}:underwriting",
        source_type=EvidenceSourceType.UNDERWRITING,
        field_path="underwriting.made_up.metric",
    )

    with pytest.raises(EvidenceValidationFailureError):
        validate_evidence_references([reference], index)
