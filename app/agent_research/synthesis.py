"""Unified synthesis service for the complete structured agent workflow."""

from __future__ import annotations

import hashlib
import time
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal

from app.agent_research.api_models import AgentResearchRunRequest, AgentResearchRunResponse
from app.agent_research.conflicts import analyze_conflicts
from app.agent_research.context import AgentRunContext, ResearchServiceContainer
from app.agent_research.exceptions import MissingAgentInputError, SynthesisFailureError
from app.agent_research.input_builders import build_property_risk_agent_input
from app.agent_research.models import (
    AgentExecutionMetadata,
    AgentFinding,
    AgentResearchOutput,
    CrossDomainRelationship,
    DuplicateFindingGroup,
    EvidenceReference,
    ResearchConflict,
    UnifiedAgentResearchPackage,
)
from app.agent_research.orchestration_models import AgentRunRecord, SpecialistWorkflowResult
from app.agent_research.orchestrator import SpecialistAgentOrchestrator
from app.agent_research.risk_models import PropertyRiskAgentOutput
from app.agent_research.services import PropertyRiskAgentService
from app.agent_research.versioning import WORKFLOW_VERSION
from app.models.research_package import ResearchPackage, ResearchPackageRequest
from app.services.neighborhood_service import NeighborhoodService
from app.services.public_records_service import PublicRecordsService
from app.services.rental_comps_service import RentalCompsService
from app.services.research_orchestrator import ResearchOrchestrator
from app.services.sales_comps_service import SalesCompsService


