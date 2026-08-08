export type StructuredApiError = {
  code: string;
  message: string;
  field?: string | null;
  retryable?: boolean;
};

export type ApiErrorResponse = {
  success: false;
  error: StructuredApiError;
};

export type ExtractListingRequest = {
  url: string;
};

export type ExtractionMetadata = {
  extraction_method: string;
  retrieved_at: string;
  fields_found: number;
  fields_missing: string[];
  warnings: string[];
};

export type NumericLike = number | string;

export type PropertyAddress = {
  street?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  full_address?: string | null;
};

export type NormalizedProperty = Record<string, unknown> & {
  source_url?: string;
  provider?: string;
  address?: PropertyAddress | null;
  asking_price?: NumericLike | null;
  bedrooms?: NumericLike | null;
  bathrooms?: NumericLike | null;
  square_feet?: number | null;
  lot_square_feet?: number | null;
  year_built?: number | null;
  annual_property_tax?: NumericLike | null;
  annual_hoa?: NumericLike | null;
  property_type?: string | null;
};

export type ExtractedField = {
  value: string | number | boolean | null;
  source: string;
  confidence: number;
  raw_value?: string | null;
};

export type ExtractListingResponse = {
  success: boolean;
  provider?: string | null;
  source_url?: string | null;
  property?: NormalizedProperty | null;
  metadata?: ExtractionMetadata | null;
  field_provenance?: Record<string, ExtractedField> | null;
  error?: StructuredApiError | null;
};

export type PropertyExtractionPayload = {
  provider: string;
  source_url: string;
  property: NormalizedProperty;
  metadata: ExtractionMetadata;
  field_provenance: Record<string, ExtractedField>;
};

export type VerificationStatus =
  | "verified"
  | "unverified"
  | "corrected"
  | "estimated"
  | "missing"
  | "conflicting";

export type VerifiedFieldSnapshot = {
  extracted_value?: string | number | null;
  final_value?: string | number | null;
  status: VerificationStatus;
  source?: string | null;
  confidence?: string | number | null;
  user_modified?: boolean;
};

export type VerifiedPropertySnapshot = {
  source_url: string;
  provider: string;
  full_address: VerifiedFieldSnapshot;
  asking_price: VerifiedFieldSnapshot;
  bedrooms: VerifiedFieldSnapshot;
  bathrooms: VerifiedFieldSnapshot;
  square_feet: VerifiedFieldSnapshot;
  lot_square_feet: VerifiedFieldSnapshot;
  year_built: VerifiedFieldSnapshot;
  annual_property_tax: VerifiedFieldSnapshot;
  annual_hoa: VerifiedFieldSnapshot;
  property_type: VerifiedFieldSnapshot;
};

export type PropertyVerificationRequest = {
  extraction: PropertyExtractionPayload;
  corrections: Record<string, string | number>;
  confirmed_fields: string[];
};

export type VerificationSummary = {
  verified_fields: string[];
  corrected_fields: string[];
  unverified_fields: string[];
  estimated_fields: string[];
  missing_fields: string[];
  conflicting_fields: string[];
};

export type PropertyVerificationResponse = {
  success: boolean;
  property?: VerifiedPropertySnapshot | null;
  verification_summary?: VerificationSummary | null;
};

export type AnalysisSummary = {
  id: string;
  property_id: string;
  version: number;
  status: string;
  current_stage?: string | null;
  parent_analysis_id?: string | null;
  created_at: string;
  completed_at?: string | null;
  failed_at?: string | null;
};

export type PropertySummary = {
  id: string;
  source_url: string;
  provider: string;
  full_address?: string | null;
  created_at: string;
  updated_at: string;
  current_version: number;
};

export type PropertyDetail = PropertySummary & {
  property?: NormalizedProperty | null;
  verified_property?: VerifiedPropertySnapshot | null;
  analysis_count: number;
  latest_analysis?: AnalysisSummary | null;
};

export type PropertyResponse = {
  success: boolean;
  property: PropertyDetail;
};

