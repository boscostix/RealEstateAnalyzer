"""Shared AI agent research foundation for structured orchestration."""

from app.agent_research.config import AgentRuntimeConfig, AgentTracingConfig
from app.agent_research.conflicts import ConflictAnalysisResult, analyze_conflicts
from app.agent_research.context import AgentRunContext, ResearchServiceContainer
from app.agent_research.definitions import AGENT_DEFINITIONS, build_specialist_agents
from app.agent_research.evidence import (
    EvidenceIndex,
    build_evidence_index,
    build_property_key,
    validate_evidence_reference,
    validate_evidence_references,
    validate_source_ownership,
)
from app.agent_research.exceptions import AgentResearchError
from app.agent_research.guardrails import guardrails_for_agent, validate_agent_output
from app.agent_research.input_builders import (
    build_comparable_agent_input,
    build_listing_agent_input,
    build_neighborhood_agent_input,
    build_public_records_agent_input,
)
from app.agent_research.models import (
    AgentConflictCandidate,
    AgentExecutionMetadata,
    AgentFinding,
    AgentResearchOutput,
    ConflictMateriality,
    ConflictResolutionStatus,
    ConflictValue,
    DuplicateFindingGroup,
    EvidenceReference,
    FindingSeverity,
    ResearchConflict,
    UnifiedAgentResearchPackage,
)
from app.agent_research.orchestration_models import (
    AgentRunRecord,
    AgentRunStatus,
    AgentUsageSummary,
    SpecialistWorkflowMetadata,
    SpecialistWorkflowResponse,
    SpecialistWorkflowResult,
    WorkflowStatus,
)
from app.agent_research.orchestrator import SpecialistAgentOrchestrator
from app.agent_research.prompts import SPECIALIST_PROMPTS, prompt_for_agent
from app.agent_research.sdk import AgentRunnerProtocol, OpenAIAgentRunner
from app.agent_research.services import (
    ComparableAgentService,
    ListingAgentService,
    NeighborhoodAgentService,
    PublicRecordsAgentService,
    SpecialistAgentService,
)
from app.agent_research.specialist_models import (
    ComparableAgentInput,
    ComparableAgentOutput,
    ListingAgentInput,
    ListingAgentOutput,
    NeighborhoodAgentInput,
    NeighborhoodAgentOutput,
    PublicRecordsAgentInput,
    PublicRecordsAgentOutput,
)
from app.agent_research.tools import tools_for_agent

__all__ = [
    "AGENT_DEFINITIONS",
    "AgentConflictCandidate",
    "AgentExecutionMetadata",
    "AgentFinding",
    "AgentResearchError",
    "AgentResearchOutput",
    "AgentRunRecord",
    "AgentRunStatus",
    "AgentRunContext",
    "AgentRunnerProtocol",
    "AgentRuntimeConfig",
    "AgentTracingConfig",
    "AgentUsageSummary",
    "ComparableAgentInput",
    "ComparableAgentOutput",
    "ComparableAgentService",
    "ConflictAnalysisResult",
    "ConflictMateriality",
    "ConflictResolutionStatus",
    "ConflictValue",
    "DuplicateFindingGroup",
    "EvidenceIndex",
    "EvidenceReference",
    "FindingSeverity",
    "ListingAgentInput",
    "ListingAgentOutput",
    "ListingAgentService",
    "NeighborhoodAgentInput",
    "NeighborhoodAgentOutput",
    "NeighborhoodAgentService",
    "OpenAIAgentRunner",
    "PublicRecordsAgentInput",
    "PublicRecordsAgentOutput",
    "PublicRecordsAgentService",
    "ResearchConflict",
    "ResearchServiceContainer",
    "SPECIALIST_PROMPTS",
    "SpecialistAgentOrchestrator",
    "SpecialistAgentService",
    "SpecialistWorkflowMetadata",
    "SpecialistWorkflowResponse",
    "SpecialistWorkflowResult",
    "UnifiedAgentResearchPackage",
    "WorkflowStatus",
    "build_evidence_index",
    "build_comparable_agent_input",
    "build_listing_agent_input",
    "build_neighborhood_agent_input",
    "build_property_key",
    "build_public_records_agent_input",
    "build_specialist_agents",
    "guardrails_for_agent",
    "prompt_for_agent",
    "tools_for_agent",
    "validate_agent_output",
    "validate_evidence_reference",
    "validate_evidence_references",
    "validate_source_ownership",
    "analyze_conflicts",
]
