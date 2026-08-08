import { fetchJson } from "./client";
import type {
  AnalysisCreateResponse,
  AnalysisDetailResponse,
  AnalysisListResponse,
} from "./types";

export function getAnalysis(analysisId: string): Promise<AnalysisDetailResponse> {
  return fetchJson<AnalysisDetailResponse>(`/api/v1/analyses/${analysisId}`);
}

export function createAnalysis(
  propertyId: string,
  payload: Record<string, unknown>,
): Promise<AnalysisCreateResponse> {
  return fetchJson<AnalysisCreateResponse>(`/api/v1/properties/${propertyId}/analyses`, {
    method: "POST",
    body: payload,
  });
}

export function listAnalyses(propertyId: string): Promise<AnalysisListResponse> {
  return fetchJson<AnalysisListResponse>(`/api/v1/properties/${propertyId}/analyses`);
}

export function rerunAnalysis(
  analysisId: string,
  payload: Record<string, unknown>,
): Promise<AnalysisCreateResponse> {
  return fetchJson<AnalysisCreateResponse>(`/api/v1/analyses/${analysisId}/rerun`, {
    method: "POST",
    body: payload,
  });
}
