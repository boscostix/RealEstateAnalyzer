import {
  analysisHeadline,
  completedReportPath,
  deriveStageDescriptors,
  shouldPollAnalysis,
} from "@/lib/progress-workflow";
import type { AnalysisDetail } from "@/lib/api/types";

const baseAnalysis: AnalysisDetail = {
  id: "analysis-123",
  property_id: "prop-123",
  version: 1,
  status: "running",
  current_stage: "research",
  created_at: "2026-08-08T12:00:00Z",
};

describe("progress workflow helpers", () => {
  it("polls only for pending and running analyses", () => {
    expect(shouldPollAnalysis("pending")).toBe(true);
    expect(shouldPollAnalysis("running")).toBe(true);
    expect(shouldPollAnalysis("completed")).toBe(false);
    expect(shouldPollAnalysis("failed")).toBe(false);
  });

  it("marks current and completed stages for a running analysis", () => {
    const stages = deriveStageDescriptors("running", "research", null);

    expect(stages.map((stage) => stage.state)).toEqual([
      "completed",
      "completed",
      "current",
      "upcoming",
      "upcoming",
      "upcoming",
    ]);
  });

  it("marks the failure stage without inventing later progress", () => {
    const stages = deriveStageDescriptors("failed", "research", "agent_research");

    expect(stages.map((stage) => stage.state)).toEqual([
      "completed",
      "completed",
      "completed",
      "failed",
      "upcoming",
      "upcoming",
    ]);
  });

  it("returns the report destination and completed headline", () => {
    expect(completedReportPath("analysis-123")).toBe("/analyses/analysis-123/report");
    expect(
      analysisHeadline({
        ...baseAnalysis,
        status: "completed",
        current_stage: "persistence",
      }),
    ).toBe("Analysis completed successfully.");
  });
});
