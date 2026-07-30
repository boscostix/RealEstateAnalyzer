"""Tests for URL validation and SSRF protections."""

import pytest

from app.exceptions import InvalidURLError
from app.utils.urls import validate_listing_url


@pytest.mark.parametrize(
    ("url"),
    [
        "https://www.zillow.com/homedetails/example",
        "https://www.redfin.com/TX/Dallas/example/home/123",
    ],
)
def test_validate_listing_url_accepts_supported_http_urls(url: str) -> None:
    assert validate_listing_url(url) == url


@pytest.mark.parametrize(
    ("url"),
    [
        "ftp://www.zillow.com/homedetails/example",
        "file:///etc/passwd",
        "mailto:test@example.com",
    ],
)
def test_validate_listing_url_rejects_non_http_protocols(url: str) -> None:
    with pytest.raises(InvalidURLError):
        validate_listing_url(url)


@pytest.mark.parametrize(
    ("url"),
    [
        "http://localhost/listing",
        "http://127.0.0.1/listing",
        "http://10.0.0.5/listing",
        "http://172.16.10.4/listing",
        "http://192.168.1.20/listing",
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://[::1]/listing",
    ],
)
def test_validate_listing_url_rejects_local_and_private_hosts(url: str) -> None:
    with pytest.raises(InvalidURLError):
        validate_listing_url(url)


def test_validate_listing_url_rejects_relative_url() -> None:
    with pytest.raises(InvalidURLError):
        validate_listing_url("/homedetails/example")
