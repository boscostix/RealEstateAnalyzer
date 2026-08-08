import type {
  AnalysisDetail,
  AnalysisListResponse,
  PropertyResponse,
} from "@/lib/api/types";

export const demoPropertyResponse: PropertyResponse = {
  success: true,
  property: {
    id: "prop-demo-123",
    source_url: "https://www.zillow.com/homedetails/demo",
    provider: "zillow",
    full_address: "123 Main St, Dallas, TX 75001",
    created_at: "2026-08-08T12:00:00Z",
    updated_at: "2026-08-08T12:30:00Z",
    current_version: 3,
    analysis_count: 3,
    latest_analysis: {
      id: "analysis-demo-v3",
      property_id: "prop-demo-123",
      version: 3,
      status: "completed",
      current_stage: "persistence",
      created_at: "2026-08-08T14:00:00Z",
      completed_at: "2026-08-08T14:05:00Z",
    },
    verified_property: {
      source_url: "https://www.zillow.com/homedetails/demo",
      provider: "zillow",
      full_address: { status: "verified", final_value: "123 Main St, Dallas, TX 75001" },
      asking_price: { status: "verified", final_value: "445000" },
      bedrooms: { status: "verified", final_value: "3" },
      bathrooms: { status: "verified", final_value: "2" },
      square_feet: { status: "verified", final_value: 1800 },
      lot_square_feet: { status: "verified", final_value: 7200 },
      year_built: { status: "verified", final_value: 1999 },
      annual_property_tax: { status: "verified", final_value: "4200" },
      annual_hoa: { status: "verified", final_value: "0" },
      property_type: { status: "verified", final_value: "single_family" },
    },
  },
};

export const demoAnalysisListResponse: AnalysisListResponse = {
  success: true,
  analyses: [
    {
      id: "analysis-demo-v3",
      property_id: "prop-demo-123",
      version: 3,
      status: "completed",
      parent_analysis_id: "analysis-demo-v2",
      current_stage: "persistence",
      created_at: "2026-08-08T14:00:00Z",
      completed_at: "2026-08-08T14:05:00Z",
    },
    {
      id: "analysis-demo-v2",
      property_id: "prop-demo-123",
      version: 2,
      status: "completed",
      current_stage: "persistence",
      created_at: "2026-08-08T13:00:00Z",
      completed_at: "2026-08-08T13:06:00Z",
    },
    {
      id: "analysis-demo-v1",
      property_id: "prop-demo-123",
      version: 1,
      status: "failed",
      current_stage: "research",
      created_at: "2026-08-08T12:00:00Z",
      failed_at: "2026-08-08T12:04:00Z",
    },
  ],
};

