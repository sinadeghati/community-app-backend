const API_BASE = "/api";

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[2]) : null;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const csrf = getCookie("csrftoken");
  if (csrf && options.method && options.method !== "GET") {
    headers.set("X-CSRFToken", csrf);
  }
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: "include",
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export async function ensureCsrf() {
  await apiFetch<{ csrfToken: string }>("/admin/auth/csrf/");
}

export type DashboardStats = {
  users_total: number;
  users_suspended: number;
  users_pending_review: number;
  businesses_total: number;
  businesses_draft: number;
  businesses_hidden: number;
  businesses_pending: number;
  events_total: number;
  events_draft: number;
  events_pending: number;
  claims_pending: number;
  reports_open: number;
  reports_new: number;
  reports_in_review: number;
  media_pending_review: number;
  promotions_active: number;
  premium_active: number;
  featured_businesses: number;
  featured_events: number;
};

export type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type Claim = {
  id: number;
  listing: number;
  listing_title: string;
  requester: number;
  requester_username: string;
  requester_email: string;
  status: string;
  admin_note: string;
  created_at: string;
};