export type PropertyCreateResponse = {
  success: boolean;
  property: PropertySummary;
};

export type PropertyCreateRequest = {
  property?: NormalizedProperty | null;
  verified_property?: VerifiedPropertySnapshot | null;
};

export type PropertyUpdateRequest = {
  property?: NormalizedProperty | null;
  verified_property?: VerifiedPropertySnapshot | null;
  current_version?: number | null;
};

export type AnalysisPreset = "conservative" | "standard" | "aggressive" | "custom";
export type FinancingType = "conventional" | "cash";

export type AcquisitionAssumptions = {
  closing_costs?: NumericLike | null;
  closing_cost_percent?: NumericLike | null;
  lender_fees: NumericLike;
  repairs: NumericLike;
  initial_reserves: NumericLike;
  other_acquisition_costs: NumericLike;
};

export type FinancingAssumptions = {
  type: FinancingType;
  down_payment_amount?: NumericLike | null;
  down_payment_percent?: NumericLike | null;
  interest_rate_percent?: NumericLike | null;
  loan_term_years?: number | null;
  loan_amount?: NumericLike | null;
  points: NumericLike;
  additional_lender_fees: NumericLike;
  monthly_mortgage_insurance: NumericLike;
};

export type IncomeAssumptions = {
  monthly_rent: NumericLike;
  other_monthly_income: NumericLike;
  vacancy_percent: NumericLike;
};

export type ExpenseAssumptions = {
  annual_property_taxes?: NumericLike | null;
  annual_insurance: NumericLike;
  annual_hoa?: NumericLike | null;
  management_percent: NumericLike;
  maintenance_percent?: NumericLike | null;
  maintenance_annual?: NumericLike | null;
  capex_percent?: NumericLike | null;
  capex_annual?: NumericLike | null;
  leasing_fee_percent: NumericLike;
  tenant_turnover_frequency_years: NumericLike;
  turnover_cost: NumericLike;
  owner_paid_utilities_monthly: NumericLike;
  landscaping_monthly: NumericLike;
  pest_control_monthly: NumericLike;
  other_monthly_expenses: NumericLike;
  other_annual_expenses: NumericLike;
};

export type ProjectionAssumptions = {
  holding_period_years: number;
  annual_rent_growth_percent: NumericLike;
  annual_expense_growth_percent: NumericLike;
  annual_appreciation_percent: NumericLike;
  selling_cost_percent: NumericLike;
};

export type TargetAssumptions = {
  monthly_cash_flow?: NumericLike | null;
  cap_rate_percent?: NumericLike | null;
  cash_on_cash_percent?: NumericLike | null;
  dscr?: NumericLike | null;
};

export type AnalysisAssumptions = {
  purchase_price: NumericLike;
  preset: AnalysisPreset;
  financing: FinancingAssumptions;
  acquisition: AcquisitionAssumptions;
  income: IncomeAssumptions;
  expenses: ExpenseAssumptions;
  projections: ProjectionAssumptions;
  targets: TargetAssumptions;
};

export type AnalysisCreateRequest = {
  assumptions: AnalysisAssumptions;
  decision_context?: Record<string, unknown> | null;
};

export type CommitteeReason = {
  title: string;
  explanation: string;
  importance: string;
  affected_metrics?: string[];
};

export type OfferRangeBasis = {
  value: NumericLike;
  source_metric: string;
  source_path: string;
  description: string;
};

export type CommitteeRisk = {
  category: string;
  title: string;
  explanation: string;
  severity: string;
  probability?: string | null;
  financial_impact?: string | null;
  mitigation?: string | null;
  blocks_investment: boolean;
};

export type RequiredCondition = {
  condition: string;
  current_status: string;
  threshold_or_requirement: string;
  consequence_if_false: string;
};

export type DueDiligenceItem = {
  category: string;
  action: string;
  reason: string;
  priority: string;
  timing: string;
  responsible_party?: string | null;
};

