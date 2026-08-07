const API_BASE = "/api";

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[2]) : null;
}

export class ApiError extends Error {
  fieldErrors: Record<string, string[]>;

  constructor(message: string, fieldErrors: Record<string, string[]> = {}) {
    super(message);
    this.name = "ApiError";
    this.fieldErrors = fieldErrors;
  }
}

function parseErrorBody(body: unknown, fallback: string): ApiError {
  if (!body || typeof body !== "object") {
    return new ApiError(fallback);
  }
  const record = body as Record<string, unknown>;
  if (typeof record.detail === "string") {
    return new ApiError(record.detail);
  }
  const fieldErrors: Record<string, string[]> = {};
  for (const [key, value] of Object.entries(record)) {
    if (Array.isArray(value) && value.every((item) => typeof item === "string")) {
      fieldErrors[key] = value;
    }
  }
  if (Object.keys(fieldErrors).length > 0) {
    return new ApiError("Please fix the highlighted fields.", fieldErrors);
  }
  return new ApiError(fallback);
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
    throw parseErrorBody(err, res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export async function ensureCsrf() {
  await apiFetch<{ csrfToken: string }>("/admin/auth/csrf/");
}

export function apiUpload<T>(
  path: string,
  formData: FormData,
  onProgress?: (percent: number) => void
): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}${path}`);
    xhr.withCredentials = true;
    const csrf = getCookie("csrftoken");
    if (csrf) {
      xhr.setRequestHeader("X-CSRFToken", csrf);
    }
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(xhr.responseText ? JSON.parse(xhr.responseText) : undefined);
        return;
      }
      try {
        const body = JSON.parse(xhr.responseText);
        reject(parseErrorBody(body, xhr.statusText));
      } catch {
        reject(new ApiError(xhr.statusText));
      }
    };
    xhr.onerror = () => reject(new ApiError("Upload failed."));
    xhr.send(formData);
  });
}

export function apiUploadPatch<T>(
  path: string,
  formData: FormData,
  onProgress?: (percent: number) => void
): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PATCH", `${API_BASE}${path}`);
    xhr.withCredentials = true;
    const csrf = getCookie("csrftoken");
    if (csrf) {
      xhr.setRequestHeader("X-CSRFToken", csrf);
    }
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
        return;
      }
      try {
        const body = JSON.parse(xhr.responseText);
        reject(parseErrorBody(body, xhr.statusText));
      } catch {
        reject(new ApiError(xhr.statusText));
      }
    };
    xhr.onerror = () => reject(new ApiError("Upload failed."));
    xhr.send(formData);
  });
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
