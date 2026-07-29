"""API tests for the listing extraction endpoint."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_extract_listing_returns_provider_for_supported_url() -> None:
    response = client.post(
        "/api/v1/listings/extract",
        json={"url": "https://www.zillow.com/homedetails/example"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["provider"] == "zillow"
    assert payload["property"]["provider"] == "zillow"
    assert payload["metadata"]["warnings"] == ["Extraction is not implemented until later phases."]


def test_extract_listing_returns_structured_error_for_unsupported_provider() -> None:
    response = client.post(
        "/api/v1/listings/extract",
        json={"url": "https://www.example.com/listing/123"},
    )

    assert response.status_code == 400
    assert response.json() == {
        "success": False,
        "error": {
            "code": "unsupported_provider",
            "message": "This listing website is not currently supported.",
            "retryable": False,
        },
    }


def test_extract_listing_rejects_ssrf_target() -> None:
    response = client.post(
        "/api/v1/listings/extract",
        json={"url": "http://127.0.0.1/listing"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "success": False,
        "error": {
            "code": "invalid_url",
            "message": "The provided host is not allowed.",
            "retryable": False,
        },
    }
