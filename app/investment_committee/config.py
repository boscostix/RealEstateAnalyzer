"""Runtime configuration for the investment-committee agent."""

from __future__ import annotations

import os

from pydantic import BaseModel, Field, field_validator

from app.utils.openai_api_key import ensure_openai_api_key_env


class CommitteeTracingConfig(BaseModel):
    enabled: bool = True
    workflow_name: str = "investment_committee"
    include_sensitive_data: bool = False


class CommitteeRuntimeConfig(BaseModel):
    model: str = "gpt-5-mini"
    prompt_version: str = "v1"
    max_turns: int = 6
    timeout_seconds: float = 30.0
    retry_attempts: int = 1
    tracing: CommitteeTracingConfig = Field(default_factory=CommitteeTracingConfig)

    @field_validator("max_turns", "retry_attempts")
    @classmethod
    def validate_non_negative_int(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Configuration integers must be non-negative.")
        return value

    @field_validator("timeout_seconds")
    @classmethod
    def validate_timeout(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("timeout_seconds must be greater than zero.")
        return value

    @classmethod
    def from_env(cls) -> CommitteeRuntimeConfig:
        ensure_openai_api_key_env()
        return cls(
            model=os.getenv("OPENAI_COMMITTEE_MODEL", "gpt-5-mini"),
            prompt_version=os.getenv("OPENAI_COMMITTEE_PROMPT_VERSION", "v1"),
            max_turns=int(os.getenv("OPENAI_COMMITTEE_MAX_TURNS", "6")),
            timeout_seconds=float(os.getenv("OPENAI_COMMITTEE_TIMEOUT_SECONDS", "30.0")),
            retry_attempts=int(os.getenv("OPENAI_COMMITTEE_RETRY_ATTEMPTS", "1")),
            tracing=CommitteeTracingConfig(
                enabled=os.getenv("OPENAI_COMMITTEE_TRACING_ENABLED", "true").lower() == "true",
                workflow_name=os.getenv(
                    "OPENAI_COMMITTEE_WORKFLOW_NAME",
                    "investment_committee",
                ),
                include_sensitive_data=os.getenv(
                    "OPENAI_COMMITTEE_TRACE_SENSITIVE_DATA",
                    "false",
                ).lower()
                == "true",
            ),
        )
