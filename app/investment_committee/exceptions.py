"""Typed exceptions for investment-committee validation and policy checks."""

from __future__ import annotations

from app.exceptions import AppError


class InvestmentCommitteeError(AppError):
    code = "investment_committee_error"
    message = "An investment-committee operation failed."
    status_code = 502
    retryable = True


class MissingCommitteeInputError(InvestmentCommitteeError):
    code = "missing_committee_input"
    message = "A required investment-committee input is missing."
    status_code = 422
    retryable = False


class InvalidCommitteeInputError(InvestmentCommitteeError):
    code = "invalid_committee_input"
    message = "The investment-committee input is invalid."
    status_code = 422
    retryable = False


class UnsupportedRecommendationError(InvestmentCommitteeError):
    code = "unsupported_recommendation"
    message = "The requested investment recommendation is not supported."
    status_code = 422
    retryable = False


class RecommendationPolicyViolationError(InvestmentCommitteeError):
    code = "recommendation_policy_violation"
    message = "The recommendation violates deterministic committee policy."
    status_code = 422
    retryable = False


class InvalidOfferRangeError(InvestmentCommitteeError):
    code = "invalid_offer_range"
    message = "The committee offer range is invalid."
    status_code = 422
    retryable = False


class UnsupportedOfferValueError(InvestmentCommitteeError):
    code = "unsupported_offer_value"
    message = "The offer value is not supported by deterministic committee policy."
    status_code = 422
    retryable = False


class ConfidencePolicyViolationError(InvestmentCommitteeError):
    code = "confidence_policy_violation"
    message = "The recommendation confidence exceeds deterministic committee policy."
    status_code = 422
    retryable = False
