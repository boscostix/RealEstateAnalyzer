"""Shared AI agent research foundation for structured orchestration."""

from app.agent_research.config import AgentRuntimeConfig, AgentTracingConfig
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
from app.agent_research.models import (
    AgentConflictCandidate,
    AgentExecutionMetadata,
    AgentFinding,
    AgentResearchOutput,
    ConflictMateriality,
    ConflictResolutionStatus,
    ConflictValue,
    EvidenceReference,
    FindingSeverity,
    ResearchConflict,
    UnifiedAgentResearchPackage,
)
from app.agent_research.sdk import AgentRunnerProtocol, OpenAIAgentRunner
from app.agent_research.tools import tools_for_agent

__all__ = [
    "AGENT_DEFINITIONS",
    "AgentConflictCandidate",
    "AgentExecutionMetadata",
    "AgentFinding",
    "AgentResearchError",
    "AgentResearchOutput",
    "AgentRunContext",
    "AgentRunnerProtocol",
    "AgentRuntimeConfig",
    "AgentTracingConfig",
    "ConflictMateriality",
    "ConflictResolutionStatus",
    "ConflictValue",
    "EvidenceIndex",
    "EvidenceReference",
    "FindingSeverity",
    "OpenAIAgentRunner",
    "ResearchConflict",
    "ResearchServiceContainer",
    "UnifiedAgentResearchPackage",
    "build_evidence_index",
    "build_property_key",
    "build_specialist_agents",
    "tools_for_agent",
    "validate_evidence_reference",
    "validate_evidence_references",
    "validate_source_ownership",
]