export type EvidenceReference = {
  source_id: string;
  source_type: string;
  citation_id?: string | null;
  field_path?: string | null;
  supporting_excerpt?: string | null;
  retrieved_at?: string | null;
};

export type CommitteeMissingItem = {
  item: string;
  materiality: string;
  importance: string;
  reason_needed: string;
  decision_impact: string;
  recommended_source?: string | null;
  blocks_recommendation: boolean;
};

export type InvestmentCommitteeOutput = {
  recommendation: string;
  recommendation_summary: string;
  recommendation_confidence: NumericLike;
  recommendation_confidence_reasons?: string[];
  asking_price: NumericLike;
  supported_offer_low?: NumericLike | null;
  supported_offer_high?: NumericLike | null;
  recommended_offer_basis?: OfferRangeBasis[];
  investment_thesis: string;
  strongest_upside: string;
  strongest_downside: string;
  reasons_to_proceed?: CommitteeReason[];
  reasons_not_to_proceed?: CommitteeReason[];
  material_risks?: CommitteeRisk[];
  missing_information?: CommitteeMissingItem[];
  what_must_be_true?: RequiredCondition[];
  due_diligence_checklist?: DueDiligenceItem[];
  evidence_references?: EvidenceReference[];
  warnings?: string[];
};

export type ValueRange = {
  low?: NumericLike | null;
  high?: NumericLike | null;
};

export type SalesComparableRecord = {
  address: string;
  source_url?: string | null;
  sold_date?: string | null;
  sold_price?: NumericLike | null;
  list_price?: NumericLike | null;
  square_feet?: number | null;
  bedrooms?: NumericLike | null;
  bathrooms?: NumericLike | null;
  year_built?: number | null;
  distance_miles?: NumericLike | null;
  price_per_square_foot?: NumericLike | null;
  adjusted_price_per_square_foot?: NumericLike | null;
  similarity_score?: NumericLike | null;
};

export type RentalComparableRecord = {
  address: string;
  source_url?: string | null;
  rental_status: string;
  listed_date?: string | null;
  leased_date?: string | null;
  monthly_rent?: NumericLike | null;
  square_feet?: number | null;
  bedrooms?: NumericLike | null;
  bathrooms?: NumericLike | null;
  year_built?: number | null;
  distance_miles?: NumericLike | null;
  rent_per_square_foot?: NumericLike | null;
  occupancy_indicator?: NumericLike | null;
  similarity_score?: NumericLike | null;
};

export type SalesCompsSummary = {
  comparable_count: number;
  average_sold_price?: NumericLike | null;
  median_sold_price?: NumericLike | null;
  average_price_per_square_foot?: NumericLike | null;
  median_adjusted_price_per_square_foot?: NumericLike | null;
  sold_price_range?: ValueRange;
};

export type RentalCompsSummary = {
  comparable_count: number;
  average_monthly_rent?: NumericLike | null;
  median_monthly_rent?: NumericLike | null;
  average_rent_per_square_foot?: NumericLike | null;
  estimated_rent_range?: ValueRange;
  active_count?: number;
  leased_count?: number;
  average_occupancy_indicator?: NumericLike | null;
};

export type SalesCompsData = {
  top_comparables?: SalesComparableRecord[];
  summary: SalesCompsSummary;
};

export type RentalCompsData = {
  best_comparables?: RentalComparableRecord[];
  summary: RentalCompsSummary;
};

export type ResearchCitation = {
  source_name: string;
  source_url: string;
  source_type: string;
  retrieved_at?: string | null;
  note?: string | null;
};

export type ResearchSource = {
  name: string;
  type: string;
  url: string;
  retrieved_at?: string | null;
};

export type ResearchConfidence = {
  value: NumericLike;
  reason?: string | null;
};

export type ResearchMetadata = {
  provider: string;
  domain: string;
  retrieved_at?: string;
  provider_latency_ms: number;
  cache_status: string;
  source_url?: string | null;
  source_name?: string | null;
  warnings?: string[];
};

