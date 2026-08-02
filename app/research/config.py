"""Configuration helpers for deterministic research services."""

from __future__ import annotations

import os

from pydantic import BaseModel, Field


class CacheConfig(BaseModel):
    """Cache-related runtime configuration."""

    enabled: bool = True
    ttl_seconds: int = 3600


class ProviderExecutionConfig(BaseModel):
    """Timeouts and retry behavior shared by research providers."""

    timeout_seconds: float = 10.0
    max_retries: int = 2
    parallelism_limit: int = 4


class ResearchConfig(BaseModel):
    """Top-level deterministic research runtime configuration."""

    cache: CacheConfig = Field(default_factory=CacheConfig)
    execution: ProviderExecutionConfig = Field(default_factory=ProviderExecutionConfig)

    @classmethod
    def from_env(cls) -> ResearchConfig:
        return cls(
            cache=CacheConfig(
                enabled=os.getenv("RESEARCH_CACHE_ENABLED", "true").lower() == "true",
                ttl_seconds=int(os.getenv("RESEARCH_CACHE_TTL_SECONDS", "3600")),
            ),
            execution=ProviderExecutionConfig(
                timeout_seconds=float(os.getenv("RESEARCH_PROVIDER_TIMEOUT_SECONDS", "10.0")),
                max_retries=int(os.getenv("RESEARCH_PROVIDER_MAX_RETRIES", "2")),
                parallelism_limit=int(os.getenv("RESEARCH_PROVIDER_PARALLELISM_LIMIT", "4")),
            ),
        )
