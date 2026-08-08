import { fetchJson } from "./client";
import type {
  AnalysisListResponse,
  PropertyCreateRequest,
  PropertyCreateResponse,
  PropertyResponse,
  PropertyUpdateRequest,
  PropertyVerificationRequest,
  PropertyVerificationResponse,
} from "./types";

export function getProperty(propertyId: string): Promise<PropertyResponse> {
  return fetchJson<PropertyResponse>(`/api/v1/properties/${propertyId}`);
}

export function listPropertyAnalyses(propertyId: string): Promise<AnalysisListResponse> {
  return fetchJson<AnalysisListResponse>(`/api/v1/properties/${propertyId}/analyses`);
}

export function createProperty(payload: PropertyCreateRequest): Promise<PropertyCreateResponse> {
  return fetchJson<PropertyCreateResponse>("/api/v1/properties", {
    method: "POST",
    body: payload,
  });
}

export function updateProperty(
  propertyId: string,
  payload: PropertyUpdateRequest,
): Promise<PropertyResponse> {
  return fetchJson<PropertyResponse>(`/api/v1/properties/${propertyId}`, {
    method: "PATCH",
    body: payload,
  });
}

export function verifyProperty(
  payload: PropertyVerificationRequest,
): Promise<PropertyVerificationResponse> {
  return fetchJson<PropertyVerificationResponse>("/api/v1/properties/verify", {
    method: "POST",
    body: payload,
  });
}
