"""Tests for underwriting stress tests."""

from app.models.assumptions import RunAnalysisRequest
from app.services.underwriting_service import UnderwritingService
from tests.test_scenarios import build_assumptions, build_property


def test_stress_tests_include_required_count() -> None:
    service = UnderwritingService()
    response = service.run(
        RunAnalysisRequest(property=build_property(), assumptions=build_assumptions())
    )
    assert response.analysis is not None
    assert len(response.analysis.stress_tests) == 12
    assert any(item.identifier == "rent_down_5" for item in response.analysis.stress_tests)
