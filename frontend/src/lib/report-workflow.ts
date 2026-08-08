import type { AnalysisDetail, InvestmentCommitteeOutput } from "@/lib/api/types";

export type RecommendationTone = "success" | "warning" | "danger" | "neutral";

export type OfferSectionData = {
  askingPrice: string | number | null;
  supportedLow: string | number | null;
  supportedHigh: string | number | null;
  bindingMaximum: string | number | null;
  askingGap: string | number | null;
  basis: Array<{
    label: string;
    value: string | number | null;
    description: string;
  }>;
  hasMeaningfulData: boolean;
};

const RECOMMENDATION_LABELS: Record<string, string> = {
  strong_buy: "Strong Buy",
  buy: "Buy",
  buy_only_below: "Buy Only Below",
  negotiate: "Negotiate",
  watch: "Watch",
  pass: "Pass",
  insufficient_information: "Insufficient Information",
};

const RECOMMENDATION_TONES: Record<string, RecommendationTone> = {
  strong_buy: "success",
  buy: "success",
  buy_only_below: "warning",
  negotiate: "warning",
  watch: "neutral",
  pass: "danger",
  insufficient_information: "neutral",
};

export function recommendationLabel(recommendation: string | null | undefined): string {
  if (!recommendation) {
    return "Recommendation unavailable";
  }

  return RECOMMENDATION_LABELS[recommendation] ?? recommendation.replaceAll("_", " ");
}

export function recommendationTone(
  recommendation: string | null | undefined,
): RecommendationTone {
  if (!recommendation) {
    return "neutral";
  }

  return RECOMMENDATION_TONES[recommendation] ?? "neutral";
}

export function deriveOfferSection(analysis: AnalysisDetail): OfferSectionData {
  const committee = analysis.investment_committee;
  const maximumOffer = recordValue(analysis.underwriting, "maximum_offer");

  const askingPrice = scalarValue(committee, "asking_price");
  const supportedLow = scalarValue(committee, "supported_offer_low");
  const supportedHigh = scalarValue(committee, "supported_offer_high");
  const bindingMaximum = scalarValue(maximumOffer, "binding_maximum_price");
  const askingGap = scalarValue(maximumOffer, "asking_price_gap");
  const basisFromCommittee = committee?.recommended_offer_basis ?? [];
  const basis =
    basisFromCommittee.length > 0
      ? basisFromCommittee.map((item) => ({
          label: item.source_metric,
          value: item.value ?? null,
          description: item.description,
        }))
      : defaultOfferBasis(maximumOffer);

  return {
    askingPrice,
    supportedLow,
    supportedHigh,
    bindingMaximum,
    askingGap,
    basis,
    hasMeaningfulData:
      askingPrice !== null ||
      supportedLow !== null ||
      supportedHigh !== null ||
      bindingMaximum !== null ||
      basis.length > 0,
  };
}

export function executiveSummaryLines(
  committee: InvestmentCommitteeOutput | null | undefined,
): string[] {
  if (!committee) {
    return [];
  }

  return [
    committee.recommendation_summary,
    committee.strongest_upside,
    committee.strongest_downside,
  ].filter((line): line is string => Boolean(line && line.trim()));
}

function defaultOfferBasis(
  maximumOffer: Record<string, unknown> | null,
): OfferSectionData["basis"] {
  const candidates = [
    {
      key: "binding_maximum_price",
      label: "Binding maximum",
      description: "Most restrictive deterministic maximum-offer threshold.",
    },
    {
      key: "break_even_cash_flow_price",
      label: "Break-even threshold",
      description: "Price support from the break-even cash flow threshold.",
    },
    {
      key: "target_monthly_cash_flow_price",
      label: "Target cash flow threshold",
      description: "Price support from the target monthly cash flow hurdle.",
    },
    {
      key: "target_cap_rate_price",
      label: "Target cap rate threshold",
      description: "Price support from the target cap rate hurdle.",
    },
    {
      key: "target_cash_on_cash_price",
      label: "Target cash-on-cash threshold",
      description: "Price support from the target cash-on-cash hurdle.",
    },
    {
      key: "target_dscr_price",
      label: "Target DSCR threshold",
      description: "Price support from the target DSCR hurdle.",
    },
  ];

  return candidates
    .map((candidate) => ({
      label: candidate.label,
      value: scalarValue(maximumOffer, candidate.key),
      description: candidate.description,
    }))
    .filter((candidate) => candidate.value !== null);
}

function recordValue(
  record: Record<string, unknown> | null | undefined,
  key: string,
): Record<string, unknown> | null {
  const value = record?.[key];
  return value && typeof value === "object" ? (value as Record<string, unknown>) : null;
}

function scalarValue(
  record: Record<string, unknown> | null | undefined,
  key: string,
): string | number | null {
  const value = record?.[key];
  return typeof value === "string" || typeof value === "number" ? value : null;
}
