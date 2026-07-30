"""Redfin provider adapter."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from app.models.extraction import FetchedPage, PropertyExtractionResult
from app.providers.base import ListingProvider
from app.providers.common import (
    build_result,
    price_history_events,
    record_field,
    sale_history_events,
)
from app.services.hasdata_redfin_client import HasDataRedfinClient
from app.utils.parsing import (
    clean_string_list,
    combine_address,
    first_json_ld_by_type,
    load_json_ld,
    load_script_json,
    normalize_listing_status,
    normalize_property_type,
    parse_date,
    parse_decimal,
    parse_int,
)


class RedfinProvider(ListingProvider):
    """Provider adapter for Redfin listings."""

    name = "redfin"
    supported_domains = ("redfin.com", "www.redfin.com")

    def __init__(self, *, hasdata_client: HasDataRedfinClient | None = None) -> None:
        self._hasdata_client = hasdata_client or HasDataRedfinClient()

    def can_handle(self, url: str) -> bool:
        hostname = urlparse(url).hostname or ""
        return hostname in self.supported_domains

    async def extract_from_url(self, url: str) -> PropertyExtractionResult | None:
        if not self._hasdata_client.is_configured:
            return None

        payload = await self._hasdata_client.fetch_property(url)
        fields: dict[str, Any] = {}
        property_data = _dig(payload, "property")
        if not isinstance(property_data, dict):
            property_data = payload

        self._extract_hasdata_property_data(fields, property_data)
        return build_result(
            provider=self.name,
            source_url=url,
            field_values=fields,
            extraction_method="hasdata_api",
        )

    async def extract(self, url: str, page: FetchedPage) -> PropertyExtractionResult:
        fields: dict[str, Any] = {}

        json_ld_documents = load_json_ld(page.html)
        listing_ld = first_json_ld_by_type(
            json_ld_documents,
            "House",
            "SingleFamilyResidence",
            "Residence",
        )
        if listing_ld is not None:
            address = listing_ld.get("address")
            if isinstance(address, dict):
                street = address.get("streetAddress")
                city = address.get("addressLocality")
                state = address.get("addressRegion")
                postal_code = address.get("postalCode")
                record_field(fields, "address.street", street, source="json_ld", confidence=0.8)
                record_field(fields, "address.city", city, source="json_ld", confidence=0.8)
                record_field(fields, "address.state", state, source="json_ld", confidence=0.8)
                record_field(
                    fields, "address.postal_code", postal_code, source="json_ld", confidence=0.8
                )
                record_field(
                    fields,
                    "address.full_address",
                    combine_address(street, city, state, postal_code),
                    source="json_ld",
                    confidence=0.85,
                )
            record_field(
                fields,
                "description",
                listing_ld.get("description"),
                source="json_ld",
                confidence=0.7,
            )

        redux_state = load_script_json(page.html, "__REDUX_STATE__")
        property_data = _dig(redux_state, "listingDetails")
        if isinstance(property_data, dict):
            self._extract_property_data(fields, property_data)

        return build_result(
            provider=self.name,
            source_url=url,
            field_values=fields,
            extraction_method="embedded_json" if isinstance(property_data, dict) else "json_ld",
        )

    def _extract_hasdata_property_data(
        self,
        fields: dict[str, Any],
        property_data: dict[str, Any],
    ) -> None:
        address = property_data.get("address")
        if isinstance(address, dict):
            street = address.get("street") or address.get("streetAddress")
            city = address.get("city")
            state = address.get("state") or address.get("stateCode")
            postal_code = address.get("zip") or address.get("zipcode") or address.get("postalCode")
            full_address = address.get("fullAddress") or combine_address(
                street,
                city,
                state,
                postal_code,
            )
            record_field(fields, "address.street", street, source="hasdata_api", confidence=0.99)
            record_field(fields, "address.city", city, source="hasdata_api", confidence=0.99)
            record_field(fields, "address.state", state, source="hasdata_api", confidence=0.99)
            record_field(
                fields,
                "address.postal_code",
                postal_code,
                source="hasdata_api",
                confidence=0.99,
            )
            record_field(
                fields,
                "address.full_address",
                full_address,
                source="hasdata_api",
                confidence=0.99,
            )

        geo = property_data.get("geo") or property_data.get("coordinates")
        if isinstance(geo, dict):
            record_field(
                fields,
                "latitude",
                parse_decimal(geo.get("latitude") or geo.get("lat")),
                source="hasdata_api",
                confidence=0.95,
            )
            record_field(
                fields,
                "longitude",
                parse_decimal(geo.get("longitude") or geo.get("lng") or geo.get("lon")),
                source="hasdata_api",
                confidence=0.95,
            )

        record_field(
            fields,
            "listing_id",
            _stringify(property_data.get("listingId") or property_data.get("id")),
            source="hasdata_api",
            confidence=0.99,
        )
        record_field(
            fields,
            "listing_status",
            normalize_listing_status(property_data.get("status")),
            source="hasdata_api",
            confidence=0.95,
        )
        record_field(
            fields,
            "asking_price",
            parse_decimal(property_data.get("price")),
            source="hasdata_api",
            confidence=0.99,
        )
        record_field(
            fields,
            "original_listing_price",
            parse_decimal(property_data.get("originalPrice")),
            source="hasdata_api",
            confidence=0.9,
        )
        record_field(
            fields,
            "bedrooms",
            parse_decimal(property_data.get("beds") or property_data.get("bedrooms")),
            source="hasdata_api",
            confidence=0.98,
        )
        record_field(
            fields,
            "bathrooms",
            parse_decimal(property_data.get("baths") or property_data.get("bathrooms")),
            source="hasdata_api",
            confidence=0.98,
        )
        record_field(
            fields,
            "square_feet",
            parse_int(property_data.get("sqft") or property_data.get("squareFeet")),
            source="hasdata_api",
            confidence=0.98,
        )
        record_field(
            fields,
            "lot_square_feet",
            parse_int(
                property_data.get("lotSizeSqFt")
                or property_data.get("lotSize")
                or _dig(property_data, "area", "lotSize")
            ),
            source="hasdata_api",
            confidence=0.9,
        )
        record_field(
            fields,
            "year_built",
            parse_int(property_data.get("yearBuilt")),
            source="hasdata_api",
            confidence=0.9,
        )
        record_field(
            fields,
            "stories",
            parse_decimal(property_data.get("stories") or property_data.get("storiesDecimal")),
            source="hasdata_api",
            confidence=0.85,
        )
        record_field(
            fields,
            "garage_spaces",
            parse_decimal(property_data.get("garageSpaces")),
            source="hasdata_api",
            confidence=0.85,
        )
        record_field(
            fields,
            "property_type",
            normalize_property_type(
                property_data.get("propertyType") or property_data.get("homeType")
            ),
            source="hasdata_api",
            confidence=0.95,
        )
        record_field(
            fields,
            "price_per_square_foot",
            parse_decimal(property_data.get("pricePerSqFt")),
            source="hasdata_api",
            confidence=0.9,
        )
        record_field(
            fields,
            "annual_property_tax",
            parse_decimal(property_data.get("annualTax") or property_data.get("tax")),
            source="hasdata_api",
            confidence=0.8,
        )
        record_field(
            fields,
            "annual_hoa",
            parse_decimal(property_data.get("annualHoa")),
            source="hasdata_api",
            confidence=0.8,
        )
        record_field(
            fields,
            "listing_agent",
            property_data.get("listingAgent")
            or property_data.get("agentName")
            or _dig(property_data, "agentInfo", "agentName"),
            source="hasdata_api",
            confidence=0.85,
        )
        record_field(
            fields,
            "listing_brokerage",
            property_data.get("brokerage")
            or property_data.get("brokerName")
            or _dig(property_data, "agentInfo", "brokerName"),
            source="hasdata_api",
            confidence=0.85,
        )
        record_field(
            fields,
            "description",
            property_data.get("description"),
            source="hasdata_api",
            confidence=0.9,
        )
        record_field(
            fields,
            "features",
            clean_string_list(property_data.get("features")),
            source="hasdata_api",
            confidence=0.8,
        )
        record_field(
            fields,
            "photos",
            clean_string_list(property_data.get("photos")),
            source="hasdata_api",
            confidence=0.9,
        )
        record_field(
            fields,
            "price_history",
            price_history_events(property_data.get("priceHistory"), "hasdata_api"),
            source="hasdata_api",
            confidence=0.8,
        )
        record_field(
            fields,
            "sale_history",
            sale_history_events(property_data.get("saleHistory"), "hasdata_api"),
            source="hasdata_api",
            confidence=0.8,
        )
        record_field(
            fields,
            "listing_date",
            parse_date(property_data.get("listingDate") or property_data.get("listDate")),
            source="hasdata_api",
            confidence=0.85,
        )
        record_field(
            fields,
            "last_updated_date",
            parse_date(property_data.get("lastUpdated")),
            source="hasdata_api",
            confidence=0.85,
        )

    def _extract_property_data(self, fields: dict[str, Any], property_data: dict[str, Any]) -> None:
        address = property_data.get("address")
        if isinstance(address, dict):
            street = address.get("street")
            city = address.get("city")
            state = address.get("state")
            postal_code = address.get("zip")
            record_field(fields, "address.street", street, source="embedded_json", confidence=0.98)
            record_field(fields, "address.city", city, source="embedded_json", confidence=0.98)
            record_field(fields, "address.state", state, source="embedded_json", confidence=0.98)
            record_field(
                fields, "address.postal_code", postal_code, source="embedded_json", confidence=0.98
            )
            record_field(
                fields,
                "address.full_address",
                combine_address(street, city, state, postal_code),
                source="embedded_json",
                confidence=0.99,
            )
        record_field(
            fields,
            "listing_id",
            property_data.get("listingId"),
            source="embedded_json",
            confidence=0.99,
        )
        record_field(
            fields,
            "listing_status",
            normalize_listing_status(property_data.get("status")),
            source="embedded_json",
            confidence=0.95,
        )
        record_field(
            fields,
            "asking_price",
            parse_decimal(property_data.get("price")),
            source="embedded_json",
            confidence=0.99,
        )
        record_field(
            fields,
            "original_listing_price",
            parse_decimal(property_data.get("originalPrice")),
            source="embedded_json",
            confidence=0.9,
        )
        record_field(
            fields,
            "bedrooms",
            parse_decimal(property_data.get("beds")),
            source="embedded_json",
            confidence=0.98,
        )
        record_field(
            fields,
            "bathrooms",
            parse_decimal(property_data.get("baths")),
            source="embedded_json",
            confidence=0.98,
        )
        record_field(
            fields,
            "square_feet",
            parse_int(property_data.get("sqft")),
            source="embedded_json",
            confidence=0.98,
        )
        record_field(
            fields,
            "lot_square_feet",
            parse_int(property_data.get("lotSizeSqFt")),
            source="embedded_json",
            confidence=0.9,
        )
        record_field(
            fields,
            "year_built",
            parse_int(property_data.get("yearBuilt")),
            source="embedded_json",
            confidence=0.9,
        )
        record_field(
            fields,
            "garage_spaces",
            parse_decimal(property_data.get("garageSpaces")),
            source="embedded_json",
            confidence=0.85,
        )
        record_field(
            fields,
            "stories",
            parse_decimal(property_data.get("stories")),
            source="embedded_json",
            confidence=0.85,
        )
        record_field(
            fields,
            "property_type",
            normalize_property_type(property_data.get("propertyType")),
            source="embedded_json",
            confidence=0.95,
        )
        record_field(
            fields,
            "price_per_square_foot",
            parse_decimal(property_data.get("pricePerSqFt")),
            source="embedded_json",
            confidence=0.9,
        )
        record_field(
            fields,
            "annual_property_tax",
            parse_decimal(property_data.get("annualTax")),
            source="embedded_json",
            confidence=0.8,
        )
        record_field(
            fields,
            "annual_hoa",
            parse_decimal(property_data.get("annualHoa")),
            source="embedded_json",
            confidence=0.8,
        )
        record_field(
            fields,
            "listing_agent",
            property_data.get("listingAgent"),
            source="embedded_json",
            confidence=0.85,
        )
        record_field(
            fields,
            "listing_brokerage",
            property_data.get("brokerage"),
            source="embedded_json",
            confidence=0.85,
        )
        record_field(
            fields,
            "description",
            property_data.get("description"),
            source="embedded_json",
            confidence=0.9,
        )
        record_field(
            fields,
            "features",
            clean_string_list(property_data.get("features")),
            source="embedded_json",
            confidence=0.8,
        )
        record_field(
            fields,
            "photos",
            clean_string_list(property_data.get("photos")),
            source="embedded_json",
            confidence=0.9,
        )
        record_field(
            fields,
            "price_history",
            price_history_events(property_data.get("priceHistory"), "embedded_json"),
            source="embedded_json",
            confidence=0.8,
        )
        record_field(
            fields,
            "sale_history",
            sale_history_events(property_data.get("saleHistory"), "embedded_json"),
            source="embedded_json",
            confidence=0.8,
        )
        record_field(
            fields,
            "listing_date",
            parse_date(property_data.get("listDate")),
            source="embedded_json",
            confidence=0.85,
        )
        record_field(
            fields,
            "last_updated_date",
            parse_date(property_data.get("lastUpdated")),
            source="embedded_json",
            confidence=0.85,
        )


def _dig(payload: dict[str, Any] | None, *path: str) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _stringify(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
