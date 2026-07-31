"""Cache interfaces and a small in-memory implementation for research results."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any

from app.models.research import CacheEntry, ResearchResult


class ResearchCache(ABC):
    """Abstract cache used by deterministic research services."""

    @abstractmethod
    async def get(self, key: str) -> ResearchResult[Any] | None:
        """Return a cached result when present and unexpired."""

    @abstractmethod
    async def set(
        self,
        key: str,
        value: ResearchResult[Any],
        *,
        ttl_seconds: int,
    ) -> None:
        """Store a result for the given TTL."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a cache entry if it exists."""


class InMemoryResearchCache(ResearchCache):
    """Simple deterministic in-memory cache for local development and tests."""

    def __init__(self) -> None:
        self._entries: dict[str, CacheEntry[Any]] = {}

    async def get(self, key: str) -> ResearchResult[Any] | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at <= datetime.now(UTC):
            self._entries.pop(key, None)
            return None
        return entry.value

    async def set(
        self,
        key: str,
        value: ResearchResult[Any],
        *,
        ttl_seconds: int,
    ) -> None:
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        self._entries[key] = CacheEntry[Any](
            key=key,
            value=value,
            expires_at=expires_at,
        )

    async def delete(self, key: str) -> None:
        self._entries.pop(key, None)
