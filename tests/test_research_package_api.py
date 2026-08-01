"""API tests for the research package endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.research_routes import get_research_orchestrator
from app.main import app
from app.models.research_package import ResearchPackageRequest
from app.services.research_orchestrator import ResearchOrchestrator
from tests.test_research_orchestrator import (
    StaticService,
    build_neighborhood_response,
    build_property,
    build_public_records_response,
    build_rental_response,
    build_sales_response,
)

client = TestClient(app, raise_server_exceptions=False)


def override_research_orchestrator() -> ResearchOrchestrator:
    return ResearchOrchestrator(
        public_records_service=StaticService(build_public_records_response()),
        sales_comps_service=StaticService(build_sales_response()),
        rental_comps_service=StaticService(build_rental_response()),
        neighborhood_service=StaticService(build_neighborhood_response()),
    )


def test_research_package_endpoint_returns_structured_package() -> None:
    app.dependency_overrides[get_research_orchestrator] = override_research_orchestrator
    try:
        response = client.post(
            "/api/v1/research/package",
            json=ResearchPackageRequest(property=build_property()).model_dump(mode="json"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["package"]["metadata"]["completed_domains"]) == 4
    assert body["package"]["public_records"]["provider"] == "public_records_provider"
