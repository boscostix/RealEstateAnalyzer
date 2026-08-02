"""Non-AI orchestrator for deterministic research services."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any, Literal

from app.exceptions import AppError
from app.models.comparables import (
    RentalCompsResearchRequest,
    RentalCompsResearchResponse,
    SalesCompsResearchRequest,
    SalesCompsResearchResponse,
)
from app.models.neighborhood import (
    NeighborhoodResearchRequest,
    NeighborhoodResearchResponse,
)
from app.models.public_records import (
    PublicRecordsResearchRequest,
    PublicRecordsResearchResponse,
)
from app.models.research import Citation
from app.models.research_package import (
    ResearchPackage,
    ResearchPackageMetadata,
    ResearchPackageRequest,
    ResearchPackageResponse,
    ResearchWarning,
)
from app.research.config import ResearchConfig
from app.services.neighborhood_service import NeighborhoodService
from app.services.public_records_service import PublicRecordsService
from app.services.rental_comps_service import RentalCompsService
from app.services.sales_comps_service import SalesCompsService

DomainName = Literal["public_records", "sales_comps", "rental_comps", "neighborhood"]


class ResearchOrchestrator:
    """Coordinates deterministic research services in parallel."""

    def __init__(
        self,
        *,
        public_records_service: PublicRecordsService | None = None,
        sales_comps_service: SalesCompsService | None = None,
        rental_comps_service: RentalCompsService | None = None,
        neighborhood_service: NeighborhoodService | None = None,
        config: ResearchConfig | None = None,
    ) -> None:
        self._public_records_service = public_records_service or PublicRecordsService()
        self._sales_comps_service = sales_comps_service or SalesCompsService()
        self._rental_comps_service = rental_comps_service or RentalCompsService()
        self._neighborhood_service = neighborhood_service or NeighborhoodService()
        self._config = config or ResearchConfig.from_env()

    async def research(
        self,
        request: ResearchPackageRequest,
    ) -> ResearchPackageResponse:
        started_at = time.perf_counter()
        semaphore = asyncio.Semaphore(self._config.execution.parallelism_limit)
        warnings: list[ResearchWarning] = []

        async def run_domain(
            domain: DomainName,
            action: Callable[[], Awaitable[Any]],
        ) -> tuple[DomainName, Any | None]:
            async with semaphore:
                result, domain_warnings = await self._execute_with_retry(domain, action)
                warnings.extend(domain_warnings)
                return domain, result

        tasks = [
            run_domain(
                "public_records",
                lambda: self._public_records_service.research(
                    PublicRecordsResearchRequest(
                        property=request.property,
                        bypass_cache=request.bypass_cache,
                    )
                ),
            ),
            run_domain(
                "sales_comps",
                lambda: self._sales_comps_service.research(
                    SalesCompsResearchRequest(
                        property=request.property,
                        bypass_cache=request.bypass_cache,
                    )
                ),
            ),
            run_domain(
                "rental_comps",
                lambda: self._rental_comps_service.research(
                    RentalCompsResearchRequest(
                        property=request.property,
                        bypass_cache=request.bypass_cache,
                    )
                ),
            ),
            run_domain(
                "neighborhood",
                lambda: self._neighborhood_service.research(
                    NeighborhoodResearchRequest(
                        property=request.property,
                        bypass_cache=request.bypass_cache,
                    )
                ),
            ),
        ]
        results = await asyncio.gather(*tasks)
        result_map = {domain: result for domain, result in results}
        citations = self._dedupe_citations(result_map.values())
        completed = [
            domain for domain, result in results if self._extract_result(result) is not None
        ]
        failed = [domain for domain, result in results if self._extract_result(result) is None]
        package = ResearchPackage(
            property=request.property,
            public_records=self._extract_result(
                result_map["public_records"],
                PublicRecordsResearchResponse,
            ),
            sales_comps=self._extract_result(
                result_map["sales_comps"],
                SalesCompsResearchResponse,
            ),
            rental_comps=self._extract_result(
                result_map["rental_comps"],
                RentalCompsResearchResponse,
            ),
            neighborhood=self._extract_result(
                result_map["neighborhood"],
                NeighborhoodResearchResponse,
            ),
            metadata=ResearchPackageMetadata(
                total_duration_ms=int((time.perf_counter() - started_at) * 1000),
                completed_domains=list(completed),
                failed_domains=list(failed),
                citations=citations,
            ),
            warnings=self._dedupe_warnings(warnings),
        )
        return ResearchPackageResponse(success=True, package=package)

    async def _execute_with_retry(
        self,
        domain: DomainName,
        action: Callable[[], Awaitable[Any]],
    ) -> tuple[Any | None, list[ResearchWarning]]:
        warnings: list[ResearchWarning] = []
        attempts = self._config.execution.max_retries + 1
        for attempt in range(1, attempts + 1):
            try:
                result = await asyncio.wait_for(
                    action(),
                    timeout=self._config.execution.timeout_seconds,
                )
                return result, warnings
            except TimeoutError:
                warnings.append(
                    ResearchWarning(
                        code="research_timeout",
                        domain=domain,
                        message=(f"{domain} timed out on attempt {attempt} of {attempts}."),
                        retryable=True,
                    )
                )
            except AppError as exc:
                warnings.append(
                    ResearchWarning(
                        code=exc.code,
                        domain=domain,
                        message=exc.message,
                        retryable=exc.retryable,
                    )
                )
                if not exc.retryable:
                    break
            except Exception as exc:
                warnings.append(
                    ResearchWarning(
                        code="unexpected_error",
                        domain=domain,
                        message=str(exc),
                        retryable=False,
                    )
                )
                break
        return None, warnings

    def _dedupe_citations(self, responses: Any) -> list[Citation]:
        deduped: dict[tuple[str, str, str, str], Citation] = {}
        for response in responses:
            result = self._extract_result(response)
            if result is None:
                continue
            for citation in result.citations:
                key = (
                    citation.source_name,
                    citation.source_url,
                    citation.source_type,
                    citation.note or "",
                )
                deduped[key] = citation
        return list(deduped.values())

    def _dedupe_warnings(
        self,
        warnings: list[ResearchWarning],
    ) -> list[ResearchWarning]:
        deduped: dict[tuple[str, str, str], ResearchWarning] = {}
        for warning in warnings:
            deduped[(warning.domain, warning.code, warning.message)] = warning
        return list(deduped.values())

    def _extract_result(
        self,
        response: Any,
        _: type[Any] | None = None,
    ) -> Any | None:
        if response is None:
            return None
        return getattr(response, "result", None)
