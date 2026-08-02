"""Deterministic conflict detection and confidence adjustment utilities."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.agent_research.guardrails import bounded_confidence_limit
from app.agent_research.models import (
    AgentFinding,
    AgentResearchOutput,
    ConflictMateriality,
    ConflictResolutionStatus,
    ConflictValue,
    DuplicateFindingGroup,
    ResearchConflict,
)
from app.models.extraction import PropertyExtractionResult
from app.models.research import SourceType
from app.models.research_package import ResearchPackage
from app.models.verification import VerificationStatus, VerifiedField, VerifiedPropertySnapshot

_DECIMAL_ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class ConflictAnalysisResult:
    """Deterministic conflict-analysis output for later synthesis layers."""

    conflicts: list[ResearchConflict]
    duplicate_findings: list[DuplicateFindingGroup]
    adjusted_agent_confidences: dict[str, Decimal]
    overall_data_confidence: Decimal
    warnings: list[str]


@dataclass(frozen=True, slots=True)
class _ConflictCandidateValue:
    value: Any
    normalized_value: str
    source_id: str
    source_type: str
    confidence: Decimal
    label: str | None = None
    field_path: str | None = None
    agent_name: str | None = None
    authoritative: bool = False
    verified: bool = False
    retrieved_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class _FieldConflictSpec:
    field_or_topic: str
    materiality: ConflictMateriality
    listing_attr: str | None = None
    verified_attr: str | None = None
    public_record_path: tuple[str, ...] | None = None


FIELD_CONFLICT_SPECS: tuple[_FieldConflictSpec, ...] = (
    _FieldConflictSpec(
        field_or_topic="asking_price",
        materiality=ConflictMateriality.HIGH,
        listing_attr="asking_price",
        verified_attr="asking_price",
    ),
    _FieldConflictSpec(
        field_or_topic="bedrooms",
        materiality=ConflictMateriality.MEDIUM,
        listing_attr="bedrooms",
        verified_attr="bedrooms",
        public_record_path=("building_characteristics", "bedrooms"),
    ),
    _FieldConflictSpec(
        field_or_topic="bathrooms",
        materiality=ConflictMateriality.MEDIUM,
        listing_attr="bathrooms",
        verified_attr="bathrooms",
        public_record_path=("building_characteristics", "bathrooms"),
    ),
    _FieldConflictSpec(
        field_or_topic="square_feet",
        materiality=ConflictMateriality.HIGH,
        listing_attr="square_feet",
        verified_attr="square_feet",
        public_record_path=("building_characteristics", "square_feet"),
    ),
    _FieldConflictSpec(
        field_or_topic="lot_square_feet",
        materiality=ConflictMateriality.MEDIUM,
        listing_attr="lot_square_feet",
        verified_attr="lot_square_feet",
        public_record_path=("parcel", "lot_square_feet"),
    ),
    _FieldConflictSpec(
        field_or_topic="year_built",
        materiality=ConflictMateriality.HIGH,
        listing_attr="year_built",
        verified_attr="year_built",
        public_record_path=("building_characteristics", "year_built"),
    ),
    _FieldConflictSpec(
        field_or_topic="property_type",
        materiality=ConflictMateriality.MEDIUM,
        listing_attr="property_type",
        verified_attr="property_type",
        public_record_path=("building_characteristics", "property_type"),
    ),
)

_MATERIALITY_PENALTIES = {
    ConflictMateriality.LOW: Decimal("0.02"),
    ConflictMateriality.MEDIUM: Decimal("0.05"),
    ConflictMateriality.HIGH: Decimal("0.10"),
}


def bounded_decimal(value: Decimal) -> Decimal:
    """Clamp confidence-style decimals to the closed interval [0, 1]."""

    if value < _DECIMAL_ZERO:
        return _DECIMAL_ZERO
    if value > Decimal("1"):
        return Decimal("1")
    return value


def analyze_conflicts(
    *,
    verified_property: VerifiedPropertySnapshot,
    listing_extraction: PropertyExtractionResult | None,
    research_package: ResearchPackage,
    listing_analysis: AgentResearchOutput,
    public_records_analysis: AgentResearchOutput,
    comparable_analysis: AgentResearchOutput,
    neighborhood_analysis: AgentResearchOutput,
) -> ConflictAnalysisResult:
    """Detect deterministic conflicts, duplicate findings, and confidence adjustments."""

    source_conflicts = _detect_source_conflicts(
        verified_property=verified_property,
        listing_extraction=listing_extraction,
        research_package=research_package,
    )
    agent_conflicts = _detect_agent_conflicts(
        listing_analysis=listing_analysis,
        public_records_analysis=public_records_analysis,
        comparable_analysis=comparable_analysis,
        neighborhood_analysis=neighborhood_analysis,
    )
    conflicts = sorted(
        [*source_conflicts, *agent_conflicts],
        key=lambda conflict: (conflict.field_or_topic, conflict.conflict_id),
    )
    duplicate_findings = _detect_duplicate_findings(
        listing_analysis=listing_analysis,
        public_records_analysis=public_records_analysis,
        comparable_analysis=comparable_analysis,
        neighborhood_analysis=neighborhood_analysis,
    )
    adjusted_agent_confidences = _adjust_agent_confidences(
        listing_analysis=listing_analysis,
        public_records_analysis=public_records_analysis,
        comparable_analysis=comparable_analysis,
        neighborhood_analysis=neighborhood_analysis,
        conflicts=conflicts,
        duplicate_findings=duplicate_findings,
    )
    overall_data_confidence = _overall_confidence(adjusted_agent_confidences, conflicts)
    warnings = [
        f"unresolved_conflict:{conflict.field_or_topic}"
        for conflict in conflicts
        if conflict.resolution_status != ConflictResolutionStatus.RESOLVED_DETERMINISTICALLY
    ]
    return ConflictAnalysisResult(
        conflicts=conflicts,
        duplicate_findings=duplicate_findings,
        adjusted_agent_confidences=adjusted_agent_confidences,
        overall_data_confidence=overall_data_confidence,
        warnings=warnings,
    )


def _detect_source_conflicts(
    *,
    verified_property: VerifiedPropertySnapshot,
    listing_extraction: PropertyExtractionResult | None,
    research_package: ResearchPackage,
) -> list[ResearchConflict]:
    conflicts: list[ResearchConflict] = []
    for spec in FIELD_CONFLICT_SPECS:
        candidates: list[_ConflictCandidateValue] = []
        verified_candidate = _verified_candidate(verified_property, spec)
        if verified_candidate is not None:
            candidates.append(verified_candidate)
        listing_candidate = _listing_candidate(listing_extraction, spec)
        if listing_candidate is not None:
            candidates.append(listing_candidate)
        public_records_candidate = _public_records_candidate(research_package, spec)
        if public_records_candidate is not None:
            candidates.append(public_records_candidate)
        conflict = _normalize_conflict(
            field_or_topic=spec.field_or_topic,
            candidates=candidates,
            materiality=spec.materiality,
            semantic=False,
        )
        if conflict is not None:
            conflicts.append(conflict)
    return conflicts


def _detect_agent_conflicts(
    *,
    listing_analysis: AgentResearchOutput,
    public_records_analysis: AgentResearchOutput,
    comparable_analysis: AgentResearchOutput,
    neighborhood_analysis: AgentResearchOutput,
) -> list[ResearchConflict]:
    conflicts: list[ResearchConflict] = []
    outputs = (
        listing_analysis,
        public_records_analysis,
        comparable_analysis,
        neighborhood_analysis,
    )
    for output in outputs:
        for candidate in output.conflicts:
            values = [
                _ConflictCandidateValue(
                    value=value,
                    normalized_value=_normalize_value(value),
                    source_id=source_id,
                    source_type="agent_claim",
                    confidence=output.overall_confidence,
                    label=candidate.field_or_topic,
                    field_path=candidate.field_or_topic,
                    agent_name=output.agent_name,
                )
                for value, source_id in zip(
                    candidate.values_or_claims,
                    candidate.source_ids,
                    strict=False,
                )
            ]
            conflict = _normalize_conflict(
                field_or_topic=candidate.field_or_topic,
                candidates=values,
                materiality=candidate.materiality,
                semantic=True,
                description=candidate.description,
            )
            if conflict is not None:
                conflicts.append(conflict)
    return conflicts


def _detect_duplicate_findings(
    *,
    listing_analysis: AgentResearchOutput,
    public_records_analysis: AgentResearchOutput,
    comparable_analysis: AgentResearchOutput,
    neighborhood_analysis: AgentResearchOutput,
) -> list[DuplicateFindingGroup]:
    by_signature: dict[str, list[tuple[str, AgentFinding]]] = defaultdict(list)
    for output in (
        listing_analysis,
        public_records_analysis,
        comparable_analysis,
        neighborhood_analysis,
    ):
        for finding in output.findings:
            by_signature[_finding_signature(finding)].append((output.agent_name, finding))

    duplicates: list[DuplicateFindingGroup] = []
    for signature, grouped_findings in sorted(by_signature.items()):
        if len(grouped_findings) < 2:
            continue
        canonical_agent_name, canonical_finding = grouped_findings[0]
        duplicate_finding_ids = [finding.finding_id for _, finding in grouped_findings[1:]]
        agent_names = [
            canonical_agent_name,
            *[agent_name for agent_name, _ in grouped_findings[1:]],
        ]
        duplicate_id = _stable_id(
            "duplicate",
            signature,
            "|".join(sorted(finding.finding_id for _, finding in grouped_findings)),
        )
        duplicates.append(
            DuplicateFindingGroup(
                duplicate_id=duplicate_id,
                canonical_finding_id=canonical_finding.finding_id,
                duplicate_finding_ids=duplicate_finding_ids,
                agent_names=agent_names,
                shared_signature=signature,
                requires_user_review=False,
            )
        )
    return duplicates


def _adjust_agent_confidences(
    *,
    listing_analysis: AgentResearchOutput,
    public_records_analysis: AgentResearchOutput,
    comparable_analysis: AgentResearchOutput,
    neighborhood_analysis: AgentResearchOutput,
    conflicts: list[ResearchConflict],
    duplicate_findings: list[DuplicateFindingGroup],
) -> dict[str, Decimal]:
    outputs = {
        listing_analysis.agent_name: listing_analysis,
        public_records_analysis.agent_name: public_records_analysis,
        comparable_analysis.agent_name: comparable_analysis,
        neighborhood_analysis.agent_name: neighborhood_analysis,
    }
    duplicate_penalties: dict[str, Decimal] = defaultdict(lambda: _DECIMAL_ZERO)
    for duplicate in duplicate_findings:
        for agent_name in duplicate.agent_names:
            duplicate_penalties[agent_name] += Decimal("0.03")

    conflict_penalties: dict[str, Decimal] = defaultdict(lambda: _DECIMAL_ZERO)
    for conflict in conflicts:
        if conflict.resolution_status == ConflictResolutionStatus.RESOLVED_DETERMINISTICALLY:
            continue
        penalty = _MATERIALITY_PENALTIES[conflict.materiality]
        involved_agents = {value.agent_name for value in conflict.values if value.agent_name}
        for agent_name in involved_agents:
            conflict_penalties[agent_name] += penalty

    adjusted: dict[str, Decimal] = {}
    for agent_name, output in outputs.items():
        capped = min(output.overall_confidence, bounded_confidence_limit(output))
        penalty = duplicate_penalties[agent_name] + conflict_penalties[agent_name]
        adjusted[agent_name] = bounded_decimal(capped - penalty)
    return adjusted


def _overall_confidence(
    adjusted_agent_confidences: dict[str, Decimal],
    conflicts: list[ResearchConflict],
) -> Decimal:
    if not adjusted_agent_confidences:
        return _DECIMAL_ZERO
    average = sum(adjusted_agent_confidences.values(), start=_DECIMAL_ZERO) / Decimal(
        len(adjusted_agent_confidences)
    )
    unresolved_penalty = sum(
        _MATERIALITY_PENALTIES[conflict.materiality]
        for conflict in conflicts
        if conflict.resolution_status != ConflictResolutionStatus.RESOLVED_DETERMINISTICALLY
    )
    return bounded_decimal(average - unresolved_penalty)


def _verified_candidate(
    verified_property: VerifiedPropertySnapshot,
    spec: _FieldConflictSpec,
) -> _ConflictCandidateValue | None:
    if spec.verified_attr is None:
        return None
    field = getattr(verified_property, spec.verified_attr)
    if not isinstance(field, VerifiedField):
        return None
    if field.final_value is None:
        return None
    return _ConflictCandidateValue(
        value=field.final_value,
        normalized_value=_normalize_value(field.final_value),
        source_id="verified_property",
        source_type="verified_property",
        confidence=_verified_field_confidence(field),
        label=spec.field_or_topic,
        field_path=f"verified_property.{spec.verified_attr}.final_value",
        authoritative=field.status in {VerificationStatus.VERIFIED, VerificationStatus.CORRECTED},
        verified=field.status in {VerificationStatus.VERIFIED, VerificationStatus.CORRECTED},
    )


def _listing_candidate(
    listing_extraction: PropertyExtractionResult | None,
    spec: _FieldConflictSpec,
) -> _ConflictCandidateValue | None:
    if listing_extraction is None or spec.listing_attr is None:
        return None
    value = getattr(listing_extraction.property, spec.listing_attr)
    if value is None:
        return None
    confidence = Decimal("0.60")
    provenance = listing_extraction.field_provenance.get(spec.listing_attr)
    if provenance is not None:
        confidence = Decimal(str(provenance.confidence))
    return _ConflictCandidateValue(
        value=value,
        normalized_value=_normalize_value(value),
        source_id="listing_extraction",
        source_type="listing_extraction",
        confidence=bounded_decimal(confidence),
        label=spec.field_or_topic,
        field_path=f"listing.property.{spec.listing_attr}",
        retrieved_at=listing_extraction.metadata.retrieved_at,
    )


def _public_records_candidate(
    research_package: ResearchPackage,
    spec: _FieldConflictSpec,
) -> _ConflictCandidateValue | None:
    if research_package.public_records is None or spec.public_record_path is None:
        return None
    field_name, nested_attr = spec.public_record_path
    research_field = getattr(research_package.public_records.data, field_name)
    nested_value = (
        getattr(research_field.value, nested_attr) if research_field.value is not None else None
    )
    if nested_value is None:
        return None
    return _ConflictCandidateValue(
        value=nested_value,
        normalized_value=_normalize_value(nested_value),
        source_id="public_records",
        source_type="public_records",
        confidence=research_field.confidence.value,
        label=spec.field_or_topic,
        field_path=f"public_records.data.{field_name}.value.{nested_attr}",
        authoritative=(
            research_package.public_records.metadata.source_type == SourceType.GOVERNMENT
            if hasattr(research_package.public_records.metadata, "source_type")
            else True
        ),
        retrieved_at=research_package.public_records.retrieved_at,
    )


def _normalize_conflict(
    *,
    field_or_topic: str,
    candidates: list[_ConflictCandidateValue],
    materiality: ConflictMateriality,
    semantic: bool,
    description: str | None = None,
) -> ResearchConflict | None:
    distinct_values: dict[str, _ConflictCandidateValue] = {}
    for candidate in candidates:
        distinct_values.setdefault(
            candidate.normalized_value,
            candidate,
        )
    if len(distinct_values) < 2:
        return None

    preferred = _preferred_candidate(candidates)
    status = ConflictResolutionStatus.UNRESOLVED
    resolution_reason: str | None = description
    requires_user_review = False
    source_precedence_applied = False
    requires_synthesis = False

    if semantic:
        status = ConflictResolutionStatus.UNRESOLVED
        resolution_reason = description or "Semantic conflict requires synthesis or reviewer input."
        requires_user_review = True
        requires_synthesis = True
    elif preferred is not None:
        status = ConflictResolutionStatus.RESOLVED_DETERMINISTICALLY
        resolution_reason = (
            "Verified property values outrank listing and research values."
            if preferred.verified
            else "Authoritative public-record values outrank listing-origin values."
            if preferred.authoritative
            else "Deterministic source precedence selected one value."
        )
        source_precedence_applied = True
    else:
        status = ConflictResolutionStatus.USER_REVIEW_REQUIRED
        resolution_reason = "Top-precedence sources still disagree and require user review."
        requires_user_review = True

    conflict_id = _stable_id(
        "conflict",
        field_or_topic,
        "|".join(sorted(distinct_values.keys())),
        status,
    )
    values = [
        ConflictValue(
            value=candidate.value,
            source_id=candidate.source_id,
            source_type=candidate.source_type,
            confidence=candidate.confidence,
            label=candidate.label,
            field_path=candidate.field_path,
            agent_name=candidate.agent_name,
            authoritative=candidate.authoritative,
            verified=candidate.verified,
            retrieved_at=candidate.retrieved_at,
        )
        for candidate in candidates
    ]
    return ResearchConflict(
        conflict_id=conflict_id,
        field_or_topic=field_or_topic,
        values=values,
        materiality=materiality,
        resolution_status=status,
        preferred_value=preferred.value if preferred is not None and not semantic else None,
        preferred_source_id=preferred.source_id if preferred is not None and not semantic else None,
        resolution_reason=resolution_reason,
        requires_user_review=requires_user_review,
        source_precedence_applied=source_precedence_applied,
        requires_synthesis=requires_synthesis,
    )


def _preferred_candidate(
    candidates: list[_ConflictCandidateValue],
) -> _ConflictCandidateValue | None:
    ranked_candidates = sorted(candidates, key=_candidate_rank)
    if not ranked_candidates:
        return None
    top = ranked_candidates[0]
    tied = [
        candidate
        for candidate in ranked_candidates
        if _candidate_rank(candidate) == _candidate_rank(top)
    ]
    top_values = {candidate.normalized_value for candidate in tied}
    if len(top_values) != 1:
        return None
    return top


def _candidate_rank(candidate: _ConflictCandidateValue) -> tuple[int, Decimal]:
    if candidate.verified:
        return (0, -candidate.confidence)
    if candidate.authoritative:
        return (1, -candidate.confidence)
    if candidate.source_type == "listing_extraction":
        return (2, -candidate.confidence)
    return (3, -candidate.confidence)


def _verified_field_confidence(field: VerifiedField[Any]) -> Decimal:
    if field.confidence is not None:
        return bounded_decimal(field.confidence)
    if field.status in {VerificationStatus.VERIFIED, VerificationStatus.CORRECTED}:
        return Decimal("1")
    if field.status == VerificationStatus.CONFLICTING:
        return Decimal("0.40")
    return Decimal("0.60")


def _finding_signature(finding: AgentFinding) -> str:
    title = _normalize_text(finding.title)
    finding_text = _normalize_text(finding.finding)
    category = _normalize_text(finding.category)
    affected_fields = ",".join(sorted(_normalize_text(field) for field in finding.affected_fields))
    return "|".join([category, title, finding_text, affected_fields])


def _normalize_value(value: Any) -> str:
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    if isinstance(value, float):
        return format(Decimal(str(value)).normalize(), "f")
    if isinstance(value, (int, bool)):
        return str(value).lower()
    return _normalize_text(str(value))


def _normalize_text(value: str) -> str:
    collapsed = re.sub(r"\s+", " ", value.strip().lower())
    return re.sub(r"[^a-z0-9.\- ]+", "", collapsed)


def _stable_id(*parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return digest
