"""Tests for maximum offer calculations."""

from decimal import Decimal

from app.models.assumptions import RunAnalysisRequest
from app.services.underwriting_service import UnderwritingService
from tests.test_scenarios import build_assumptions, build_property


def test_maximum_offer_returns_binding_price() -> None:
    service = UnderwritingService()
    assumptions = build_assumptions()
    assumptions.targets.monthly_cash_flow = Decimal("100")
    response = service.run(RunAnalysisRequest(property=build_property(), assumptions=assumptions))
    assert response.analysis is not None
    assert response.analysis.maximum_offer.binding_maximum_price is not None
