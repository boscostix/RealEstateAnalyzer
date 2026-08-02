"""API tests for the public-records endpoint."""

from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient

from app.api.research_routes import get_public_records_service
from app.main import app
from app.models.public_records import PublicRecordsResearchRequest
from app.models.verification import VerificationStatus, VerifiedField, VerifiedPropertySnapshot
from app.research.cache import InMemoryResearchCache
from app.services.public_records_service import PublicRecordsService
from app.services.research_provider_registry import ResearchProviderRegistry
from tests.test_public_records_service import SuccessfulPublicRecordsProvider

client = TestClient(app, raise_server_exceptions=False)


def build_property() -> VerifiedPropertySnapshot:
    return VerifiedPropertySnapshot(
        source_url="https://example.com/property",
        provider="zillow",
        full_address=VerifiedField[str](
            extracted_value="123 Main St, Dallas, TX 75001",
            final_value="123 Main St, Dallas, TX 75001",
            status=VerificationStatus.VERIFIED,
        ),
        asking_price=VerifiedField[Decimal](
            extracted_value=Decimal("300000"),
            final_value=Decimal("300000"),
            status=VerificationStatus.VERIFIED,
        ),
    )


def override_service() -> PublicRecordsService:
    return PublicRecordsService(
        registry=ResearchProviderRegistry([SuccessfulPublicRecordsProvider()]),
        cache=InMemoryResearchCache(),
    )


def test_public_records_endpoint_returns_structured_result() -> None:
    app.dependency_overrides[get_public_records_service] = override_service
    try:
        response = client.post(
            "/api/v1/research/public-records",
            json=PublicRecordsResearchRequest(property=build_property()).model_dump(mode="json"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["result"]["provider"] == "successful_provider"
    assert body["result"]["data"]["parcel"]["value"]["parcel_number"] == "123-456"