export type ResearchResult<T> = {
  provider: string;
  retrieved_at: string;
  metadata: ResearchMetadata;
  confidence: ResearchConfidence;
  citations?: ResearchCitation[];
  sources?: ResearchSource[];
  data: T;
};

export type ResearchPackageMetadata = {
  retrieved_at?: string;
  total_duration_ms: number;
  completed_domains?: string[];
  failed_domains?: string[];
  citations?: ResearchCitation[];
};

export type ResearchPackage = {
  public_records?: ResearchResult<Record<string, unknown>> | null;
  sales_comps?: ResearchResult<SalesCompsData> | null;
  rental_comps?: ResearchResult<RentalCompsData> | null;
  neighborhood?: ResearchResult<Record<string, unknown>> | null;
  metadata: ResearchPackageMetadata;
  warnings?: Array<{
    code: string;
    domain: string;
    message: string;
    retryable?: boolean;
  }>;
};

export type AgentFinding = {
  finding_id: string;
  category: string;
  title: string;
  finding: string;
  significance: string;
  severity: string;
  confidence: NumericLike;
  evidence?: EvidenceReference[];
  affected_fields?: string[];
  missing_information?: string[];
  recommended_next_actions?: string[];
  is_inference: boolean;
};

export type ResearchConflict = {
  conflict_id: string;
  field_or_topic: string;
  materiality: string;
  resolution_status: string;
  resolution_reason?: string | null;
  requires_user_review: boolean;
};

export type UnifiedAgentResearchPackage = {
  consolidated_findings?: AgentFinding[];
  conflicts?: ResearchConflict[];
  missing_information?: string[];
  due_diligence_questions?: string[];
  evidence_index?: EvidenceReference[];
  overall_data_confidence: NumericLike;
  warnings?: string[];
  execution_metadata?: Record<string, unknown>;
};

export type StressTestResult = {
  identifier: string;
  description: string;
  changed_assumptions: Record<string, NumericLike | string>;
  change_in_monthly_cash_flow: NumericLike;
  change_in_annual_cash_flow: NumericLike;
  change_in_cash_on_cash_return?: NumericLike | null;
  cash_flow_remains_positive: boolean;
  additional_cash_required: NumericLike;
  warnings?: string[];
};

export type ScenarioResult = {
  name: string;
  adjustments?: Record<string, NumericLike>;
  warnings?: string[];
  metrics?: Record<string, NumericLike | null>;
};

export type MaximumOfferResult = {
  break_even_cash_flow_price?: NumericLike | null;
  target_monthly_cash_flow_price?: NumericLike | null;
  target_cap_rate_price?: NumericLike | null;
  target_cash_on_cash_price?: NumericLike | null;
  target_dscr_price?: NumericLike | null;
  binding_maximum_price?: NumericLike | null;
  asking_price_gap?: NumericLike | null;
  warnings?: string[];
};

export type UnderwritingAnalysis = {
  acquisition?: Record<string, unknown>;
  metrics?: Record<string, NumericLike | null>;
  maximum_offer?: MaximumOfferResult | null;
  scenarios?: ScenarioResult[];
  stress_tests?: StressTestResult[];
  warnings?: string[];
};

export type AnalysisDetail = {
  id: string;
  property_id: string;
  version: number;
  status: string;
  current_stage?: string | null;
  parent_analysis_id?: string | null;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  failed_at?: string | null;
  failure_stage?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  property_snapshot?: VerifiedPropertySnapshot | null;
  assumptions?: AnalysisAssumptions | null;
  underwriting?: UnderwritingAnalysis | null;
  research?: ResearchPackage | null;
  agent_research?: UnifiedAgentResearchPackage | null;
  investment_committee?: InvestmentCommitteeOutput | null;
  execution?: Record<string, unknown> | null;
};

export type AnalysisDetailResponse = {
  success: boolean;
  analysis: AnalysisDetail;
};

export type AnalysisCreateResponse = {
  success: boolean;
  analysis: AnalysisSummary;
};

export type AnalysisListResponse = {
  success: boolean;
  analyses: AnalysisSummary[];
};
