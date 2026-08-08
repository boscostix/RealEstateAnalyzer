import {
  buildRerunOverridePayload,
  EMPTY_RERUN_OVERRIDES,
  parentVersionLabel,
  versionNavigation,
} from "@/lib/history-workflow";
import type { AnalysisSummary } from "@/lib/api/types";

const analyses: AnalysisSummary[] = [
  {
    id: "analysis-v1",
    property_id: "prop-123",
    version: 1,
    status: "completed",
    created_at: "2026-08-08T12:00:00Z",
  },
  {
    id: "analysis-v2",
    property_id: "prop-123",
    version: 2,
    status: "completed",
    parent_analysis_id: "analysis-v1",
    created_at: "2026-08-08T13:00:00Z",
  },
  {
    id: "analysis-v3",
    property_id: "prop-123",
    version: 3,
    status: "running",
    created_at: "2026-08-08T14:00:00Z",
  },
];

describe("history workflow helpers", () => {
  it("builds nested rerun override payloads", () => {
    expect(
      buildRerunOverridePayload({
        interest_rate_percent: "7.10",
        monthly_rent: "3500",
        purchase_price: "",
      }),
    ).toEqual({
      assumption_overrides: {
        financing: { interest_rate_percent: "7.10" },
        income: { monthly_rent: "3500" },
      },
    });
  });

  it("returns parent version labels when lineage is present", () => {
    expect(parentVersionLabel(analyses[1], analyses)).toBe("Rerun of v1");
  });

  it("computes previous and next version navigation", () => {
    expect(versionNavigation("analysis-v2", analyses)).toMatchObject({
      latest: analyses[2],
      previous: analyses[0],
      next: analyses[2],
    });
  });

  it("keeps empty rerun overrides empty", () => {
    expect(buildRerunOverridePayload(EMPTY_RERUN_OVERRIDES)).toEqual({
      assumption_overrides: {},
    });
  });
});
