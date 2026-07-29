"""Typed application exceptions mapped to structured API errors."""

from __future__ import annotations


class AppError(Exception):
    """Base application error for predictable API responses."""

    code = "application_error"
    message = "An unexpected application error occurred."
    status_code = 400
    retryable = False

    def __init__(
        self,
        *,
        message: str | None = None,
        code: str | None = None,
        retryable: bool | None = None,
        status_code: int | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.retryable = self.retryable if retryable is None else retryable
        self.status_code = self.status_code if status_code is None else status_code
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
