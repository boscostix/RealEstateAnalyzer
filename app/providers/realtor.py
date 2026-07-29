"""Realtor.com provider adapter."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from app.models.extraction import FetchedPage, PropertyExtractionResult
from app.providers.base import ListingProvider
from app.providers.common import build_result, price_history_events, record_field
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


class RealtorProvider(ListingProvider):
    """Provider adapter for Realtor.com listings."""

    name = "realtor"
    supported_domains = ("realtor.com", "www.realtor.com")

    def can_handle(self, url: str) -> bool:
        hostname = urlparse(url).hostname or ""
        return hostname in self.supported_domains

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
            geo = listing_ld.get("geo")
            if isinstance(geo, dict):
                record_field(
                    fields,
                    "latitude",
                    parse_decimal(geo.get("latitude")),
                    source="json_ld",
                    confidence=0.75,
                )
                record_field(
                    fields,
                    "longitude",
                    parse_decimal(geo.get("longitude")),
                    source="json_ld",
                    confidence=0.75,
                )
            record_field(
                fields,
                "description",
                listing_ld.get("description"),
                source="json_ld",
                confidence=0.7,
            )

        next_data = load_script_json(page.html, "__NEXT_DATA__")
        property_data = _dig(
            next_data,
            "props",
            "pageProps",
            "initialProps",
            "propertyData",
        )
        if isinstance(property_data, dict):
            self._extract_property_data(fields, property_data)

        return build_result(
            provider=self.name,
            source_url=url,
            field_values=fields,
            extraction_method="next_data" if isinstance(property_data, dict) else "json_ld",
        )

    def _extract_property_data(self, fields: dict[str, Any], property_data: dict[str, Any]) -> None:
        address = property_data.get("address")
        if isinstance(address, dict):
            street = address.get("line")
            city = address.get("city")
            state = address.get("stateCode")
            postal_code = address.get("postalCode")
            record_field(fields, "address.street", street, source="next_data", confidence=0.98)
            record_field(fields, "address.city", city, source="next_data", confidence=0.98)
            record_field(fields, "address.state", state, source="next_data", confidence=0.98)
            record_field(
                fields, "address.postal_code", postal_code, source="next_data", confidence=0.98
            )
            record_field(
                fields,
                "address.full_address",
                combine_address(street, city, state, postal_code),
                source="next_data",
                confidence=0.99,
            )

        record_field(
            fields,
            "listing_id",
            property_data.get("propertyId"),
            source="next_data",
            confidence=0.99,
        )
        record_field(
            fields,
            "listing_status",
            normalize_listing_status(property_data.get("status")),
            source="next_data",
            confidence=0.95,
        )
        record_field(
            fields,
            "asking_price",
            parse_decimal(property_data.get("listPrice")),
            source="next_data",
            confidence=0.99,
        )
        record_field(
            fields,
            "bedrooms",
            parse_decimal(property_data.get("beds")),
            source="next_data",
            confidence=0.98,
        )
        record_field(
            fields,
            "bathrooms",
            parse_decimal(property_data.get("baths")),
            source="next_data",
            confidence=0.98,
        )
        record_field(
            fields,
            "square_feet",
            parse_int(property_data.get("sqft")),
            source="next_data",
            confidence=0.98,
        )
        record_field(
            fields,
            "lot_square_feet",
            parse_int(property_data.get("lotSqft")),
            source="next_data",
            confidence=0.9,
        )
        record_field(
            fields,
            "year_built",
            parse_int(property_data.get("yearBuilt")),
            source="next_data",
            confidence=0.9,
        )
        record_field(
            fields,
            "garage_spaces",
            parse_decimal(property_data.get("garageSpaces")),
            source="next_data",
            confidence=0.85,
        )
        record_field(
            fields,
            "stories",
            parse_decimal(property_data.get("stories")),
            source="next_data",
            confidence=0.85,
        )
        record_field(
            fields,
            "property_type",
            normalize_property_type(property_data.get("propertyType")),
            source="next_data",
            confidence=0.95,
        )
        record_field(
            fields,
            "price_per_square_foot",
            parse_decimal(property_data.get("pricePerSqFt")),
            source="next_data",
            confidence=0.9,
        )
        record_field(
            fields,
            "annual_property_tax",
            parse_decimal(property_data.get("annualTax")),
            source="next_data",
            confidence=0.8,
        )
        record_field(
            fields,
            "annual_hoa",
            parse_decimal(property_data.get("annualHoa")),
            source="next_data",
            confidence=0.8,
        )
        record_field(
            fields,
            "listing_agent",
            property_data.get("agentName"),
            source="next_data",
            confidence=0.85,
        )
        record_field(
            fields,
            "listing_brokerage",
            property_data.get("brokerName"),
            source="next_data",
            confidence=0.85,
        )
        record_field(
            fields,
            "description",
            property_data.get("description"),
            source="next_data",
            confidence=0.9,
        )
        record_field(
            fields,
            "features",
            clean_string_list(property_data.get("features")),
            source="next_data",
            confidence=0.8,
        )
        record_field(
            fields,
            "appliances",
            clean_string_list(property_data.get("appliances")),
            source="next_data",
            confidence=0.8,
        )
        record_field(
            fields,
            "school_names",
            clean_string_list(property_data.get("schools")),
            source="next_data",
            confidence=0.8,
        )
        record_field(
            fields,
            "photos",
            clean_string_list(property_data.get("photos")),
            source="next_data",
            confidence=0.9,
        )
        record_field(
            fields,
            "price_history",
            price_history_events(property_data.get("priceHistory"), "next_data"),
            source="next_data",
            confidence=0.8,
        )
        record_field(
            fields,
            "listing_date",
            parse_date(property_data.get("listDate")),
            source="next_data",
            confidence=0.85,
        )
        record_field(
            fields,
            "last_updated_date",
            parse_date(property_data.get("lastUpdated")),
            source="next_data",
            confidence=0.85,
        )


def _dig(payload: dict[str, Any] | None, *path: str) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current
