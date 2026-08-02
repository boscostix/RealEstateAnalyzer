"""Typed exceptions for agent orchestration and structured output validation."""

from __future__ import annotations

from app.exceptions import AppError


class AgentResearchError(AppError):
    code = "agent_research_error"
    message = "An agent research operation failed."
    status_code = 502
    retryable = True


class MissingAgentInputError(AgentResearchError):
    code = "missing_agent_input"
    message = "A required agent input is missing."
    status_code = 422
    retryable = False


class InvalidResearchPackageError(AgentResearchError):
    code = "invalid_research_package"
    message = "The research package is invalid for agent execution."
    status_code = 422
    retryable = False


class AgentTimeoutError(AgentResearchError):
    code = "agent_timeout"
    message = "An agent execution timed out."
    status_code = 504


class WorkflowTimeoutError(AgentResearchError):
    code = "workflow_timeout"
    message = "The agent workflow timed out."
    status_code = 504


class AgentModelFailureError(AgentResearchError):
    code = "agent_model_failure"
    message = "The language model could not complete the agent run."
    status_code = 502


class ToolExecutionFailureError(AgentResearchError):
    code = "agent_tool_execution_failure"
    message = "An agent tool execution failed."
    status_code = 502


class InvalidStructuredAgentOutputError(AgentResearchError):
    code = "invalid_structured_agent_output"
    message = "An agent returned invalid structured output."
    status_code = 422
    retryable = False


class EvidenceValidationFailureError(AgentResearchError):
    code = "evidence_validation_failure"
    message = "Agent evidence validation failed."
    status_code = 422
    retryable = False


class AgentGuardrailFailureError(AgentResearchError):
    code = "agent_guardrail_failure"
    message = "An agent guardrail blocked the response."
    status_code = 422
    retryable = False


class ConflictResolutionFailureError(AgentResearchError):
    code = "conflict_resolution_failure"
    message = "A conflict could not be resolved."
    status_code = 422
    retryable = False


class SynthesisFailureError(AgentResearchError):
    code = "agent_synthesis_failure"
    message = "The agent synthesis step failed."
    status_code = 502


class AgentConfigurationError(AgentResearchError):
    code = "agent_configuration_error"
    message = "Agent runtime configuration is invalid."
    status_code = 500
    retryable = False
