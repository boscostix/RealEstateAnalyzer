"""Deterministic sales comparable service with cache and provider fallback."""

from __future__ import annotations

import time

from app.exceptions import (
    AppError,
    ResearchProviderError,
    ResearchValidationError,
    SalesCompsUnavailableError,
)
from app.models.comparables import (
    SalesCompsData,
    SalesCompsProviderData,
    SalesCompsResearchRequest,
    SalesCompsResearchResponse,
)
from app.models.research import CacheStatus, ResearchDomain, ResearchResult
from app.research.cache import InMemoryResearchCache, ResearchCache
from app.research.comparables_base import SalesCompsProvider
from app.research.config import ResearchConfig
from app.services.research_provider_registry import ResearchProviderRegistry
from app.utils.comparables import filter_and_rank_sales_comps
from app.utils.research_validation import validate_provider_latency, validate_source_url


class SalesCompsService:
    """Coordinates sales comparable providers, ranking, fallback, and cache usage."""

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
        request: SalesCompsResearchRequest,
    ) -> SalesCompsResearchResponse:
        cache_key = self._cache_key(request)
        if self._config.cache.enabled and not request.bypass_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                return SalesCompsResearchResponse(
                    success=True,
                    result=self._with_cache_status(cached, CacheStatus.HIT),
                )

        providers = self._registry.supported_providers(
            ResearchDomain.SALES_COMPS,
            request.property,
        )
        warnings: list[str] = []
        for provider in providers:
            if not isinstance(provider, SalesCompsProvider):
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
            validated = self._validate_provider_result(result)
            ranked, summary, confidence = filter_and_rank_sales_comps(
                request.property,
                validated.data.comparables,
                request.filters,
            )
            latency_ms = int((time.perf_counter() - started_at) * 1000)
            response_result = ResearchResult[SalesCompsData](
                provider=validated.provider,
                retrieved_at=validated.retrieved_at,
                metadata=validated.metadata.model_copy(
                    update={
                        "provider_latency_ms": max(
                            validated.metadata.provider_latency_ms,
                            latency_ms,
                        ),
                        "cache_status": CacheStatus.BYPASS
                        if not self._config.cache.enabled
                        else CacheStatus.MISS,
                        "warnings": [*validated.metadata.warnings, *warnings],
                    }
                ),
                confidence=confidence,
                citations=validated.citations,
                sources=validated.sources,
                data=SalesCompsData(
                    top_comparables=ranked,
                    summary=summary,
                ),
            )
            if self._config.cache.enabled and not request.bypass_cache:
                await self._cache.set(
                    cache_key,
                    response_result,
                    ttl_seconds=self._config.cache.ttl_seconds,
                )
            return SalesCompsResearchResponse(success=True, result=response_result)
        raise SalesCompsUnavailableError(
            message="No sales comparable providers could complete the request."
        )

    def _cache_key(self, request: SalesCompsResearchRequest) -> str:
        address = request.property.full_address.final_value or "unknown-address"
        return (
            f"sales_comps:{request.property.provider}:{address.lower()}:"
            f"{request.filters.model_dump_json()}"
        )

    def _validate_provider_result(
        self,
        result: ResearchResult[SalesCompsProviderData],
    ) -> ResearchResult[SalesCompsProviderData]:
        if result.metadata.domain != ResearchDomain.SALES_COMPS:
            raise ResearchValidationError(
                message="Research result domain must be sales_comps.",
                field="domain",
            )
        validate_provider_latency(result.metadata.provider_latency_ms)
        if result.metadata.source_url is not None:
            validate_source_url(result.metadata.source_url)
        return result

    def _with_cache_status(
        self,
        result: ResearchResult[SalesCompsData],
        cache_status: CacheStatus,
    ) -> ResearchResult[SalesCompsData]:
        metadata = result.metadata.model_copy(update={"cache_status": cache_status})
        return result.model_copy(update={"metadata": metadata})