export const demoCompletedAnalysis: AnalysisDetail = {
  id: "analysis-demo-v3",
  property_id: "prop-demo-123",
  version: 3,
  status: "completed",
  current_stage: "persistence",
  parent_analysis_id: "analysis-demo-v2",
  created_at: "2026-08-08T14:00:00Z",
  completed_at: "2026-08-08T14:05:00Z",
  underwriting: {
    acquisition: {
      total_cash_required_at_closing: "88000",
    },
    metrics: {
      noi: "30480",
      monthly_pre_tax_cash_flow: "372.08",
      cap_rate: "0.0693",
      cash_on_cash_return: "0.0507",
      dscr: "1.17",
    },
    maximum_offer: {
      break_even_cash_flow_price: "430000",
      binding_maximum_price: "425000",
      asking_price_gap: "20000",
    },
    scenarios: [
      {
        name: "conservative",
        adjustments: { rent_percent_delta: "-5" },
        metrics: { monthly_pre_tax_cash_flow: "140", cap_rate: "0.062" },
      },
      {
        name: "optimistic",
        adjustments: { rent_percent_delta: "5" },
        metrics: { monthly_pre_tax_cash_flow: "590", cap_rate: "0.074" },
      },
    ],
    stress_tests: [
      {
        identifier: "insurance_plus_15",
        description: "Insurance increases by 15 percent.",
        changed_assumptions: { insurance_percent_delta: "15" },
        change_in_monthly_cash_flow: "-45",
        change_in_annual_cash_flow: "-540",
        cash_flow_remains_positive: true,
        additional_cash_required: "0",
      },
    ],
  },
  research: {
    metadata: {
      total_duration_ms: 123,
      completed_domains: ["sales_comps", "rental_comps", "public_records"],
      citations: [
        {
          source_name: "County records",
          source_url: "https://example.com/county-records",
          source_type: "government",
          note: "Tax and ownership record",
        },
      ],
    },
    sales_comps: {
      provider: "demo",
      retrieved_at: "2026-08-08T14:03:00Z",
      metadata: {
        provider: "demo",
        domain: "sales_comps",
        provider_latency_ms: 50,
        cache_status: "hit",
      },
      confidence: { value: "0.82" },
      data: {
        summary: {
          comparable_count: 2,
          median_sold_price: "438000",
          sold_price_range: { low: "430000", high: "445000" },
        },
        top_comparables: [
          {
            address: "125 Main St, Dallas, TX",
            source_url: "https://example.com/sale-1",
            sold_price: "438000",
            sold_date: "2026-04-10",
            distance_miles: "0.4",
          },
        ],
      },
    },
    rental_comps: {
      provider: "demo",
      retrieved_at: "2026-08-08T14:03:00Z",
      metadata: {
        provider: "demo",
        domain: "rental_comps",
        provider_latency_ms: 48,
        cache_status: "hit",
      },
      confidence: { value: "0.80" },
      data: {
        summary: {
          comparable_count: 2,
          median_monthly_rent: "3250",
          estimated_rent_range: { low: "3150", high: "3350" },
        },
        best_comparables: [
          {
            address: "210 Oak St, Dallas, TX",
            source_url: "https://example.com/rent-1",
            rental_status: "active",
            monthly_rent: "3300",
            distance_miles: "0.6",
          },
        ],
      },
    },
  },
  agent_research: {
    overall_data_confidence: "0.75",
    consolidated_findings: [
      {
        finding_id: "risk-1",
        category: "risk",
        title: "Thin pricing margin",
        finding: "The asking price sits above the strongest deterministic support.",
        significance: "Limited downside protection at current pricing.",
        severity: "high",
        confidence: "0.8",
        evidence: [
          {
            source_id: "underwriting.maximum_offer",
            source_type: "underwriting",
            field_path: "maximum_offer.binding_maximum_price",
          },
        ],
        is_inference: true,
      },
    ],
    missing_information: ["Roof age remains unverified."],
    due_diligence_questions: ["Confirm insurance quote with a local carrier."],
    evidence_index: [
      {
        source_id: "county_records",
        source_type: "research_citation",
        citation_id: "county-record-1",
        supporting_excerpt: "Annual property tax record from county system.",
      },
    ],
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
    investment_thesis: "Stabilized rental with moderate leverage and workable cash flow below ask.",
    strongest_upside: "Positive cash flow at the right basis.",
    strongest_downside: "Thin margin at current pricing.",
    reasons_to_proceed: [
      {
        title: "Stable rent support",
        explanation: "Rental comps cluster around the underwritten rent range.",
        importance: "high",
      },
    ],
    reasons_not_to_proceed: [
      {
        title: "Price support gap",
        explanation: "The current ask exceeds the strongest deterministic threshold.",
        importance: "decisive",
      },
    ],
    material_risks: [
      {
        category: "pricing",
        title: "Asking price above supported range",
        explanation: "The listing price exceeds the binding maximum supported by underwriting.",
        severity: "high",
        blocks_investment: false,
      },
    ],
    missing_information: [
      {
        item: "Roof age documentation",
        materiality: "important",
        importance: "medium",
        reason_needed: "Capex exposure remains uncertain.",
        decision_impact: "Unexpected near-term replacement cost could reduce returns.",
        blocks_recommendation: false,
      },
    ],
    what_must_be_true: [
      {
        condition: "Seller accepts an offer within the supported range.",
        current_status: "not confirmed",
        threshold_or_requirement: "At or below $430,000",
        consequence_if_false: "The deal no longer clears the pricing support threshold.",
      },
    ],
    due_diligence_checklist: [
      {
        category: "insurance",
        action: "Get bindable insurance quotes.",
        reason: "Validate the annual insurance assumption before closing.",
        priority: "high",
        timing: "before_offer",
      },
    ],
    evidence_references: [
      {
        source_id: "underwriting.maximum_offer",
        source_type: "underwriting",
        field_path: "maximum_offer.binding_maximum_price",
        supporting_excerpt: "Binding maximum of $425,000 from deterministic underwriting thresholds.",
      },
    ],
  },
};
