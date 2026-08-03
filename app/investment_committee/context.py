"""Typed runtime context for investment-committee execution."""

from __future__ import annotations

from dataclasses import dataclass

from app.investment_committee.config import CommitteeRuntimeConfig


@dataclass(slots=True)
class CommitteeRunContext:
    request_id: str
    analysis_id: str | None
    committee_config: CommitteeRuntimeConfig
