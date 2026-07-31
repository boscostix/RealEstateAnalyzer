"""API tests for comparable research endpoints."""

from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient

from app.api.research_routes import (
    get_rental_comps_service,
    get_sales_comps_service,
)
from app.main import app
from app.models.comparables import (
    RentalCompsResearchRequest,
    SalesCompsResearchRequest,
)
from app.models.verification import VerificationStatus, VerifiedField, VerifiedPropertySnapshot
from app.research.cache import InMemoryResearchCache
from app.services.rental_comps_service import RentalCompsService
from app.services.research_provider_registry import ResearchProviderRegistry
from app.services.sales_comps_service import SalesCompsService
from tests.test_comparable_services import SuccessfulRentalProvider, SuccessfulSalesProvider

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
        bedrooms=VerifiedField[Decimal](
            extracted_value=Decimal("3"),
            final_value=Decimal("3"),
            status=VerificationStatus.VERIFIED,
        ),
        bathrooms=VerifiedField[Decimal](
            extracted_value=Decimal("2"),
            final_value=Decimal("2"),
            status=VerificationStatus.VERIFIED,
        ),
        square_feet=VerifiedField[int](
            extracted_value=1500,
            final_value=1500,
            status=VerificationStatus.VERIFIED,
        ),
        year_built=VerifiedField[int](
            extracted_value=1990,
            final_value=1990,
            status=VerificationStatus.VERIFIED,
        ),
    )


def override_sales_service() -> SalesCompsService:
    return SalesCompsService(
        registry=ResearchProviderRegistry([SuccessfulSalesProvider()]),
        cache=InMemoryResearchCache(),
    )


def override_rental_service() -> RentalCompsService:
    return RentalCompsService(
        registry=ResearchProviderRegistry([SuccessfulRentalProvider()]),
        cache=InMemoryResearchCache(),
    )


def test_sales_comps_endpoint_returns_structured_result() -> None:
    app.dependency_overrides[get_sales_comps_service] = override_sales_service
    try:
        response = client.post(
            "/api/v1/research/sales-comps",
            json=SalesCompsResearchRequest(property=build_property()).model_dump(
                mode="json"
            ),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["result"]["data"]["summary"]["comparable_count"] == 2


def test_rental_comps_endpoint_returns_structured_result() -> None:
    app.dependency_overrides[get_rental_comps_service] = override_rental_service
    try:
        response = client.post(
            "/api/v1/research/rental-comps",
            json=RentalCompsResearchRequest(property=build_property()).model_dump(
                mode="json"
            ),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["result"]["data"]["summary"]["average_monthly_rent"] == "2350.00"
