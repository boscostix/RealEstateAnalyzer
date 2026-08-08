import { fetchJson } from "./client";
import type { ExtractListingRequest, ExtractListingResponse } from "./types";

export function extractListing(payload: ExtractListingRequest): Promise<ExtractListingResponse> {
  return fetchJson<ExtractListingResponse>("/api/v1/listings/extract", {
    method: "POST",
    body: payload,
  });
}
