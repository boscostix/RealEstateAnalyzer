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
  property_snapshot?: Record<string, unknown> | null;
  assumptions?: Record<string, unknown> | null;
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
