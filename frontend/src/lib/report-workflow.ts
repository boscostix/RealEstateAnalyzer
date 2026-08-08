import type {
  AnalysisDetail,
  CommitteeReason,
  InvestmentCommitteeOutput,
} from "@/lib/api/types";

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

export type ComparableTableRow = {
  address: string;
  primary: string;
  secondary: string;
  tertiary: string;
  link?: string | null;
};

export type EvidencePanelData = {
  researchCitations: Array<{
    label: string;
    url: string;
    note: string;
  }>;
  evidenceReferences: Array<{
    sourceId: string;
    sourceType: string;
    locator: string;
    excerpt: string;
  }>;
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

export function scenarioCards(analysis: AnalysisDetail) {
  const scenarios = analysis.underwriting?.scenarios ?? [];
  return scenarios.map((scenario) => ({
    name: scenario.name,
    monthlyCashFlow: scenario.metrics?.monthly_pre_tax_cash_flow ?? null,
    capRate: scenario.metrics?.cap_rate ?? null,
    cashOnCash: scenario.metrics?.cash_on_cash_return ?? null,
    warnings: scenario.warnings ?? [],
    adjustments: Object.entries(scenario.adjustments ?? {}),
  }));
}

export function stressTestCards(analysis: AnalysisDetail) {
  const stressTests = analysis.underwriting?.stress_tests ?? [];
  return stressTests.map((stressTest) => ({
    identifier: stressTest.identifier,
    description: stressTest.description,
    monthlyCashFlowDelta: stressTest.change_in_monthly_cash_flow,
    annualCashFlowDelta: stressTest.change_in_annual_cash_flow,
    remainsPositive: stressTest.cash_flow_remains_positive,
    additionalCashRequired: stressTest.additional_cash_required,
    changedAssumptions: Object.entries(stressTest.changed_assumptions ?? {}),
    warnings: stressTest.warnings ?? [],
  }));
}

export function salesComparableRows(analysis: AnalysisDetail): ComparableTableRow[] {
  const sales = analysis.research?.sales_comps?.data.top_comparables ?? [];
  return sales.map((item) => ({
    address: item.address,
    primary: item.sold_price == null ? "Price N/A" : `Sold ${item.sold_price}`,
    secondary:
      item.sold_date == null
        ? "Date N/A"
        : `Sold ${item.sold_date}`,
    tertiary:
      item.distance_miles == null
        ? "Distance N/A"
        : `${item.distance_miles} mi away`,
    link: item.source_url,
  }));
}

export function rentalComparableRows(analysis: AnalysisDetail): ComparableTableRow[] {
  const rentals = analysis.research?.rental_comps?.data.best_comparables ?? [];
  return rentals.map((item) => ({
    address: item.address,
    primary: item.monthly_rent == null ? "Rent N/A" : `Rent ${item.monthly_rent}/mo`,
    secondary: item.rental_status.replaceAll("_", " "),
    tertiary:
      item.distance_miles == null
        ? "Distance N/A"
        : `${item.distance_miles} mi away`,
    link: item.source_url,
  }));
}

export function reasonsOrEmpty(reasons: CommitteeReason[] | undefined): CommitteeReason[] {
  return reasons ?? [];
}

export function riskTone(severity: string): RecommendationTone {
  switch (severity) {
    case "critical":
    case "high":
      return "danger";
    case "medium":
      return "warning";
    case "low":
      return "neutral";
    default:
      return "neutral";
  }
}

export function evidencePanelData(analysis: AnalysisDetail): EvidencePanelData {
  const citations = [
    ...(analysis.research?.metadata.citations ?? []),
    ...(analysis.research?.sales_comps?.citations ?? []),
    ...(analysis.research?.rental_comps?.citations ?? []),
    ...(analysis.research?.neighborhood?.citations ?? []),
    ...(analysis.research?.public_records?.citations ?? []),
  ];
  const uniqueCitations = new Map<string, { label: string; url: string; note: string }>();
  for (const citation of citations) {
    const key = `${citation.source_name}-${citation.source_url}-${citation.note ?? ""}`;
    if (!uniqueCitations.has(key)) {
      uniqueCitations.set(key, {
        label: citation.source_name,
        url: citation.source_url,
        note: citation.note ?? citation.source_type,
      });
    }
  }

  const references = [
    ...(analysis.agent_research?.evidence_index ?? []),
    ...(analysis.investment_committee?.evidence_references ?? []),
  ];
  const uniqueReferences = new Map<
    string,
    { sourceId: string; sourceType: string; locator: string; excerpt: string }
  >();
  for (const reference of references) {
    const locator = reference.citation_id ?? reference.field_path ?? "unspecified locator";
    const key = `${reference.source_id}-${locator}`;
    if (!uniqueReferences.has(key)) {
      uniqueReferences.set(key, {
        sourceId: reference.source_id,
        sourceType: reference.source_type,
        locator,
        excerpt: reference.supporting_excerpt ?? "No excerpt provided.",
      });
    }
  }

  return {
    researchCitations: [...uniqueCitations.values()],
    evidenceReferences: [...uniqueReferences.values()],
  };
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
