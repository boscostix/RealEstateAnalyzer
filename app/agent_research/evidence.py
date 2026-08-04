"""Deterministic evidence indexing and validation for agent outputs."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import Field

from app.agent_research.context import AgentRunContext
from app.agent_research.exceptions import EvidenceValidationFailureError
from app.agent_research.models import AgentModel, EvidenceReference, EvidenceSourceType
from app.models.research import Citation, ResearchResult, Source
from app.models.verification import VerifiedPropertySnapshot


def build_property_key(property_snapshot: VerifiedPropertySnapshot) -> str:
    """Create a stable property identifier for evidence ownership checks."""

    fingerprint = "|".join(
        [
            property_snapshot.provider,
            property_snapshot.source_url,
            property_snapshot.full_address.final_value or "",
        ]
    )
    digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:16]
    return f"property:{digest}"


class EvidenceSourceRecord(AgentModel):
    """Normalized source lookup record for the current property analysis."""

    source_id: str
    property_key: str
    source_name: str
    source_url: str
    source_kind: str
    retrieved_at: datetime | None = None
    citation_ids: list[str] = Field(default_factory=list)


class EvidenceCitationRecord(AgentModel):
    """Normalized citation lookup record for the current property analysis."""

    citation_id: str
    source_id: str
    property_key: str
    source_name: str
    source_url: str
    note: str | None = None
    retrieved_at: datetime | None = None


@dataclass(slots=True)
class EvidenceIndex:
    """In-memory index of allowed evidence for one property analysis."""

    property_key: str
    sources: dict[str, EvidenceSourceRecord]
    citations: dict[str, EvidenceCitationRecord]
    field_paths: set[str]

    def lookup_source(self, source_id: str) -> EvidenceSourceRecord | None:
        return self.sources.get(source_id)

    def lookup_citation(self, citation_id: str) -> EvidenceCitationRecord | None:
        return self.citations.get(citation_id)


def _source_id(property_key: str, label: str) -> str:
    return f"{property_key}:{label}"


def _citation_key(citation: Citation) -> str:
    return "|".join(
        [
            citation.source_name,
            citation.source_url,
            citation.source_type,
            citation.note or "",
        ]
    )


def _iter_field_paths(node: Any, prefix: str) -> set[str]:
    field_paths = {prefix}
    if hasattr(node, "model_dump"):
        dumped = node.model_dump(mode="python")
        if isinstance(dumped, dict):
            for key, value in dumped.items():
                child_prefix = f"{prefix}.{key}"
                field_paths.update(_iter_field_paths(value, child_prefix))
        return field_paths
    if isinstance(node, dict):
        for key, value in node.items():
            field_paths.update(_iter_field_paths(value, f"{prefix}.{key}"))
        return field_paths
    if isinstance(node, list):
        for index, value in enumerate(node):
            field_paths.update(_iter_field_paths(value, f"{prefix}[{index}]"))
    return field_paths


def _unresolved_verified_fields(property_snapshot: VerifiedPropertySnapshot) -> list[str]:
    unresolved: list[str] = []
    for field_name, field_value in property_snapshot.model_dump(mode="python").items():
        if field_name in {"source_url", "provider"}:
            continue
        if isinstance(field_value, dict) and field_value.get("status") != "verified":
            unresolved.append(field_name)
    return unresolved


def _register_source(
    sources: dict[str, EvidenceSourceRecord],
    *,
    source_id: str,
    property_key: str,
    source_name: str,
    source_url: str,
    source_kind: str,
    retrieved_at: datetime | None,
) -> None:
    sources[source_id] = EvidenceSourceRecord(
        source_id=source_id,
        property_key=property_key,
        source_name=source_name,
        source_url=source_url,
        source_kind=source_kind,
        retrieved_at=retrieved_at,
        citation_ids=[],
    )


def _register_citations(
    index: EvidenceIndex,
    *,
    property_key: str,
    citations: list[Citation],
    source_id_lookup: dict[str, str],
) -> None:
    occurrence_counts: dict[str, int] = {}
    for citation in citations:
        key = _citation_key(citation)
        occurrence = occurrence_counts.get(key, 0)
        occurrence_counts[key] = occurrence + 1
        source_id = source_id_lookup.get(key)
        if source_id is None:
            source_id = _source_id(property_key, f"citation_source:{len(index.sources)}")
            _register_source(
                index.sources,
                source_id=source_id,
                property_key=property_key,
                source_name=citation.source_name,
                source_url=citation.source_url,
                source_kind="citation_only",
                retrieved_at=citation.retrieved_at,
            )
        citation_id = f"{source_id}:citation:{occurrence}"
        index.citations[citation_id] = EvidenceCitationRecord(
            citation_id=citation_id,
            source_id=source_id,
            property_key=property_key,
            source_name=citation.source_name,
            source_url=citation.source_url,
            note=citation.note,
            retrieved_at=citation.retrieved_at,
        )
        index.sources[source_id].citation_ids.append(citation_id)


def _index_research_result(
    index: EvidenceIndex,
    *,
    domain_name: str,
    result: ResearchResult[Any],
) -> None:
    source_id_lookup: dict[str, str] = {}
    for source_index, source in enumerate(result.sources):
        source_id = _source_id(index.property_key, f"research:{domain_name}:source:{source_index}")
        _register_source(
            index.sources,
            source_id=source_id,
            property_key=index.property_key,
            source_name=source.name,
            source_url=source.url,
            source_kind=source.type,
            retrieved_at=source.retrieved_at,
        )
        source_id_lookup[_citation_key_from_source(source)] = source_id
    _register_citations(
        index,
        property_key=index.property_key,
        citations=result.citations,
        source_id_lookup=source_id_lookup,
    )


def _citation_key_from_source(source: Source) -> str:
    return "|".join([source.name, source.url, source.type, ""])


def source_ids_for_label(index: EvidenceIndex, label: str) -> list[str]:
    """Return source IDs matching one deterministic label prefix."""

    prefix = f"{index.property_key}:{label}"
    return sorted(source_id for source_id in index.sources if source_id.startswith(prefix))


def citation_ids_for_source_ids(index: EvidenceIndex, source_ids: list[str]) -> list[str]:
    """Return citation IDs attached to the provided source IDs."""

    citation_ids: list[str] = []
    for source_id in source_ids:
        source = index.lookup_source(source_id)
        if source is not None:
            citation_ids.extend(source.citation_ids)
    return sorted(citation_ids)


def build_evidence_index(context: AgentRunContext) -> EvidenceIndex:
    """Build a deterministic evidence index from the current run context."""

    property_key = build_property_key(context.verified_property)
    index = EvidenceIndex(property_key=property_key, sources={}, citations={}, field_paths=set())

    verified_source_id = _source_id(property_key, "verified_property")
    _register_source(
        index.sources,
        source_id=verified_source_id,
        property_key=property_key,
        source_name="Verified Property Snapshot",
        source_url=context.verified_property.source_url,
        source_kind=EvidenceSourceType.VERIFIED_PROPERTY,
        retrieved_at=None,
    )
    index.field_paths.update(_iter_field_paths(context.verified_property, "verified_property"))
    index.field_paths.update(
        _iter_field_paths(
            _unresolved_verified_fields(context.verified_property),
            "unresolved_verified_fields",
        )
    )

    if context.listing_extraction is not None:
        listing_source_id = _source_id(property_key, "listing_extraction")
        _register_source(
            index.sources,
            source_id=listing_source_id,
            property_key=property_key,
            source_name="Listing Extraction",
            source_url=context.listing_extraction.source_url,
            source_kind="listing_extraction",
            retrieved_at=context.listing_extraction.metadata.retrieved_at,
        )
        index.field_paths.update(
            _iter_field_paths(context.listing_extraction.property, "listing.property")
        )
        index.field_paths.update(
            _iter_field_paths(context.listing_extraction.property, "listing_snapshot.property")
        )
        index.field_paths.update(
            _iter_field_paths(
                context.listing_extraction.field_provenance, "listing.field_provenance"
            )
        )
        index.field_paths.update(
            _iter_field_paths(
                context.listing_extraction.field_provenance, "listing_snapshot.field_provenance"
            )
        )
        index.field_paths.update(
            _iter_field_paths(context.listing_extraction.metadata, "listing_snapshot.metadata")
        )
        index.field_paths.update(
            _iter_field_paths(
                context.listing_extraction.property.price_history,
                "listing_history.price_history",
            )
        )
        index.field_paths.update(
            _iter_field_paths(
                context.listing_extraction.property.sale_history,
                "listing_history.sale_history",
            )
        )

    if context.underwriting_result is not None:
        underwriting_source_id = _source_id(property_key, "underwriting")
        _register_source(
            index.sources,
            source_id=underwriting_source_id,
            property_key=property_key,
            source_name="Deterministic Underwriting",
            source_url=context.verified_property.source_url,
            source_kind=EvidenceSourceType.UNDERWRITING,
            retrieved_at=None,
        )
        index.field_paths.update(_iter_field_paths(context.underwriting_result, "underwriting"))

    package = context.research_package
    for domain_name, result in (
        ("public_records", package.public_records),
        ("sales_comps", package.sales_comps),
        ("rental_comps", package.rental_comps),
        ("neighborhood", package.neighborhood),
    ):
        if result is not None:
            _index_research_result(index, domain_name=domain_name, result=result)

    return index


def validate_source_ownership(source_id: str, index: EvidenceIndex) -> None:
    """Reject references that belong to another property analysis."""

    if not source_id.startswith(index.property_key):
        raise EvidenceValidationFailureError(
            message="Evidence source does not belong to the current property analysis.",
        )


def _candidate_field_paths(raw_path: str) -> list[str]:
    candidates: list[str] = []
    path = raw_path.strip()
    if not path:
        return candidates
    candidates.append(path)
    if path.startswith("property."):
        candidates.append(f"listing.property.{path.removeprefix('property.')}")
        candidates.append(f"listing_snapshot.property.{path.removeprefix('property.')}")
        candidates.append(f"verified_property.{path.removeprefix('property.')}")
    elif path.startswith("field_provenance."):
        suffix = path.removeprefix("field_provenance.")
        candidates.append(f"listing.field_provenance.{suffix}")
        candidates.append(f"listing_snapshot.field_provenance.{suffix}")
    elif path.startswith("metadata."):
        candidates.append(f"listing_snapshot.{path}")
    elif path.startswith("price_history.") or path.startswith("sale_history."):
        candidates.append(f"listing_history.{path}")
    return candidates


def _split_field_paths(field_path: str | None) -> list[str]:
    if field_path is None:
        return []
    return [part.strip() for part in re.split(r"\s*(?:,|/)\s*", field_path) if part.strip()]


def validate_evidence_reference(reference: EvidenceReference, index: EvidenceIndex) -> None:
    """Validate one evidence reference against the current evidence index."""

    validate_source_ownership(reference.source_id, index)
    source = index.lookup_source(reference.source_id)
    if source is None:
        raise EvidenceValidationFailureError(message="Referenced source_id is not available.")

    if reference.citation_id is not None:
        citation = index.lookup_citation(reference.citation_id)
        if citation is None:
            raise EvidenceValidationFailureError(message="Referenced citation_id is not available.")
        if citation.source_id != source.source_id:
            raise EvidenceValidationFailureError(
                message="Referenced citation_id does not belong to the provided source_id.",
            )

    if reference.field_path is not None and not all(
        any(candidate in index.field_paths for candidate in _candidate_field_paths(reference_path))
        for reference_path in _split_field_paths(reference.field_path)
    ):
        raise EvidenceValidationFailureError(
            message=(
                "Referenced field_path is not available: "
                f"{reference.field_path} (source_id={reference.source_id})"
            )
        )

    source_kind = str(source.source_kind)

    if source_kind == str(EvidenceSourceType.VERIFIED_PROPERTY) and (
        reference.field_path is None
        or not any(
            candidate.startswith("verified_property")
            for reference_path in _split_field_paths(reference.field_path)
            for candidate in _candidate_field_paths(reference_path)
        )
    ):
        raise EvidenceValidationFailureError(
            message=(
                "Verified-property evidence must reference a verified_property field path: "
                f"{reference.field_path} (source_id={reference.source_id})"
            ),
        )
    if source_kind == str(EvidenceSourceType.UNDERWRITING) and (
        reference.field_path is None or not reference.field_path.startswith("underwriting")
    ):
        raise EvidenceValidationFailureError(
            message="Underwriting evidence must reference an underwriting field path.",
        )


def validate_evidence_references(
    references: list[EvidenceReference],
    index: EvidenceIndex,
) -> None:
    """Validate a batch of references against the current property evidence index."""

    for reference in references:
        validate_evidence_reference(reference, index)
