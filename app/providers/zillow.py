"""Zillow provider adapter."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from app.models.extraction import FetchedPage, PropertyExtractionResult
from app.providers.base import ListingProvider
from app.providers.common import build_result, price_history_events, record_field
from app.services.hasdata_zillow_client import HasDataZillowClient
from app.utils.parsing import (
    clean_string_list,
    combine_address,
    first_json_ld_by_type,
    load_json_ld,
    load_script_json,
    meta_content,
    normalize_listing_status,
    normalize_property_type,
    parse_date,
    parse_decimal,
    parse_int,
    visible_text_by_selector,
)


class ZillowProvider(ListingProvider):
    """Provider adapter for Zillow listings."""

    name = "zillow"
    supported_domains = ("zillow.com", "www.zillow.com")

    def __init__(self, *, hasdata_client: HasDataZillowClient | None = None) -> None:
        self._hasdata_client = hasdata_client or HasDataZillowClient()

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
            "SingleFamilyResidence",
            "House",
            "Residence",
        )
        if listing_ld is not None:
            address = listing_ld.get("address")
            if isinstance(address, dict):
                full_address = combine_address(
                    address.get("streetAddress"),
                    address.get("addressLocality"),
                    address.get("addressRegion"),
                    address.get("postalCode"),
                )
                record_field(
                    fields,
                    "address.street",
                    address.get("streetAddress"),
                    source="json_ld",
                    confidence=0.8,
                )
                record_field(
                    fields,
                    "address.city",
                    address.get("addressLocality"),
                    source="json_ld",
                    confidence=0.8,
                )
                record_field(
                    fields,
                    "address.state",
                    address.get("addressRegion"),
                    source="json_ld",
                    confidence=0.8,
                )
                record_field(
                    fields,
                    "address.postal_code",
                    address.get("postalCode"),
                    source="json_ld",
                    confidence=0.8,
                )
                record_field(
                    fields,
                    "address.full_address",
                    full_address or None,
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
            "componentProps",
            "gdpClientCache",
            "property",
        )
        if isinstance(property_data, dict):
            self._extract_property_data(fields, property_data)

        record_field(
            fields,
            "address.full_address",
            meta_content(page.html, "og:title"),
            source="html_meta",
            confidence=0.4,
        )
        record_field(
            fields,
            "asking_price",
            parse_decimal(visible_text_by_selector(page.html, "[data-testid='price']")),
            source="visible_html",
            confidence=0.35,
        )
        record_field(
            fields,
            "bedrooms",
            parse_decimal(
                visible_text_by_selector(page.html, "[data-testid='bed-bath-sqft-facts'] .beds")
            ),
            source="visible_html",
            confidence=0.35,
        )
        record_field(
            fields,
            "bathrooms",
            parse_decimal(
                visible_text_by_selector(page.html, "[data-testid='bed-bath-sqft-facts'] .baths")
            ),
            source="visible_html",
            confidence=0.35,
        )
        record_field(
            fields,
            "square_feet",
            parse_int(
                visible_text_by_selector(page.html, "[data-testid='bed-bath-sqft-facts'] .sqft")
            ),
            source="visible_html",
            confidence=0.35,
        )

        method = "next_data" if isinstance(property_data, dict) else "json_ld"
        if not isinstance(property_data, dict) and fields.get("asking_price") is not None:
            method = "visible_html"
        return build_result(
            provider=self.name,
            source_url=url,
            field_values=fields,
            extraction_method=method,
        )

    def _extract_hasdata_property_data(
        self,
        fields: dict[str, Any],
        property_data: dict[str, Any],
    ) -> None:
        address = property_data.get("address")
        if isinstance(address, dict):
            street = address.get("streetAddress") or address.get("street")
            city = address.get("city") or address.get("addressLocality")
            state = address.get("state") or address.get("stateCode") or address.get("addressRegion")
            postal_code = address.get("zipcode") or address.get("postalCode") or address.get("zip")
            full_address = (
                address.get("full")
                or address.get("fullAddress")
                or combine_address(street, city, state, postal_code)
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
        else:
            record_field(
                fields,
                "address.full_address",
                property_data.get("address"),
                source="hasdata_api",
                confidence=0.95,
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
            property_data.get("listingId") or property_data.get("zpid"),
            source="hasdata_api",
            confidence=0.99,
        )
        record_field(
            fields,
            "listing_status",
            normalize_listing_status(
                property_data.get("listingStatus") or property_data.get("homeStatus")
            ),
            source="hasdata_api",
            confidence=0.95,
        )
        record_field(
            fields,
            "asking_price",
            parse_decimal(property_data.get("price") or property_data.get("listPrice")),
            source="hasdata_api",
            confidence=0.99,
        )
        record_field(
            fields,
            "original_listing_price",
            parse_decimal(
                property_data.get("originalListPrice") or property_data.get("originalPrice")
            ),
            source="hasdata_api",
            confidence=0.9,
        )
        record_field(
            fields,
            "bedrooms",
            parse_decimal(property_data.get("bedrooms") or property_data.get("beds")),
            source="hasdata_api",
            confidence=0.98,
        )
        record_field(
            fields,
            "bathrooms",
            parse_decimal(property_data.get("bathrooms") or property_data.get("baths")),
            source="hasdata_api",
            confidence=0.98,
        )
        record_field(
            fields,
            "square_feet",
            parse_int(
                property_data.get("livingArea")
                or property_data.get("squareFeet")
                or property_data.get("sqft")
            ),
            source="hasdata_api",
            confidence=0.98,
        )
        record_field(
            fields,
            "lot_square_feet",
            parse_int(
                property_data.get("lotSize")
                or property_data.get("lotAreaValue")
                or property_data.get("lotSizeSqFt")
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
            parse_decimal(property_data.get("stories")),
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
            parse_decimal(
                property_data.get("pricePerSquareFoot") or property_data.get("pricePerSqFt")
            ),
            source="hasdata_api",
            confidence=0.9,
        )
        record_field(
            fields,
            "annual_property_tax",
            parse_decimal(
                property_data.get("annualTaxAmount")
                or property_data.get("annualTax")
                or property_data.get("propertyTaxRate")
            ),
            source="hasdata_api",
            confidence=0.8,
        )
        record_field(
            fields,
            "annual_hoa",
            parse_decimal(property_data.get("annualHoaFee") or property_data.get("annualHoa")),
            source="hasdata_api",
            confidence=0.8,
        )
        record_field(
            fields,
            "estimated_property_value",
            parse_decimal(property_data.get("zestimate")),
            source="hasdata_api",
            confidence=0.85,
        )
        record_field(
            fields,
            "estimated_monthly_rent",
            parse_decimal(property_data.get("rentZestimate")),
            source="hasdata_api",
            confidence=0.8,
        )
        record_field(
            fields,
            "listing_agent",
            property_data.get("listingAgent")
            or property_data.get("agentName")
            or _dig(property_data, "agent", "name"),
            source="hasdata_api",
            confidence=0.85,
        )
        record_field(
            fields,
            "listing_brokerage",
            property_data.get("brokerage")
            or property_data.get("brokerName")
            or _dig(property_data, "broker", "name"),
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
            "photos",
            _normalize_photos(property_data.get("photos")),
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
            "appliances",
            clean_string_list(property_data.get("appliances")),
            source="hasdata_api",
            confidence=0.8,
        )
        record_field(
            fields,
            "school_names",
            _normalize_school_names(property_data.get("schools")),
            source="hasdata_api",
            confidence=0.8,
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
            record_field(
                fields,
                "address.street",
                address.get("streetAddress"),
                source="next_data",
                confidence=0.98,
            )
            record_field(
                fields,
                "address.city",
                address.get("city"),
                source="next_data",
                confidence=0.98,
            )
            record_field(
                fields,
                "address.state",
                address.get("state"),
                source="next_data",
                confidence=0.98,
            )
            record_field(
                fields,
                "address.postal_code",
                address.get("zipcode"),
                source="next_data",
                confidence=0.98,
            )
            record_field(
                fields,
                "address.full_address",
                address.get("full")
                or combine_address(
                    address.get("streetAddress"),
                    address.get("city"),
                    address.get("state"),
                    address.get("zipcode"),
                ),
                source="next_data",
                confidence=0.99,
            )

        record_field(
            fields,
            "listing_id",
            property_data.get("listingId"),
            source="next_data",
            confidence=0.99,
        )
        record_field(
            fields,
            "listing_status",
            normalize_listing_status(property_data.get("listingStatus")),
            source="next_data",
            confidence=0.95,
        )
        record_field(
            fields,
            "asking_price",
            parse_decimal(property_data.get("price")),
            source="next_data",
            confidence=0.99,
        )
        record_field(
            fields,
            "original_listing_price",
            parse_decimal(property_data.get("originalListPrice")),
            source="next_data",
            confidence=0.9,
        )
        record_field(
            fields,
            "bedrooms",
            parse_decimal(property_data.get("bedrooms")),
            source="next_data",
            confidence=0.98,
        )
        record_field(
            fields,
            "bathrooms",
            parse_decimal(property_data.get("bathrooms")),
            source="next_data",
            confidence=0.98,
        )
        record_field(
            fields,
            "square_feet",
            parse_int(property_data.get("livingArea")),
            source="next_data",
            confidence=0.98,
        )
        record_field(
            fields,
            "lot_square_feet",
            parse_int(property_data.get("lotSize")),
            source="next_data",
            confidence=0.95,
        )
        record_field(
            fields,
            "year_built",
            parse_int(property_data.get("yearBuilt")),
            source="next_data",
            confidence=0.95,
        )
        record_field(
            fields,
            "price_per_square_foot",
            parse_decimal(property_data.get("pricePerSquareFoot")),
            source="next_data",
            confidence=0.95,
        )
        record_field(
            fields,
            "annual_property_tax",
            parse_decimal(property_data.get("annualTaxAmount")),
            source="next_data",
            confidence=0.85,
        )
        record_field(
            fields,
            "annual_hoa",
            parse_decimal(property_data.get("annualHoaFee")),
            source="next_data",
            confidence=0.85,
        )
        record_field(
            fields,
            "garage_spaces",
            parse_decimal(property_data.get("garageSpaces")),
            source="next_data",
            confidence=0.9,
        )
        record_field(
            fields,
            "stories",
            parse_decimal(property_data.get("stories")),
            source="next_data",
            confidence=0.9,
        )
        record_field(
            fields,
            "foundation_type",
            property_data.get("foundationType"),
            source="next_data",
            confidence=0.8,
        )
        record_field(
            fields, "roof_type", property_data.get("roofType"), source="next_data", confidence=0.8
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
            "description",
            property_data.get("description"),
            source="next_data",
            confidence=0.9,
        )
        record_field(
            fields,
            "photos",
            clean_string_list(property_data.get("photos")),
            source="next_data",
            confidence=0.95,
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
            parse_date(property_data.get("listingDate")),
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


def _normalize_photos(value: object) -> list[str]:
    if isinstance(value, list):
        urls: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                urls.append(item.strip())
            elif isinstance(item, dict):
                url = item.get("url") or item.get("src")
                if isinstance(url, str) and url.strip():
                    urls.append(url.strip())
        return urls
    return clean_string_list(value)


def _normalize_school_names(value: object) -> list[str]:
    if isinstance(value, list):
        names: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                names.append(item.strip())
            elif isinstance(item, dict):
                name = item.get("name")
                if isinstance(name, str) and name.strip():
                    names.append(name.strip())
        return names
    return clean_string_list(value)
