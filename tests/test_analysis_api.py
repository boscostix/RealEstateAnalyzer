"""API tests for verification and deterministic analysis routes."""

from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app
from app.models.assumptions import RunAnalysisRequest
from app.models.extraction import ExtractionMetadata, PropertyExtractionResult
from app.models.property import Address, NormalizedProperty
from app.models.verification import PropertyVerificationRequest
from tests.test_scenarios import build_assumptions, build_property

client = TestClient(app, raise_server_exceptions=False)


def test_verify_property_endpoint_returns_summary() -> None:
    extraction = PropertyExtractionResult(
        provider="zillow",
        source_url="https://www.zillow.com/example",
        property=NormalizedProperty(
            source_url="https://www.zillow.com/example",
            provider="zillow",
            address=Address(full_address="123 Main St"),
            asking_price=Decimal("300000"),
        ),
        metadata=ExtractionMetadata(
            extraction_method="hasdata_api",
            fields_found=2,
            fields_missing=[],
            warnings=[],
        ),
    )
    response = client.post(
        "/api/v1/properties/verify",
        json=PropertyVerificationRequest(
            extraction=extraction,
            corrections={"annual_hoa": "0"},
            confirmed_fields=["asking_price"],
        ).model_dump(mode="json"),
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_run_analysis_endpoint_returns_analysis() -> None:
    payload = RunAnalysisRequest(property=build_property(), assumptions=build_assumptions())
    response = client.post(
        "/api/v1/analyses/run",
        json=payload.model_dump(mode="json"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["analysis"]["metrics"]["noi"] is not None
    assert len(body["analysis"]["scenarios"]) == 3
