"""Tests for specialist-agent deterministic output guardrails."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.agent_research.evidence import build_property_key
from app.agent_research.exceptions import AgentGuardrailFailureError
from app.agent_research.guardrails import validate_agent_output
from app.agent_research.models import (
    AgentFinding,
    EvidenceReference,
    EvidenceSourceType,
    FindingSeverity,
)
from app.agent_research.versioning import AgentName
from tests.agent_sdk_utils import (
    make_agent_context,
    make_comparable_agent_output,
    make_listing_agent_output,
    make_neighborhood_agent_output,
)


def make_evidence(context_property_key: str) -> EvidenceReference:
    return EvidenceReference(
        source_id=f"{context_property_key}:verified_property",
        source_type=EvidenceSourceType.VERIFIED_PROPERTY,
        field_path="verified_property.asking_price.final_value",
    )


def test_listing_agent_output_rejects_final_recommendation_language() -> None:
    context = make_agent_context()
    output = make_listing_agent_output()
    output.summary = "You should buy this property."

    with pytest.raises(AgentGuardrailFailureError):
        validate_agent_output(agent_name=AgentName.LISTING, output=output, context=context)


def test_neighborhood_agent_output_rejects_fair_housing_language() -> None:
    context = make_agent_context()
    output = make_neighborhood_agent_output()
    output.summary = "This is a great neighborhood for families."

    with pytest.raises(AgentGuardrailFailureError):
        validate_agent_output(agent_name=AgentName.NEIGHBORHOOD, output=output, context=context)


def test_guardrail_rejects_invalid_source_reference() -> None:
    context = make_agent_context()
    output = make_comparable_agent_output()
    output.sources_used = ["property:other:verified_property"]

    with pytest.raises(AgentGuardrailFailureError):
        validate_agent_output(agent_name=AgentName.COMPARABLE, output=output, context=context)


def test_guardrail_caps_finding_confidence_by_evidence_strength() -> None:
    context = make_agent_context()
    property_key = build_property_key(context.verified_property)
    output = make_listing_agent_output()
    output.findings = [
        AgentFinding(
            finding_id="finding-1",
            category="listing",
            title="One evidence point",
            finding="Only one data point supports this interpretation.",
            significance="Confidence should be capped.",
            severity=FindingSeverity.MEDIUM,
            confidence=Decimal("0.95"),
            evidence=[make_evidence(context_property_key=property_key)],
            affected_fields=["asking_price"],
            is_inference=True,
        )
    ]

    validate_agent_output(agent_name=AgentName.LISTING, output=output, context=context)

    assert output.findings[0].confidence == Decimal("0.85")


def test_guardrail_caps_overall_confidence_by_evidence_strength() -> None:
    context = make_agent_context()
    property_key = build_property_key(context.verified_property)
    output = make_listing_agent_output()
    output.overall_confidence = Decimal("0.99")
    output.findings = [
        AgentFinding(
            finding_id="finding-1",
            category="listing",
            title="Supported by one evidence point",
            finding="One evidence point supports this listing interpretation.",
            significance="Overall confidence should be capped to the evidence limit.",
            severity=FindingSeverity.LOW,
            confidence=Decimal("0.70"),
            evidence=[make_evidence(context_property_key=property_key)],
            affected_fields=["asking_price"],
            is_inference=False,
        )
    ]

    validate_agent_output(agent_name=AgentName.LISTING, output=output, context=context)

    assert output.overall_confidence == Decimal("0.85")
