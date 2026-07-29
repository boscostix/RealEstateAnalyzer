"""Reusable parsing helpers for provider adapters."""

from __future__ import annotations

import json
from datetime import date as dt_date
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from bs4 import BeautifulSoup

PROPERTY_TYPE_MAP = {
    "single family": "single_family",
    "single_family": "single_family",
    "singlefamilyresidence": "single_family",
    "single family residence": "single_family",
    "house": "single_family",
    "condo": "condo",
    "condominium": "condo",
    "townhouse": "townhouse",
    "multi family": "multi_family",
    "multifamily": "multi_family",
}

LISTING_STATUS_MAP = {
    "for sale": "for_sale",
    "forsale": "for_sale",
    "for_sale": "for_sale",
    "active": "for_sale",
    "pending": "pending",
    "sold": "sold",
    "off market": "off_market",
}


def parse_decimal(value: object) -> Decimal | None:
    """Parse a money or decimal-like value into a Decimal."""

    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, str):
        cleaned = (
            value.strip()
            .replace("$", "")
            .replace(",", "")
            .replace("sqft", "")
            .replace("sq. ft.", "")
        )
        if not cleaned:
            return None
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None
    return None


def parse_int(value: object) -> int | None:
    """Parse an integer-like value."""

    parsed = parse_decimal(value)
    return None if parsed is None else int(parsed)


def parse_date(value: object) -> dt_date | None:
    """Parse common date strings used in fixture data."""

    if value is None or value == "":
        return None
    if isinstance(value, dt_date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        for parser in (dt_date.fromisoformat, _parse_datetime_to_date):
            try:
                return parser(value)
            except ValueError:
                continue
    return None


def normalize_property_type(value: object) -> str | None:
    """Normalize provider-specific property types."""

    if value is None:
        return None
    normalized = str(value).strip().lower().replace("-", " ")
    return PROPERTY_TYPE_MAP.get(normalized, normalized.replace(" ", "_"))


def normalize_listing_status(value: object) -> str | None:
    """Normalize provider-specific listing statuses."""

    if value is None:
        return None
    normalized = str(value).strip().lower().replace("-", " ").replace("/", " ")
    key = normalized.replace(" ", "")
    return LISTING_STATUS_MAP.get(key) or LISTING_STATUS_MAP.get(normalized)


def load_json_ld(html: str) -> list[dict[str, Any]]:
    """Load JSON-LD objects from HTML."""

    soup = BeautifulSoup(html, "html.parser")
    documents: list[dict[str, Any]] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        if not script.string:
            continue
        try:
            payload = json.loads(script.string)
        except json.JSONDecodeError:
            continue
        documents.extend(_flatten_json_ld(payload))
    return documents


def load_script_json(html: str, script_id: str) -> dict[str, Any] | None:
    """Load a JSON object from a script tag with a known id."""

    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", id=script_id)
    if script is None or not script.string:
        return None
    try:
        payload = json.loads(script.string)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def meta_content(html: str, name: str, attribute: str = "property") -> str | None:
    """Read a meta tag by property or name."""

    soup = BeautifulSoup(html, "html.parser")
    tag = soup.find("meta", attrs={attribute: name})
    content = None if tag is None else tag.get("content")
    return content if isinstance(content, str) else None


def visible_text_by_selector(html: str, selector: str) -> str | None:
    """Extract visible text from a CSS selector."""

    soup = BeautifulSoup(html, "html.parser")
    node = soup.select_one(selector)
    if node is None:
        return None
    text = node.get_text(" ", strip=True)
    return text or None


def clean_string_list(value: object) -> list[str]:
    """Normalize list-like values into a clean string list."""

    if isinstance(value, list):
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        return cleaned
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def combine_address(
    street: object,
    city: object,
    state: object,
    postal_code: object,
) -> str | None:
    """Build a normalized full address string from separate parts."""

    street_str = _clean_part(street)
    city_str = _clean_part(city)
    state_str = _clean_part(state)
    postal_str = _clean_part(postal_code)

    first_parts = [part for part in (street_str, city_str) if part]
    tail = " ".join(part for part in (state_str, postal_str) if part).strip()
    if tail:
        first_parts.append(tail)
    return ", ".join(first_parts) or None


def first_json_ld_by_type(documents: list[dict[str, Any]], *types: str) -> dict[str, Any] | None:
    """Return the first JSON-LD document matching one of the requested types."""

    wanted = {item.lower() for item in types}
    for document in documents:
        value = document.get("@type")
        if isinstance(value, list):
            normalized = {str(item).lower() for item in value}
            if normalized & wanted:
                return document
        elif isinstance(value, str) and value.lower() in wanted:
            return document
    return None


def _flatten_json_ld(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        results: list[dict[str, Any]] = []
        for item in payload:
            results.extend(_flatten_json_ld(item))
        return results
    if isinstance(payload, dict):
        if "@graph" in payload and isinstance(payload["@graph"], list):
            return _flatten_json_ld(payload["@graph"])
        return [payload]
    return []


def _parse_datetime_to_date(value: str) -> dt_date:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


def _clean_part(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
