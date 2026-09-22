import { apiFetch } from "../../api";

export type GeocodeResult = {
  latitude: number;
  longitude: number;
};

export async function geocodeBusinessAddress(params: {
  address: string;
  city: string;
  state: string;
}): Promise<GeocodeResult> {
  return apiFetch<GeocodeResult>("/admin/businesses/geocode/", {
    method: "POST",
    body: JSON.stringify({
      address: params.address.trim(),
      city: params.city.trim(),
      state: params.state.trim(),
    }),
  });
}
