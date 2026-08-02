"""Deterministic comparable-property filtering, scoring, and summary helpers."""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from app.calculations.common import money, ratio
from app.models.comparables import (
    RentalComparableRecord,
    RentalCompsFilters,
    RentalCompsSummary,
    RentalStatus,
    SalesComparableRecord,
    SalesCompsFilters,
    SalesCompsSummary,
    ValueRange,
)
from app.models.research import ConfidenceScore
from app.models.verification import VerifiedPropertySnapshot


def _median(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return money(ordered[midpoint])
    return money((ordered[midpoint - 1] + ordered[midpoint]) / Decimal("2"))


def _average(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    return money(sum(values, start=Decimal("0")) / Decimal(len(values)))


def _value_range(values: list[Decimal]) -> ValueRange:
    if not values:
        return ValueRange()
    ordered = sorted(values)
    return ValueRange(low=money(ordered[0]), high=money(ordered[-1]))


def _subject_bedrooms(property_snapshot: VerifiedPropertySnapshot) -> Decimal | None:
    return property_snapshot.bedrooms.final_value


def _subject_bathrooms(property_snapshot: VerifiedPropertySnapshot) -> Decimal | None:
    return property_snapshot.bathrooms.final_value


def _subject_square_feet(property_snapshot: VerifiedPropertySnapshot) -> int | None:
    return property_snapshot.square_feet.final_value


def _subject_year_built(property_snapshot: VerifiedPropertySnapshot) -> int | None:
    return property_snapshot.year_built.final_value


def _similarity_components(
    property_snapshot: VerifiedPropertySnapshot,
    *,
    distance_miles: Decimal | None,
    square_feet: int | None,
    bedrooms: Decimal | None,
    bathrooms: Decimal | None,
    year_built: int | None,
    max_distance_miles: Decimal,
    max_year_built_delta: int,
) -> list[Decimal]:
    components: list[Decimal] = []
    if distance_miles is not None and max_distance_miles > 0:
        components.append(
            max(
                Decimal("0"),
                Decimal("1") - (distance_miles / max_distance_miles),
            )
        )
    subject_sqft = _subject_square_feet(property_snapshot)
    if subject_sqft is not None and square_feet is not None and subject_sqft > 0:
        components.append(
            max(
                Decimal("0"),
                Decimal("1") - (Decimal(abs(subject_sqft - square_feet)) / Decimal(subject_sqft)),
            )
        )
    subject_beds = _subject_bedrooms(property_snapshot)
    if subject_beds is not None and bedrooms is not None:
        components.append(
            max(
                Decimal("0"),
                Decimal("1") - (abs(subject_beds - bedrooms) / Decimal("2")),
            )
        )
    subject_baths = _subject_bathrooms(property_snapshot)
    if subject_baths is not None and bathrooms is not None:
        components.append(
            max(
                Decimal("0"),
                Decimal("1") - (abs(subject_baths - bathrooms) / Decimal("2")),
            )
        )
    subject_year = _subject_year_built(property_snapshot)
    if subject_year is not None and year_built is not None and max_year_built_delta > 0:
        components.append(
            max(
                Decimal("0"),
                Decimal("1")
                - (Decimal(abs(subject_year - year_built)) / Decimal(max_year_built_delta)),
            )
        )
    return components


def _average_confidence(values: Iterable[Decimal]) -> ConfidenceScore:
    collected = list(values)
    if not collected:
        return ConfidenceScore(value=Decimal("0"), reason="No comparable candidates matched")
    return ConfidenceScore(
        value=money(sum(collected, start=Decimal("0")) / Decimal(len(collected))),
        reason="Average similarity score across matched comparables",
    )


def filter_and_rank_sales_comps(
    property_snapshot: VerifiedPropertySnapshot,
    candidates: list[SalesComparableRecord],
    filters: SalesCompsFilters,
) -> tuple[list[SalesComparableRecord], SalesCompsSummary, ConfidenceScore]:
    matched: list[SalesComparableRecord] = []
    subject_sqft = _subject_square_feet(property_snapshot)
    for candidate in candidates:
        if (
            candidate.distance_miles is not None
            and candidate.distance_miles > filters.max_distance_miles
        ):
            continue
        if candidate.sold_date is not None:
            age_days = (filters.reference_date - candidate.sold_date).days
            if age_days > filters.sold_within_days:
                continue
        if (
            subject_sqft is not None
            and candidate.square_feet is not None
            and subject_sqft > 0
            and Decimal(abs(subject_sqft - candidate.square_feet)) / Decimal(subject_sqft)
            > filters.max_square_feet_delta_ratio
        ):
            continue
        subject_beds = _subject_bedrooms(property_snapshot)
        if (
            subject_beds is not None
            and candidate.bedrooms is not None
            and abs(subject_beds - candidate.bedrooms) > filters.max_bedroom_delta
        ):
            continue
        subject_baths = _subject_bathrooms(property_snapshot)
        if (
            subject_baths is not None
            and candidate.bathrooms is not None
            and abs(subject_baths - candidate.bathrooms) > filters.max_bathroom_delta
        ):
            continue
        subject_year = _subject_year_built(property_snapshot)
        if (
            subject_year is not None
            and candidate.year_built is not None
            and abs(subject_year - candidate.year_built) > filters.max_year_built_delta
        ):
            continue
        price_per_square_foot = candidate.price_per_square_foot
        if (
            price_per_square_foot is None
            and candidate.sold_price is not None
            and candidate.square_feet is not None
            and candidate.square_feet > 0
        ):
            price_per_square_foot = money(candidate.sold_price / Decimal(candidate.square_feet))
        adjusted_ppsf = price_per_square_foot
        if price_per_square_foot is not None and candidate.sold_price is not None:
            adjustments = Decimal("0")
            if subject_beds is not None and candidate.bedrooms is not None:
                adjustments += (subject_beds - candidate.bedrooms) * Decimal("5000")
            if subject_baths is not None and candidate.bathrooms is not None:
                adjustments += (subject_baths - candidate.bathrooms) * Decimal("7500")
            if subject_sqft is not None and candidate.square_feet is not None and subject_sqft > 0:
                adjustments += (
                    Decimal(subject_sqft - candidate.square_feet)
                    * price_per_square_foot
                    * Decimal("0.25")
                )
                adjusted_price = money(candidate.sold_price + adjustments)
                adjusted_ppsf = money(adjusted_price / Decimal(subject_sqft))
        components = _similarity_components(
            property_snapshot,
            distance_miles=candidate.distance_miles,
            square_feet=candidate.square_feet,
            bedrooms=candidate.bedrooms,
            bathrooms=candidate.bathrooms,
            year_built=candidate.year_built,
            max_distance_miles=filters.max_distance_miles,
            max_year_built_delta=filters.max_year_built_delta,
        )
        similarity = ratio(sum(components, start=Decimal("0")) / Decimal(len(components)))
        matched.append(
            candidate.model_copy(
                update={
                    "price_per_square_foot": price_per_square_foot,
                    "adjusted_price_per_square_foot": adjusted_ppsf,
                    "similarity_score": similarity,
                }
            )
        )
    ranked = sorted(
        matched,
        key=lambda item: item.similarity_score or Decimal("0"),
        reverse=True,
    )[: filters.limit]
    sold_prices = [item.sold_price for item in ranked if item.sold_price is not None]
    ppsf_values = [
        item.price_per_square_foot for item in ranked if item.price_per_square_foot is not None
    ]
    adjusted_ppsf_values = [
        item.adjusted_price_per_square_foot
        for item in ranked
        if item.adjusted_price_per_square_foot is not None
    ]
    summary = SalesCompsSummary(
        comparable_count=len(ranked),
        average_sold_price=_average(sold_prices),
        median_sold_price=_median(sold_prices),
        average_price_per_square_foot=_average(ppsf_values),
        median_adjusted_price_per_square_foot=_median(adjusted_ppsf_values),
        sold_price_range=_value_range(sold_prices),
    )
    confidence = _average_confidence([item.similarity_score or Decimal("0") for item in ranked])
    return ranked, summary, confidence


def filter_and_rank_rental_comps(
    property_snapshot: VerifiedPropertySnapshot,
    candidates: list[RentalComparableRecord],
    filters: RentalCompsFilters,
) -> tuple[list[RentalComparableRecord], RentalCompsSummary, ConfidenceScore]:
    matched: list[RentalComparableRecord] = []
    subject_sqft = _subject_square_feet(property_snapshot)
    for candidate in candidates:
        if candidate.rental_status == RentalStatus.ACTIVE and not filters.include_active:
            continue
        if candidate.rental_status == RentalStatus.LEASED and not filters.include_leased:
            continue
        if (
            candidate.distance_miles is not None
            and candidate.distance_miles > filters.max_distance_miles
        ):
            continue
        if (
            subject_sqft is not None
            and candidate.square_feet is not None
            and subject_sqft > 0
            and Decimal(abs(subject_sqft - candidate.square_feet)) / Decimal(subject_sqft)
            > filters.max_square_feet_delta_ratio
        ):
            continue
        subject_beds = _subject_bedrooms(property_snapshot)
        if (
            subject_beds is not None
            and candidate.bedrooms is not None
            and abs(subject_beds - candidate.bedrooms) > filters.max_bedroom_delta
        ):
            continue
        subject_baths = _subject_bathrooms(property_snapshot)
        if (
            subject_baths is not None
            and candidate.bathrooms is not None
            and abs(subject_baths - candidate.bathrooms) > filters.max_bathroom_delta
        ):
            continue
        subject_year = _subject_year_built(property_snapshot)
        if (
            subject_year is not None
            and candidate.year_built is not None
            and abs(subject_year - candidate.year_built) > filters.max_year_built_delta
        ):
            continue
        rent_per_square_foot = candidate.rent_per_square_foot
        if (
            rent_per_square_foot is None
            and candidate.monthly_rent is not None
            and candidate.square_feet is not None
            and candidate.square_feet > 0
        ):
            rent_per_square_foot = money(candidate.monthly_rent / Decimal(candidate.square_feet))
        components = _similarity_components(
            property_snapshot,
            distance_miles=candidate.distance_miles,
            square_feet=candidate.square_feet,
            bedrooms=candidate.bedrooms,
            bathrooms=candidate.bathrooms,
            year_built=candidate.year_built,
            max_distance_miles=filters.max_distance_miles,
            max_year_built_delta=filters.max_year_built_delta,
        )
        similarity = ratio(sum(components, start=Decimal("0")) / Decimal(len(components)))
        matched.append(
            candidate.model_copy(
                update={
                    "rent_per_square_foot": rent_per_square_foot,
                    "similarity_score": similarity,
                }
            )
        )
    ranked = sorted(
        matched,
        key=lambda item: item.similarity_score or Decimal("0"),
        reverse=True,
    )[: filters.limit]
    monthly_rents = [item.monthly_rent for item in ranked if item.monthly_rent is not None]
    rent_psf_values = [
        item.rent_per_square_foot for item in ranked if item.rent_per_square_foot is not None
    ]
    occupancy_values = [
        item.occupancy_indicator for item in ranked if item.occupancy_indicator is not None
    ]
    summary = RentalCompsSummary(
        comparable_count=len(ranked),
        average_monthly_rent=_average(monthly_rents),
        median_monthly_rent=_median(monthly_rents),
        average_rent_per_square_foot=_average(rent_psf_values),
        estimated_rent_range=_value_range(monthly_rents),
        active_count=sum(1 for item in ranked if item.rental_status == RentalStatus.ACTIVE),
        leased_count=sum(1 for item in ranked if item.rental_status == RentalStatus.LEASED),
        average_occupancy_indicator=_average(occupancy_values),
    )
    confidence = _average_confidence([item.similarity_score or Decimal("0") for item in ranked])
    return ranked, summary, confidence
