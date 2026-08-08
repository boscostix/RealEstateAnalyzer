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
  underwriting?: Record<string, unknown> | null;
  research?: Record<string, unknown> | null;
  agent_research?: Record<string, unknown> | null;
  investment_committee?: Record<string, unknown> | null;
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
