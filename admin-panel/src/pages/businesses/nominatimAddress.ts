export type NominatimAddress = {
  house_number?: string;
  road?: string;
  pedestrian?: string;
  neighbourhood?: string;
  suburb?: string;
  city?: string;
  town?: string;
  village?: string;
  municipality?: string;
  county?: string;
  state?: string;
  postcode?: string;
  "ISO3166-2-lvl4"?: string;
};

export type NominatimResult = {
  place_id: number | string;
  display_name?: string;
  lat?: string;
  lon?: string;
  address?: NominatimAddress;
};

export type ParsedAddressSelection = {
  address: string;
  city: string;
  state: string;
  latitude: string;
  longitude: string;
  label: string;
};

const US_STATE_ABBREV: Record<string, string> = {
  alabama: "AL",
  alaska: "AK",
  arizona: "AZ",
  arkansas: "AR",
  california: "CA",
  colorado: "CO",
  connecticut: "CT",
  delaware: "DE",
  florida: "FL",
  georgia: "GA",
  hawaii: "HI",
  idaho: "ID",
  illinois: "IL",
  indiana: "IN",
  iowa: "IA",
  kansas: "KS",
  kentucky: "KY",
  louisiana: "LA",
  maine: "ME",
  maryland: "MD",
  massachusetts: "MA",
  michigan: "MI",
  minnesota: "MN",
  mississippi: "MS",
  missouri: "MO",
  montana: "MT",
  nebraska: "NE",
  nevada: "NV",
  "new hampshire": "NH",
  "new jersey": "NJ",
  "new mexico": "NM",
  "new york": "NY",
  "north carolina": "NC",
  "north dakota": "ND",
  ohio: "OH",
  oklahoma: "OK",
  oregon: "OR",
  pennsylvania: "PA",
  "rhode island": "RI",
  "south carolina": "SC",
  "south dakota": "SD",
  tennessee: "TN",
  texas: "TX",
  utah: "UT",
  vermont: "VT",
  virginia: "VA",
  washington: "WA",
  "west virginia": "WV",
  wisconsin: "WI",
  wyoming: "WY",
  "district of columbia": "DC",
};

export function parseStateCode(raw: string): string {
  const value = String(raw || "").trim();
  if (!value) return "";

  const isoMatch = value.match(/^US-([A-Z]{2})$/i);
  if (isoMatch) return isoMatch[1].toUpperCase();

  if (value.length === 2) return value.toUpperCase();

  return US_STATE_ABBREV[value.toLowerCase()] || value;
}

export function buildStreetAddressWithZip(street: string, zip: string): string {
  const streetLine = street.trim();
  const zipCode = zip.trim();
  if (!streetLine) return zipCode;
  if (!zipCode) return streetLine;
  if (streetLine.includes(zipCode)) return streetLine;
  return `${streetLine}, ${zipCode}`;
}

export function formatSuggestionLabel(parsed: {
  address: string;
  city: string;
  state: string;
  zip: string;
}): string {
  const { address, city, state, zip } = parsed;
  if (address && city && state && zip) {
    return `${address}, ${city}, ${state} ${zip}`;
  }
  if (address && city && state) {
    return `${address}, ${city}, ${state}`;
  }
  return [address, city, state, zip].filter(Boolean).join(", ");
}

export function parseNominatimResult(result: NominatimResult): ParsedAddressSelection | null {
  const address = result.address;
  if (!address) return null;

  const streetCore = [address.house_number, address.road || address.pedestrian]
    .filter(Boolean)
    .join(" ")
    .trim();

  const city =
    address.city ||
    address.town ||
    address.village ||
    address.suburb ||
    address.neighbourhood ||
    address.municipality ||
    address.county ||
    "";

  const state = parseStateCode(address["ISO3166-2-lvl4"] || address.state || "");
  const zip = String(address.postcode || "").trim();

  const addressLine = buildStreetAddressWithZip(streetCore, zip);

  const latitude = Number(result.lat);
  const longitude = Number(result.lon);

  if (!addressLine && !city) {
    return null;
  }

  const label = formatSuggestionLabel({
    address: addressLine,
    city,
    state,
    zip,
  });

  return {
    address: addressLine,
    city,
    state,
    latitude: Number.isFinite(latitude) ? String(latitude) : "",
    longitude: Number.isFinite(longitude) ? String(longitude) : "",
    label: label || String(result.display_name || "").trim(),
  };
}

export function nominatimResultsToSuggestions(
  results: NominatimResult[]
): { id: string; label: string; selection: ParsedAddressSelection }[] {
  const items: { id: string; label: string; selection: ParsedAddressSelection }[] = [];
  const seen = new Set<string>();

  for (const result of results) {
    const selection = parseNominatimResult(result);
    if (!selection) continue;
    const key = `${selection.address}|${selection.city}|${selection.state}|${selection.latitude}`;
    if (seen.has(key)) continue;
    seen.add(key);
    items.push({
      id: String(result.place_id),
      label: selection.label,
      selection,
    });
  }
  return items;
}
