import type { NominatimResult } from "./nominatimAddress";

const API_BASE = "/api";

export async function fetchAddressSuggestions(
  query: string,
  signal?: AbortSignal
): Promise<NominatimResult[]> {
  const q = query.trim();
  if (q.length < 3) {
    return [];
  }

  const params = new URLSearchParams({
    q,
    format: "json",
    addressdetails: "1",
    limit: "8",
    countrycodes: "us",
  });

  const response = await fetch(`${API_BASE}/geocode/suggest/?${params.toString()}`, {
    method: "GET",
    credentials: "include",
    headers: { Accept: "application/json" },
    signal,
  });

  if (response.status === 429) {
    throw new Error("Too many address searches. Please wait a moment and try again.");
  }
  if (response.status === 502) {
    throw new Error("Address search is temporarily unavailable.");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail =
      body && typeof body === "object" && typeof body.detail === "string"
        ? body.detail
        : "Address search failed.";
    throw new Error(detail);
  }

  const payload = (await response.json()) as NominatimResult[] | { detail?: string };
  if (!Array.isArray(payload)) {
    return [];
  }
  return payload;
}
