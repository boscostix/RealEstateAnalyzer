"""URL validation and SSRF protections for listing ingestion."""

import ipaddress
from collections.abc import Awaitable, Callable
from urllib.parse import urlparse

from app.exceptions import InvalidURLError

DISALLOWED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
}

DISALLOWED_IPS = {
    ipaddress.ip_address("169.254.169.254"),
}

Resolver = Callable[[str], Awaitable[list[str]]]


def validate_listing_url(url: str) -> str:
    """Validate a user-supplied listing URL and reject common SSRF targets."""

    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise InvalidURLError(message="Only HTTP and HTTPS URLs are allowed.")

    if not parsed.netloc or not parsed.hostname:
        raise InvalidURLError(message="A valid absolute URL is required.")

    hostname = parsed.hostname.strip().lower()

    if hostname in DISALLOWED_HOSTNAMES:
        raise InvalidURLError(message="The provided host is not allowed.")

    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        return url

    if _is_disallowed_ip(ip):
        raise InvalidURLError(message="The provided host is not allowed.")

    return url


async def validate_resolved_addresses(hostname: str, resolver: Resolver) -> None:
    """Resolve a hostname and reject disallowed IP targets."""

    try:
        resolved_addresses = await resolver(hostname)
    except OSError as exc:
        raise InvalidURLError(message="The host could not be resolved safely.") from exc

    if not resolved_addresses:
        raise InvalidURLError(message="The host could not be resolved safely.")

    for address in resolved_addresses:
        ip = ipaddress.ip_address(address)
        if _is_disallowed_ip(ip):
            raise InvalidURLError(message="The provided host is not allowed.")


def _is_disallowed_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
        or ip in DISALLOWED_IPS
    )
