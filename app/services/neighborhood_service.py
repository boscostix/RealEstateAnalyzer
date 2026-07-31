"""Deterministic neighborhood research service with cache and provider fallback."""

from __future__ import annotations

import time

from app.exceptions import (
    AppError,
    NeighborhoodUnavailableError,
    ResearchProviderError,
    ResearchValidationError,
)
from app.models.neighborhood import (
    NeighborhoodData,
    NeighborhoodResearchRequest,
    NeighborhoodResearchResponse,
)
from app.models.research import CacheStatus, ResearchDomain, ResearchResult
from app.research.cache import InMemoryResearchCache, ResearchCache
from app.research.config import ResearchConfig
from app.research.neighborhood_base import NeighborhoodProvider
from app.services.research_provider_registry import ResearchProviderRegistry
from app.utils.research_validation import validate_provider_latency, validate_source_url


class NeighborhoodService:
    """Coordinates neighborhood providers, fallback, and cache usage."""

    def __init__(
        self,
        *,
        registry: ResearchProviderRegistry | None = None,
        cache: ResearchCache | None = None,
        config: ResearchConfig | None = None,
    ) -> None:
        self._registry = registry or ResearchProviderRegistry()
        self._cache = cache or InMemoryResearchCache()
        self._config = config or ResearchConfig.from_env()

    async def research(
        self,
        request: NeighborhoodResearchRequest,
    ) -> NeighborhoodResearchResponse:
        cache_key = self._cache_key(request)
        if self._config.cache.enabled and not request.bypass_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                return NeighborhoodResearchResponse(
                    success=True,
                    result=self._with_cache_status(cached, CacheStatus.HIT),
                )

        providers = self._registry.supported_providers(
            ResearchDomain.NEIGHBORHOOD,
            request.property,
        )
        warnings: list[str] = []
        for provider in providers:
            if not isinstance(provider, NeighborhoodProvider):
                continue
            started_at = time.perf_counter()
            try:
                result = await provider.research(request.property)
            except AppError as exc:
                warnings.append(f"{provider.name}:{exc.code}")
                continue
            except Exception as exc:
                warnings.append(f"{provider.name}:unexpected_error")
                wrapped = ResearchProviderError(message=str(exc))
                warnings.append(f"{provider.name}:{wrapped.code}")
                continue

            validated = self._validate_result(result)
            latency_ms = int((time.perf_counter() - started_at) * 1000)
            merged = self._apply_runtime_metadata(validated, latency_ms, warnings)
            if self._config.cache.enabled and not request.bypass_cache:
                await self._cache.set(
                    cache_key,
                    merged,
                    ttl_seconds=self._config.cache.ttl_seconds,
                )
            return NeighborhoodResearchResponse(success=True, result=merged)

        raise NeighborhoodUnavailableError(
            message="No neighborhood providers could complete the request."
        )

    def _cache_key(self, request: NeighborhoodResearchRequest) -> str:
        address = request.property.full_address.final_value or "unknown-address"
        return f"neighborhood:{request.property.provider}:{address.lower()}"

    def _validate_result(
        self,
        result: ResearchResult[NeighborhoodData],
    ) -> ResearchResult[NeighborhoodData]:
        if result.metadata.domain != ResearchDomain.NEIGHBORHOOD:
            raise ResearchValidationError(
                message="Research result domain must be neighborhood.",
                field="domain",
            )
        validate_provider_latency(result.metadata.provider_latency_ms)
        if result.metadata.source_url is not None:
            validate_source_url(result.metadata.source_url)
        return result

    def _apply_runtime_metadata(
        self,
        result: ResearchResult[NeighborhoodData],
        latency_ms: int,
        warnings: list[str],
    ) -> ResearchResult[NeighborhoodData]:
        metadata = result.metadata.model_copy(
            update={
                "provider_latency_ms": max(
                    result.metadata.provider_latency_ms,
                    latency_ms,
                ),
                "cache_status": CacheStatus.BYPASS
                if not self._config.cache.enabled
                else CacheStatus.MISS,
                "warnings": [*result.metadata.warnings, *warnings],
            }
        )
        return result.model_copy(update={"metadata": metadata})

    def _with_cache_status(
        self,
        result: ResearchResult[NeighborhoodData],
        cache_status: CacheStatus,
    ) -> ResearchResult[NeighborhoodData]:
        metadata = result.metadata.model_copy(update={"cache_status": cache_status})
        return result.model_copy(update={"metadata": metadata})
