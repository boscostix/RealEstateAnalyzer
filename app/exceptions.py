"""Typed application exceptions mapped to structured API errors."""

from __future__ import annotations


class AppError(Exception):
    """Base application error for predictable API responses."""

    code = "application_error"
    message = "An unexpected application error occurred."
    status_code = 400
    retryable = False
    field: str | None = None

    def __init__(
        self,
        *,
        message: str | None = None,
        code: str | None = None,
        retryable: bool | None = None,
        status_code: int | None = None,
        field: str | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.retryable = self.retryable if retryable is None else retryable
        self.status_code = self.status_code if status_code is None else status_code
        self.field = self.field if field is None else field
        super().__init__(self.message)


class InvalidURLError(AppError):
    code = "invalid_url"
    message = "The provided URL is invalid."
    status_code = 422


class UnsupportedProviderError(AppError):
    code = "unsupported_provider"
    message = "This listing website is not currently supported."
    status_code = 400


class FetchFailureError(AppError):
    code = "fetch_failure"
    message = "Failed to retrieve the listing page."
    status_code = 502
    retryable = True


class AccessBlockedError(AppError):
    code = "access_blocked"
    message = "The listing website blocked automated access."
    status_code = 403


class CaptchaDetectedError(AppError):
    code = "captcha_detected"
    message = "The listing website requires CAPTCHA verification."
    status_code = 403


class ListingNotFoundError(AppError):
    code = "listing_not_found"
    message = "The requested listing could not be found."
    status_code = 404


class ParsingFailureError(AppError):
    code = "parsing_failure"
    message = "The listing page could not be parsed."
    status_code = 422


class InsufficientListingDataError(AppError):
    code = "insufficient_listing_data"
    message = "The listing page did not contain enough data to extract."
    status_code = 422


class StaticContentInsufficientError(AppError):
    code = "static_content_insufficient"
    message = "The static page response did not contain enough content to parse."
    status_code = 422


class InternalApplicationError(AppError):
    code = "internal_server_error"
    message = "An internal server error occurred."
    status_code = 500


class MissingAnalysisInputError(AppError):
    code = "missing_required_analysis_input"
    message = "A required analysis input is missing."
    status_code = 422


class InvalidAssumptionError(AppError):
    code = "invalid_financial_assumption"
    message = "A financial assumption is invalid."
    status_code = 422


class ConflictingAssumptionsError(AppError):
    code = "conflicting_assumptions"
    message = "The provided assumptions conflict with each other."
    status_code = 422


class UnsupportedFinancingTypeError(AppError):
    code = "unsupported_financing_type"
    message = "The financing type is not supported."
    status_code = 422


class InvalidPercentageError(AppError):
    code = "invalid_percentage"
    message = "A provided percentage value is invalid."
    status_code = 422


class InvalidLoanTermError(AppError):
    code = "invalid_loan_term"
    message = "The loan term is invalid."
    status_code = 422


class InvalidTargetError(AppError):
    code = "invalid_target"
    message = "A requested analysis target is invalid."
    status_code = 422


class CalculationFailureError(AppError):
    code = "calculation_failure"
    message = "A deterministic calculation failed."
    status_code = 422


class UnsolvableMaximumOfferError(AppError):
    code = "unsolvable_maximum_offer_target"
    message = "A maximum-offer target could not be solved."
    status_code = 422
