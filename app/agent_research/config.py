"""Central runtime configuration for agent-based research execution."""

from __future__ import annotations

import os

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.agent_research.versioning import PROMPT_VERSION, WORKFLOW_NAME


class AgentTracingConfig(BaseModel):
    """Tracing and usage capture settings for OpenAI Agents SDK runs."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    workflow_name: str = WORKFLOW_NAME
    include_sensitive_data: bool = False


class AgentRuntimeConfig(BaseModel):
    """Runtime controls shared across deterministic agent orchestration."""

    model_config = ConfigDict(extra="forbid")

    model: str = "gpt-5-mini"
    prompt_version: str = PROMPT_VERSION
    max_turns: int = 6
    timeout_seconds: float = 30.0
    max_parallel_agents: int = 4
    retry_attempts: int = 1
    tracing: AgentTracingConfig = Field(default_factory=AgentTracingConfig)

    @field_validator("max_turns", "max_parallel_agents", "retry_attempts")
    @classmethod
    def validate_positive_ints(cls, value: int) -> int:
        if value < 1:
            raise ValueError("Runtime integer settings must be at least 1.")
        return value

    @field_validator("timeout_seconds")
    @classmethod
    def validate_timeout_seconds(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("timeout_seconds must be greater than 0.")
        return value

    @classmethod
    def from_env(cls) -> AgentRuntimeConfig:
        """Load runtime configuration from environment variables."""

        return cls(
            model=os.getenv("OPENAI_AGENT_MODEL", "gpt-5-mini"),
            prompt_version=os.getenv("OPENAI_AGENT_PROMPT_VERSION", PROMPT_VERSION),
            max_turns=int(os.getenv("OPENAI_AGENT_MAX_TURNS", "6")),
            timeout_seconds=float(os.getenv("OPENAI_AGENT_TIMEOUT_SECONDS", "30.0")),
            max_parallel_agents=int(os.getenv("OPENAI_AGENT_MAX_PARALLEL_AGENTS", "4")),
            retry_attempts=int(os.getenv("OPENAI_AGENT_RETRY_ATTEMPTS", "1")),
            tracing=AgentTracingConfig(
                enabled=os.getenv("OPENAI_AGENT_TRACING_ENABLED", "true").lower() == "true",
                workflow_name=os.getenv("OPENAI_AGENT_WORKFLOW_NAME", WORKFLOW_NAME),
                include_sensitive_data=(
                    os.getenv("OPENAI_AGENT_TRACE_SENSITIVE_DATA", "false").lower() == "true"
                ),
            ),
        )
