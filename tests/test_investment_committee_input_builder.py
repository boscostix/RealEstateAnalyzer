"""Tests for deterministic committee input building and sanitization."""

from __future__ import annotations

from decimal import Decimal

from app.agent_research.models import (
    AgentFinding,
    EvidenceReference,
    EvidenceSourceType,
    FindingSeverity,
)
from app.investment_committee.input_builders import build_committee_model_input
from app.investment_committee.sanitization import (
    SECRET_REPLACEMENT,
    serialize_committee_model_input,
)
from app.investment_committee.versioning import COMMITTEE_INPUT_FORMAT_VERSION
from tests.test_investment_committee_policies import make_committee_input


def _evidence_reference() -> EvidenceReference:
    return EvidenceReference(
        source_id="property:test:verified_property",
        source_type=EvidenceSourceType.VERIFIED_PROPERTY,
        field_path="verified_property.asking_price.final_value",
    )


def test_build_committee_model_input_is_stable_and_versioned() -> None:
    committee_input = make_committee_input()

    built_one = build_committee_model_input(committee_input)
    built_two = build_committee_model_input(committee_input)

    assert built_one.format_version == COMMITTEE_INPUT_FORMAT_VERSION
    assert serialize_committee_model_input(built_one) == serialize_committee_model_input(built_two)


def test_build_committee_model_input_preserves_metric_values_and_conflicts() -> None:
    committee_input = make_committee_input()

    built = build_committee_model_input(committee_input)

    metric_lookup = {metric.metric_name: metric.value for metric in built.underwriting_metrics}
    assert metric_lookup["monthly_pre_tax_cash_flow"] == Decimal("250")
    assert metric_lookup["dscr"] == Decimal("1.20")
    assert built.research.conflicts == []


def test_build_committee_model_input_keeps_missing_information_visible_and_classified() -> None:
    committee_input = make_committee_input()
    committee_input.agent_research = committee_input.agent_research.model_copy(
        update={
            "missing_information": [
                "Expected rent is unsupported",
                "Expected rent is unsupported",
                "Insurance quote is missing",
            ]
        }
    )

    built = build_committee_model_input(committee_input)

    assert [item.item for item in built.research.missing_information] == [
        "Expected rent is unsupported",
        "Insurance quote is missing",
    ]
    assert any(item.blocks_recommendation for item in built.research.missing_information)


def test_build_committee_model_input_dedupes_findings_and_evidence() -> None:
    committee_input = make_committee_input()
    duplicate_finding = AgentFinding(
        finding_id="duplicate-1",
        category="pricing",
        title="Asking price exceeds support",
        finding="The asking price is above the binding threshold.",
        significance="Negotiation is required to reach a supportable basis.",
        severity=FindingSeverity.HIGH,
        confidence=Decimal("0.80"),
        evidence=[_evidence_reference(), _evidence_reference()],
        affected_fields=["asking_price", "asking_price"],
        missing_information=[],
        recommended_next_actions=["Negotiate price", "Negotiate price"],
        is_inference=False,
    )
    committee_input.agent_research = committee_input.agent_research.model_copy(
        update={
            "consolidated_findings": [duplicate_finding, duplicate_finding],
            "evidence_index": [_evidence_reference(), _evidence_reference()],
        }
    )

    built = build_committee_model_input(committee_input)

    assert len(built.research.consolidated_findings) == 1
    assert len(built.research.consolidated_findings[0].evidence) == 1
    assert built.research.consolidated_findings[0].affected_fields == ["asking_price"]
    assert built.research.consolidated_findings[0].recommended_next_actions == ["Negotiate price"]
    assert len(built.research.evidence_index) == 1


def test_build_committee_model_input_sanitizes_html_and_secrets() -> None:
    committee_input = make_committee_input()
    risky_output = committee_input.agent_research.listing_analysis
    assert risky_output is not None
    committee_input.decision_context = committee_input.decision_context or None
    committee_input.agent_research = committee_input.agent_research.model_copy(
        update={
            "listing_analysis": risky_output.model_copy(
                update={
                    "summary": "<script>alert(1)</script> api_key=sk-test-123",
                    "warnings": ["token: secret-value"],
                }
            ),
            "warnings": ["<div>debug html</div>", "password=hunter2"],
        }
    )

    built = build_committee_model_input(committee_input)
    payload = serialize_committee_model_input(built)

    assert "<script>" not in payload
    assert "<div>" not in payload
    assert "sk-test-123" not in payload
    assert "hunter2" not in payload
    assert SECRET_REPLACEMENT in payload


def test_build_committee_model_input_excludes_raw_html_container_fields() -> None:
    committee_input = make_committee_input()

    built = build_committee_model_input(committee_input)
    dumped = built.model_dump(mode="json")

    assert "html" not in str(dumped).lower()
