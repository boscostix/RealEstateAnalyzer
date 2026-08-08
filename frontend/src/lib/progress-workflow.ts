import type { AnalysisDetail } from "@/lib/api/types";

export const ANALYSIS_STAGES = [
  "preparation",
  "underwriting",
  "research",
  "agent_research",
  "investment_committee",
  "persistence",
] as const;

export type AnalysisStageValue = (typeof ANALYSIS_STAGES)[number];
export type StageState = "completed" | "current" | "upcoming" | "failed";

export type StageDescriptor = {
  key: AnalysisStageValue;
  label: string;
  description: string;
  state: StageState;
};

const STAGE_COPY: Record<AnalysisStageValue, Omit<StageDescriptor, "state">> = {
  preparation: {
    key: "preparation",
    label: "Preparation",
    description: "Load the property snapshot, assumptions, and execution inputs.",
  },
  underwriting: {
    key: "underwriting",
    label: "Underwriting",
    description: "Run the deterministic underwriting engine using the verified property.",
  },
  research: {
    key: "research",
    label: "Research",
    description: "Assemble supporting research and property diligence inputs.",
  },
  agent_research: {
    key: "agent_research",
    label: "Agent Research",
    description: "Generate the structured agent research package.",
  },
  investment_committee: {
    key: "investment_committee",
    label: "Investment Committee",
    description: "Prepare the decision output and recommendation package.",
  },
  persistence: {
    key: "persistence",
    label: "Persistence",
    description: "Save completed analysis outputs and finalize the record.",
  },
};

export function shouldPollAnalysis(status: string | null | undefined): boolean {
  return status === "pending" || status === "running";
}

export function completedReportPath(analysisId: string): string {
  return `/analyses/${analysisId}/report`;
}

export function deriveStageDescriptors(
  status: string,
  currentStage: string | null | undefined,
  failureStage: string | null | undefined,
): StageDescriptor[] {
  const currentIndex = stageIndex(currentStage);
  const failureIndex = stageIndex(failureStage);

  return ANALYSIS_STAGES.map((stage, index) => {
    let state: StageState = "upcoming";

    if (status === "completed") {
      state = "completed";
    } else if (status === "failed") {
      if (failureIndex !== -1 && index < failureIndex) {
        state = "completed";
      } else if (failureIndex !== -1 && index === failureIndex) {
        state = "failed";
      } else if (failureIndex === -1 && currentIndex !== -1 && index < currentIndex) {
        state = "completed";
      } else if (failureIndex === -1 && currentIndex !== -1 && index === currentIndex) {
        state = "failed";
      }
    } else if (currentIndex === -1) {
      state = index === 0 ? "current" : "upcoming";
    } else if (index < currentIndex) {
      state = "completed";
    } else if (index === currentIndex) {
      state = "current";
    }

    return {
      ...STAGE_COPY[stage],
      state,
    };
  });
}

export function analysisHeadline(analysis: AnalysisDetail): string {
  switch (analysis.status) {
    case "pending":
      return "Analysis is queued and waiting to begin.";
    case "running":
      return "Analysis is currently running.";
    case "failed":
      return "Analysis stopped before completion.";
    case "completed":
      return "Analysis completed successfully.";
    default:
      return "Analysis status is available.";
  }
}

export function analysisSubhead(analysis: AnalysisDetail): string {
  switch (analysis.status) {
    case "pending":
      return "The persisted analysis record exists and the background execution service has not started substantive work yet.";
    case "running":
      return analysis.current_stage
        ? `The current persisted stage is ${humanizeStage(analysis.current_stage)}.`
        : "The analysis is running and waiting to report its current stage.";
    case "failed":
      return analysis.error_message ??
        "A safe failure message is available below, and the analysis can be rerun without mutating prior history.";
    case "completed":
      return "The progress poll has stopped and the workflow can move into the completed report view.";
    default:
      return "This page follows the persisted analysis lifecycle without estimating progress.";
  }
}

export function humanizeStage(stage: string): string {
  return stage.replaceAll("_", " ");
}

function stageIndex(stage: string | null | undefined): number {
  if (!stage) {
    return -1;
  }

  return ANALYSIS_STAGES.indexOf(stage as AnalysisStageValue);
}
