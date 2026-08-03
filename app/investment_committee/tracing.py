"""Minimal tracing helpers for investment-committee execution."""

from __future__ import annotations

from agents import RunConfig, set_tracing_disabled

from app.investment_committee.config import CommitteeRuntimeConfig
from app.investment_committee.versioning import COMMITTEE_INPUT_FORMAT_VERSION
from app.investment_committee.versioning_runtime import (
    COMMITTEE_AGENT_NAME,
    build_committee_agent_version,
    build_committee_prompt_version,
)


def configure_committee_tracing(config: CommitteeRuntimeConfig) -> None:
    set_tracing_disabled(not config.tracing.enabled)


def build_committee_run_config(
    config: CommitteeRuntimeConfig,
    *,
    request_id: str,
    analysis_id: str | None,
) -> RunConfig:
    return RunConfig(
        workflow_name=config.tracing.workflow_name,
        trace_include_sensitive_data=config.tracing.include_sensitive_data,
        tracing_disabled=not config.tracing.enabled,
        trace_metadata={
            "request_id": request_id,
            "analysis_id": analysis_id or "",
            "workflow_name": config.tracing.workflow_name,
            "trace_sensitive_data": str(config.tracing.include_sensitive_data).lower(),
            "agent_name": COMMITTEE_AGENT_NAME,
            "agent_version": build_committee_agent_version(),
            "prompt_version": build_committee_prompt_version(),
            "input_format_version": COMMITTEE_INPUT_FORMAT_VERSION,
        },
    )
