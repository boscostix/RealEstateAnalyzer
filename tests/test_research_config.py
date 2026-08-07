"""Tests for research configuration loading."""

from __future__ import annotations

from pytest import MonkeyPatch

from app.research.config import ResearchConfig


def test_research_config_reads_environment(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("RESEARCH_CACHE_ENABLED", "false")
    monkeypatch.setenv("RESEARCH_CACHE_TTL_SECONDS", "7200")
    monkeypatch.setenv("RESEARCH_PROVIDER_TIMEOUT_SECONDS", "12.5")
    monkeypatch.setenv("RESEARCH_PROVIDER_MAX_RETRIES", "4")
    monkeypatch.setenv("RESEARCH_PROVIDER_PARALLELISM_LIMIT", "8")

    config = ResearchConfig.from_env()

    assert config.cache.enabled is False
    assert config.cache.ttl_seconds == 7200
    assert config.execution.timeout_seconds == 12.5
    assert config.execution.max_retries == 4
    assert config.execution.parallelism_limit == 8
