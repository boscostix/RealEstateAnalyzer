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


class CommitteeTimeoutError(InvestmentCommitteeError):
    code = "committee_timeout"
    message = "The investment committee timed out."
    status_code = 504


class CommitteeModelFailureError(InvestmentCommitteeError):
    code = "committee_model_failure"
    message = "The investment committee model could not complete the run."
    status_code = 502


class InvalidCommitteeStructuredOutputError(InvestmentCommitteeError):
    code = "invalid_committee_structured_output"
    message = "The investment committee returned invalid structured output."
    status_code = 422
    retryable = False


class CommitteeOutputValidationError(InvestmentCommitteeError):
    code = "committee_output_validation_failure"
    message = "The investment committee output failed deterministic validation."
    status_code = 422
    retryable = False