class UnifiedSynthesisService:
    """Runs the complete agent workflow and assembles the final package."""

    def __init__(
        self,
        *,
        specialist_orchestrator: SpecialistAgentOrchestrator | None = None,
        risk_agent_service: PropertyRiskAgentService | None = None,
        research_orchestrator: ResearchOrchestrator | None = None,
        public_records_service: PublicRecordsService | None = None,
        sales_comps_service: SalesCompsService | None = None,
        rental_comps_service: RentalCompsService | None = None,
        neighborhood_service: NeighborhoodService | None = None,
    ) -> None:
        self._specialist_orchestrator = specialist_orchestrator or SpecialistAgentOrchestrator()
        self._risk_agent_service = risk_agent_service or PropertyRiskAgentService()
        self._research_orchestrator = research_orchestrator or ResearchOrchestrator(
            public_records_service=public_records_service,
            sales_comps_service=sales_comps_service,
            rental_comps_service=rental_comps_service,
            neighborhood_service=neighborhood_service,
        )
        self._public_records_service = public_records_service
        self._sales_comps_service = sales_comps_service
        self._rental_comps_service = rental_comps_service
        self._neighborhood_service = neighborhood_service

    async def run(
        self,
        *,
        request_id: str,
        payload: AgentResearchRunRequest,
    ) -> AgentResearchRunResponse:
        started_perf = time.perf_counter()
        research_package = await self._load_research_package(payload)
        context = AgentRunContext(
            request_id=request_id,
            analysis_id=payload.analysis_id,
            verified_property=payload.verified_property,
            listing_extraction=payload.listing_extraction,
            underwriting_result=payload.underwriting_result,
            research_package=research_package,
            research_services=ResearchServiceContainer(
                public_records_service=self._public_records_service,
                sales_comps_service=self._sales_comps_service,
                rental_comps_service=self._rental_comps_service,
                neighborhood_service=self._neighborhood_service,
            ),
            agent_config=self._specialist_orchestrator._config,  # noqa: SLF001
        )

        specialist_response = await self._specialist_orchestrator.run(context)
        if specialist_response.result is None:
            raise SynthesisFailureError(message="Specialist workflow did not return a result.")
        specialist_result = specialist_response.result

        listing_analysis = specialist_result.listing_analysis
        public_records_analysis = specialist_result.public_records_analysis
        comparable_analysis = specialist_result.comparable_analysis
        neighborhood_analysis = specialist_result.neighborhood_analysis

        conflicts: list[ResearchConflict] = []
        duplicate_findings: list[DuplicateFindingGroup] = []
        overall_data_confidence = Decimal("0")
        synthesis_warnings: list[str] = []
        risk_analysis: PropertyRiskAgentOutput | None = None
        risk_record: AgentRunRecord | None = None
        risk_warning: str | None = None
        risk_duration_ms = 0

        if (
            listing_analysis is not None
            and public_records_analysis is not None
            and comparable_analysis is not None
            and neighborhood_analysis is not None
        ):
            conflict_result = analyze_conflicts(
                verified_property=payload.verified_property,
                listing_extraction=payload.listing_extraction,
                research_package=research_package,
                listing_analysis=listing_analysis,
                public_records_analysis=public_records_analysis,
                comparable_analysis=comparable_analysis,
                neighborhood_analysis=neighborhood_analysis,
            )
            conflicts = conflict_result.conflicts
            duplicate_findings = conflict_result.duplicate_findings
            overall_data_confidence = conflict_result.overall_data_confidence
            synthesis_warnings.extend(conflict_result.warnings)

            risk_started = time.perf_counter()
            risk_input = await build_property_risk_agent_input(
                context,
                listing_analysis=listing_analysis,
                public_records_analysis=public_records_analysis,
                comparable_analysis=comparable_analysis,
                neighborhood_analysis=neighborhood_analysis,
                conflicts=conflicts,
                duplicate_findings=duplicate_findings,
                upstream_data_confidence=overall_data_confidence,
                upstream_warnings=specialist_result.warnings,
            )
            try:
                risk_run_result = await self._risk_agent_service.run_with_record(
                    context,
                    built_input=risk_input,
                )
                risk_analysis = risk_run_result.output
                risk_record = risk_run_result.record
            except Exception as exc:  # pragma: no cover - exercised via service stubs in API tests
                risk_warning = str(exc)
            risk_duration_ms = int((time.perf_counter() - risk_started) * 1000)
        else:
            risk_warning = "risk_agent_skipped_missing_upstream_agents"
            overall_data_confidence = Decimal("0.40")

        consolidated_findings = self._consolidate_findings(
            listing_analysis,
            public_records_analysis,
            comparable_analysis,
            neighborhood_analysis,
            risk_analysis,
            duplicate_findings,
        )
        cross_domain_relationships = self._group_relationships(consolidated_findings)
        evidence_index = self._collect_evidence_index(
            consolidated_findings,
            risk_analysis,
        )
        missing_information = self._collect_missing_information(
            listing_analysis,
            public_records_analysis,
            comparable_analysis,
            neighborhood_analysis,
            risk_analysis,
        )
        due_diligence_questions = self._collect_due_diligence_questions(
            listing_analysis,
            public_records_analysis,
            comparable_analysis,
            neighborhood_analysis,
            risk_analysis,
        )
        warnings = self._dedupe_strings(
            [
                *specialist_result.warnings,
                *synthesis_warnings,
                *([risk_warning] if risk_warning is not None else []),
                *(risk_analysis.warnings if risk_analysis is not None else []),
            ]
        )
        execution_metadata = self._build_execution_metadata(
            request_id=request_id,
            specialist_result=specialist_result,
            listing_analysis=listing_analysis,
            public_records_analysis=public_records_analysis,
            comparable_analysis=comparable_analysis,
            neighborhood_analysis=neighborhood_analysis,
            risk_analysis=risk_analysis,
            risk_record=risk_record,
            risk_duration_ms=risk_duration_ms,
            total_duration_ms=int((time.perf_counter() - started_perf) * 1000),
            warnings=warnings,
        )
        package = UnifiedAgentResearchPackage(
            listing_analysis=listing_analysis,
            public_records_analysis=public_records_analysis,
            comparable_analysis=comparable_analysis,
            neighborhood_analysis=neighborhood_analysis,
            risk_analysis=risk_analysis,
            consolidated_findings=consolidated_findings,
            cross_domain_relationships=cross_domain_relationships,
            conflicts=conflicts,
            duplicate_findings=duplicate_findings,
            missing_information=missing_information,
            due_diligence_questions=due_diligence_questions,
            evidence_index=evidence_index,
            overall_data_confidence=overall_data_confidence,
            warnings=warnings,
            execution_metadata=execution_metadata,
        )
        return AgentResearchRunResponse(
            success=any(
                output is not None
                for output in (
                    listing_analysis,
                    public_records_analysis,
                    comparable_analysis,
                    neighborhood_analysis,
                    risk_analysis,
                )
            ),
            package=package,
            warnings=warnings,
        )

    async def _load_research_package(
        self,
        payload: AgentResearchRunRequest,
    ) -> ResearchPackage:
        if payload.research_package is not None:
            return payload.research_package
        response = await self._research_orchestrator.research(
            ResearchPackageRequest(
                property=payload.verified_property,
                bypass_cache=payload.bypass_research_cache,
            )
        )
        if response.package is None:
            raise MissingAgentInputError(message="Deterministic research package is unavailable.")
        return response.package

    def _consolidate_findings(
        self,
        listing_analysis: AgentResearchOutput | None,
        public_records_analysis: AgentResearchOutput | None,
        comparable_analysis: AgentResearchOutput | None,
        neighborhood_analysis: AgentResearchOutput | None,
        risk_analysis: PropertyRiskAgentOutput | None,
        duplicate_findings: list[DuplicateFindingGroup],
    ) -> list[AgentFinding]:
        findings: dict[str, AgentFinding] = {}
        duplicate_ids = {
            duplicate_finding_id
            for group in duplicate_findings
            for duplicate_finding_id in group.duplicate_finding_ids
        }
        for output in (
            listing_analysis,
            public_records_analysis,
            comparable_analysis,
            neighborhood_analysis,
            risk_analysis,
        ):
            if output is None:
                continue
            for finding in output.findings:
                if finding.finding_id in duplicate_ids:
                    continue
                findings.setdefault(finding.finding_id, finding)
        return list(findings.values())

    def _group_relationships(
        self,
        consolidated_findings: list[AgentFinding],
    ) -> list[CrossDomainRelationship]:
        grouped: dict[str, list[AgentFinding]] = defaultdict(list)
        for finding in consolidated_findings:
            for field_name in finding.affected_fields or [finding.category]:
                grouped[field_name].append(finding)

        relationships: list[CrossDomainRelationship] = []
        for topic, findings in sorted(grouped.items()):
            if len(findings) < 2:
                continue
            evidence = self._dedupe_evidence(
                [reference for finding in findings for reference in finding.evidence]
            )
            relationship_id = hashlib.sha256(topic.encode("utf-8")).hexdigest()[:16]
            agent_names = sorted(
                {
                    reference.source_id.split(":")[0]
                    for finding in findings
                    for reference in finding.evidence
                }
            )
            affected_fields = sorted(
                {field_name for finding in findings for field_name in finding.affected_fields}
            )
            relationships.append(
                CrossDomainRelationship(
                    relationship_id=relationship_id,
                    topic=topic,
                    summary=f"Multiple findings reference {topic}.",
                    finding_ids=[finding.finding_id for finding in findings],
                    agent_names=agent_names,
                    affected_fields=affected_fields,
                    evidence=evidence,
                )
            )
        return relationships

    def _collect_evidence_index(
        self,
        consolidated_findings: list[AgentFinding],
        risk_analysis: PropertyRiskAgentOutput | None,
    ) -> list[EvidenceReference]:
        evidence = [
            reference for finding in consolidated_findings for reference in finding.evidence
        ]
        if risk_analysis is not None:
            for risk in risk_analysis.risk_findings:
                evidence.extend(risk.evidence)
            for item in risk_analysis.inspection_priorities:
                evidence.extend(item.evidence)
            for question in risk_analysis.seller_questions:
                evidence.extend(question.evidence)
        return self._dedupe_evidence(evidence)

    def _collect_missing_information(
        self,
        listing_analysis: AgentResearchOutput | None,
        public_records_analysis: AgentResearchOutput | None,
        comparable_analysis: AgentResearchOutput | None,
        neighborhood_analysis: AgentResearchOutput | None,
        risk_analysis: PropertyRiskAgentOutput | None,
    ) -> list[str]:
        collected: list[str] = []
        for output in (
            listing_analysis,
            public_records_analysis,
            comparable_analysis,
            neighborhood_analysis,
            risk_analysis,
        ):
            if output is None:
                continue
            collected.extend(output.missing_information)
            if isinstance(output, PropertyRiskAgentOutput):
                for risk in output.risk_findings:
                    collected.extend(risk.missing_information)
        return self._dedupe_strings(collected)

    def _collect_due_diligence_questions(
        self,
        listing_analysis: AgentResearchOutput | None,
        public_records_analysis: AgentResearchOutput | None,
        comparable_analysis: AgentResearchOutput | None,
        neighborhood_analysis: AgentResearchOutput | None,
        risk_analysis: PropertyRiskAgentOutput | None,
    ) -> list[str]:
        questions: list[str] = []
        for output in (
            listing_analysis,
            public_records_analysis,
            comparable_analysis,
            neighborhood_analysis,
            risk_analysis,
        ):
            if output is None:
                continue
            questions.extend(output.due_diligence_questions)
        if risk_analysis is not None:
            questions.extend(question.question for question in risk_analysis.seller_questions)
        return self._dedupe_strings(questions)

    def _build_execution_metadata(
        self,
        *,
        request_id: str,
        specialist_result: SpecialistWorkflowResult,
        listing_analysis: AgentResearchOutput | None,
        public_records_analysis: AgentResearchOutput | None,
        comparable_analysis: AgentResearchOutput | None,
        neighborhood_analysis: AgentResearchOutput | None,
        risk_analysis: PropertyRiskAgentOutput | None,
        risk_record: AgentRunRecord | None,
        risk_duration_ms: int,
        total_duration_ms: int,
        warnings: list[str],
    ) -> AgentExecutionMetadata:
        specialist_metadata = specialist_result.metadata
        outputs = [
            output
            for output in (
                listing_analysis,
                public_records_analysis,
                comparable_analysis,
                neighborhood_analysis,
                risk_analysis,
            )
            if output is not None
        ]
        agent_versions = {output.agent_name: output.agent_version for output in outputs}
        agent_latencies_ms = {
            str(record.agent_name): record.duration_ms for record in specialist_metadata.run_records
        }
        if risk_analysis is not None:
            agent_latencies_ms[str(risk_analysis.agent_name)] = risk_duration_ms
        usage_requests = specialist_metadata.usage.requests + (
            0 if risk_record is None else risk_record.usage.requests
        )
        usage_input_tokens = specialist_metadata.usage.input_tokens + (
            0 if risk_record is None else risk_record.usage.input_tokens
        )
        usage_output_tokens = specialist_metadata.usage.output_tokens + (
            0 if risk_record is None else risk_record.usage.output_tokens
        )
        usage_total_tokens = specialist_metadata.usage.total_tokens + (
            0 if risk_record is None else risk_record.usage.total_tokens
        )
        trace_metadata = dict(specialist_metadata.trace_metadata)
        trace_metadata["workflow_name"] = specialist_metadata.workflow_name
        trace_metadata["prompt_version"] = self._prompt_version(outputs)
        trace_metadata["trace_enabled"] = str(
            self._specialist_orchestrator._config.tracing.enabled  # noqa: SLF001
        ).lower()
        if risk_record is not None:
            trace_metadata["risk_tool_call_count"] = risk_record.trace_metadata.get(
                "tool_call_count",
                "0",
            )
            trace_metadata["risk_llm_call_count"] = risk_record.trace_metadata.get(
                "llm_call_count",
                "0",
            )
        return AgentExecutionMetadata(
            request_id=request_id,
            workflow_name=specialist_metadata.workflow_name,
            workflow_version=WORKFLOW_VERSION,
            prompt_version=self._prompt_version(outputs),
            model_name=self._model_name(),
            agent_versions=agent_versions,
            started_at=specialist_metadata.started_at,
            completed_at=datetime.now(UTC),
            total_duration_ms=total_duration_ms,
            agent_latencies_ms=agent_latencies_ms,
            traced=self._specialist_orchestrator._config.tracing.enabled,  # noqa: SLF001
            usage_requests=usage_requests,
            usage_input_tokens=usage_input_tokens,
            usage_output_tokens=usage_output_tokens,
            usage_total_tokens=usage_total_tokens,
            trace_metadata=trace_metadata,
            partial_failure=(specialist_metadata.partial_failure or risk_analysis is None),
            warnings=warnings,
        )

    def _prompt_version(self, outputs: list[AgentResearchOutput]) -> str:
        for output in outputs:
            if output.prompt_version:
                return output.prompt_version
        return "v1"

    def _model_name(self) -> str:
        return self._specialist_orchestrator._config.model  # noqa: SLF001

    def _dedupe_evidence(
        self,
        evidence: list[EvidenceReference],
    ) -> list[EvidenceReference]:
        deduped: dict[tuple[str, str, str | None, str | None], EvidenceReference] = {}
        for reference in evidence:
            key = (
                reference.source_id,
                reference.source_type,
                reference.citation_id,
                reference.field_path,
            )
            deduped[key] = reference
        return list(deduped.values())

    def _dedupe_strings(self, values: list[str]) -> list[str]:
        seen: dict[str, str] = {}
        for value in values:
            normalized = value.strip()
            if normalized:
                seen.setdefault(normalized.lower(), normalized)
        return list(seen.values())
