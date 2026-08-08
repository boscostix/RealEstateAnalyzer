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

export type NormalizedProperty = Record<string, unknown> & {
  source_url?: string;
  provider?: string;
};

export type ExtractListingResponse = {
  success: boolean;
  provider?: string | null;
  source_url?: string | null;
  property?: NormalizedProperty | null;
  metadata?: ExtractionMetadata | null;
  error?: StructuredApiError | null;
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
  property?: Record<string, unknown> | null;
  verified_property?: Record<string, unknown> | null;
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
