import {
  deriveOfferSection,
  executiveSummaryLines,
  recommendationLabel,
  recommendationTone,
} from "@/lib/report-workflow";
import type { AnalysisDetail } from "@/lib/api/types";

const analysis: AnalysisDetail = {
  id: "analysis-123",
  property_id: "prop-123",
  version: 1,
  status: "completed",
  current_stage: "persistence",
  created_at: "2026-08-08T12:00:00Z",
  underwriting: {
    maximum_offer: {
      break_even_cash_flow_price: "430000",
      binding_maximum_price: "425000",
      asking_price_gap: "20000",
    },
    metrics: {
      noi: "30480",
    },
  },
  investment_committee: {
    recommendation: "negotiate",
    recommendation_summary: "Works only with a lower purchase price.",
    recommendation_confidence: "0.70",
    asking_price: "445000",
    supported_offer_low: "425000",
    supported_offer_high: "430000",
    recommended_offer_basis: [
      {
        value: "425000",
        source_metric: "Binding maximum",
        source_path: "underwriting.maximum_offer.binding_maximum_price",
        description: "Most restrictive deterministic maximum-offer threshold.",
      },
    ],
    investment_thesis: "Stabilized rental with moderate leverage.",
    strongest_upside: "Positive cash flow at the right basis.",
    strongest_downside: "Thin margin at current pricing.",
    reasons_to_proceed: [],
    reasons_not_to_proceed: [],
  },
};

describe("report workflow helpers", () => {
  it("maps recommendation labels and tones", () => {
    expect(recommendationLabel("buy_only_below")).toBe("Buy Only Below");
    expect(recommendationTone("pass")).toBe("danger");
  });

  it("builds executive summary lines from committee output", () => {
    expect(executiveSummaryLines(analysis.investment_committee)).toEqual([
      "Works only with a lower purchase price.",
      "Positive cash flow at the right basis.",
      "Thin margin at current pricing.",
    ]);
  });

  it("uses persisted offer-range values without recalculation", () => {
    const section = deriveOfferSection(analysis);

    expect(section.askingPrice).toBe("445000");
    expect(section.supportedLow).toBe("425000");
    expect(section.supportedHigh).toBe("430000");
    expect(section.bindingMaximum).toBe("425000");
    expect(section.askingGap).toBe("20000");
    expect(section.basis).toHaveLength(1);
  });
});
