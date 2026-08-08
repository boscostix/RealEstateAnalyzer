import type {
  AnalysisDetail,
  AnalysisRerunRequest,
  AnalysisSummary,
} from "@/lib/api/types";

export type RerunOverrideFormValues = {
  interest_rate_percent: string;
  monthly_rent: string;
  purchase_price: string;
};

export const EMPTY_RERUN_OVERRIDES: RerunOverrideFormValues = {
  interest_rate_percent: "",
  monthly_rent: "",
  purchase_price: "",
};

export function buildRerunOverridePayload(
  values: RerunOverrideFormValues,
): AnalysisRerunRequest {
  const assumptionOverrides: Record<string, unknown> = {};

  if (values.purchase_price.trim() !== "") {
    assumptionOverrides.purchase_price = values.purchase_price.trim();
  }
  if (values.interest_rate_percent.trim() !== "") {
    assumptionOverrides.financing = {
      interest_rate_percent: values.interest_rate_percent.trim(),
    };
  }
  if (values.monthly_rent.trim() !== "") {
    assumptionOverrides.income = {
      monthly_rent: values.monthly_rent.trim(),
    };
  }

  return {
    assumption_overrides: assumptionOverrides,
  };
}

export function parentVersionLabel(
  analysis: AnalysisSummary | AnalysisDetail,
  analyses: AnalysisSummary[],
): string | null {
  if (!analysis.parent_analysis_id) {
    return null;
  }

  const parent = analyses.find((item) => item.id === analysis.parent_analysis_id);
  if (!parent) {
    return "Rerun of earlier analysis";
  }

  return `Rerun of v${parent.version}`;
}

export function versionNavigation(
  currentAnalysisId: string,
  analyses: AnalysisSummary[],
): {
  previous: AnalysisSummary | null;
  next: AnalysisSummary | null;
  latest: AnalysisSummary | null;
} {
  const ordered = [...analyses].sort((left, right) => right.version - left.version);
  const currentIndex = ordered.findIndex((analysis) => analysis.id === currentAnalysisId);

  return {
    latest: ordered[0] ?? null,
    previous: currentIndex >= 0 && currentIndex < ordered.length - 1 ? ordered[currentIndex + 1] : null,
    next: currentIndex > 0 ? ordered[currentIndex - 1] : null,
  };
}
