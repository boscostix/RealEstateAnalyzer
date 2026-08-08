import { fetchJson } from "./client";
import type { PropertyCreateResponse, PropertyResponse } from "./types";

export function getProperty(propertyId: string): Promise<PropertyResponse> {
  return fetchJson<PropertyResponse>(`/api/v1/properties/${propertyId}`);
}

export function listPropertyAnalyses(propertyId: string) {
  return fetchJson(`/api/v1/properties/${propertyId}/analyses`);
}

export function createProperty(payload: Record<string, unknown>): Promise<PropertyCreateResponse> {
  return fetchJson<PropertyCreateResponse>("/api/v1/properties", {
    method: "POST",
    body: payload,
  });
}
