export type UserListRow = {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  display_name: string;
  is_active: boolean;
  is_staff: boolean;
  last_login: string | null;
  date_joined: string;
  email_verified: boolean;
  role: string;
  account_status: string;
  admin_note: string;
  businesses_count: number | null;
};

export type UserDetail = UserListRow & {
  is_superuser: boolean;
  suspended_at: string | null;
  suspended_by_id: number | null;
  suspended_by_username: string | null;
  events_count: number;
  claims_count: number;
  reports_count: number;
};

export type UserBusinessSummary = {
  id: number;
  title: string;
  city: string;
  status: string;
  is_featured: boolean;
};

export type UserEventSummary = {
  id: number;
  title: string;
  city: string;
  status: string;
  starts_at: string;
  is_featured: boolean;
};

export type UserClaimSummary = {
  id: number;
  listing: number;
  listing_title: string;
  status: string;
  created_at: string;
};

export type UserReportSummary = {
  id: number;
  reported_object_type: string;
  reported_object_id: number;
  reason: string;
  status: string;
  created_at: string;
};

export const ACCOUNT_STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "active", label: "Active" },
  { value: "suspended", label: "Suspended" },
  { value: "pending_review", label: "Pending review" },
];

export const EMAIL_VERIFIED_OPTIONS = [
  { value: "", label: "All verification" },
  { value: "true", label: "Verified" },
  { value: "false", label: "Unverified" },
];

export function buildUsersListEndpoint(params: {
  page: number;
  search: string;
  accountStatus: string;
  emailVerified: string;
}): string {
  const qs = new URLSearchParams();
  qs.set("page_size", "25");
  qs.set("page", String(params.page));
  if (params.search.trim()) qs.set("search", params.search.trim());
  if (params.accountStatus) qs.set("account_status", params.accountStatus);
  if (params.emailVerified) qs.set("email_verified", params.emailVerified);
  return `/admin/users/?${qs.toString()}`;
}

export function formatDate(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export function statusBadgeClass(status: string): string {
  if (status === "suspended" || status === "hidden") return "badge danger";
  if (status === "active" || status === "published") return "badge success";
  if (status === "pending_review" || status === "draft") return "badge warning";
  return "badge";
}
