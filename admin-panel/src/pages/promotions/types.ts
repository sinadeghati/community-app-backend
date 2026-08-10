export type PromotionListRow = {
  id: number;
  title: string;
  image_url: string | null;
  placement: string;
  advertiser_name: string;
  status: string;
  display_priority: number;
  starts_at: string | null;
  ends_at: string | null;
  destination_type: string;
  destination_label: string;
  is_active: boolean;
  hero_approved: boolean;
  created_at: string;
  updated_at: string;
};

export type PromotionDetail = {
  id: number;
  advertiser_name: string;
  listing_id: number | null;
  listing_title: string | null;
  event_id: number | null;
  event_title: string | null;
  placement: string;
  title: string;
  subtitle: string;
  image_url: string | null;
  image_filename: string;
  video_url: string;
  cta_text: string;
  cta_link: string;
  target_route: string;
  target_id: string;
  channel: string;
  starts_at: string | null;
  ends_at: string | null;
  is_active: boolean;
  display_priority: number;
  sponsored_label: string;
  status: string;
  hero_approved: boolean;
  admin_note: string;
  destination_type: string;
  destination_label: string;
  schedule_state: string;
  analytics_available: boolean;
  created_at: string;
  updated_at: string;
};

export type PromotionFormValues = {
  advertiser_name: string;
  title: string;
  subtitle: string;
  placement: string;
  channel: string;
  starts_at: string;
  ends_at: string;
  display_priority: string;
  cta_text: string;
  destination_type: string;
  listing_id: string;
  event_id: string;
  cta_link: string;
  target_route: string;
  target_id: string;
  is_active: boolean;
  hero_approved: boolean;
  sponsored_label: string;
  admin_note: string;
};

export const PLACEMENT_OPTIONS = [
  { value: "home_hero", label: "Home hero" },
  { value: "explore_hero", label: "Explore hero" },
  { value: "business_featured", label: "Business featured" },
  { value: "event_featured", label: "Event featured" },
  { value: "sponsored_card", label: "Sponsored card" },
];

export const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "draft", label: "Draft" },
  { value: "scheduled", label: "Scheduled" },
  { value: "active", label: "Active" },
  { value: "expired", label: "Expired" },
  { value: "paused", label: "Paused" },
];

export const LIFECYCLE_OPTIONS = [
  { value: "", label: "All lifecycle" },
  { value: "active_now", label: "Active now" },
  { value: "scheduled", label: "Scheduled" },
  { value: "expired", label: "Expired" },
  { value: "draft", label: "Draft" },
  { value: "paused", label: "Paused" },
];

export const DESTINATION_OPTIONS = [
  { value: "none", label: "No action" },
  { value: "business", label: "Open business" },
  { value: "event", label: "Open event" },
  { value: "external_url", label: "External URL" },
  { value: "internal", label: "Internal route" },
];

export const ORDERING_OPTIONS = [
  { value: "display_priority", label: "Priority (low first)" },
  { value: "-display_priority", label: "Priority (high first)" },
  { value: "-created_at", label: "Created (newest)" },
  { value: "title", label: "Title (A–Z)" },
];

export const ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];
export const ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"];

export const HERO_ASPECT_NOTE =
  "Mobile hero uses full-width imagery from GET /api/hero-slides/. Exact pixel dimensions could not be verified because community-app-mobile is outside this repo. Use a wide landscape image (recommended 16:9 or wider).";

export function validateImageFile(file: File): string | null {
  const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  if (
    !ALLOWED_IMAGE_TYPES.includes(file.type) &&
    !ALLOWED_IMAGE_EXTENSIONS.includes(extension)
  ) {
    return "Unsupported format. Please upload PNG, JPEG, or WEBP.";
  }
  return null;
}

export function toDatetimeLocal(value: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function fromDatetimeLocal(value: string): string | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

export function formatDate(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export function statusBadgeClass(status: string): string {
  if (status === "active") return "badge success";
  if (status === "scheduled") return "badge accent";
  if (status === "expired" || status === "paused") return "badge warning";
  return "badge";
}

export function placementLabel(value: string): string {
  return PLACEMENT_OPTIONS.find((o) => o.value === value)?.label || value;
}

export function promotionToFormValues(promo: PromotionDetail): PromotionFormValues {
  return {
    advertiser_name: promo.advertiser_name,
    title: promo.title,
    subtitle: promo.subtitle || "",
    placement: promo.placement,
    channel: promo.channel || "",
    starts_at: toDatetimeLocal(promo.starts_at),
    ends_at: toDatetimeLocal(promo.ends_at),
    display_priority: String(promo.display_priority ?? 0),
    cta_text: promo.cta_text || "",
    destination_type: promo.destination_type || "none",
    listing_id: promo.listing_id ? String(promo.listing_id) : "",
    event_id: promo.event_id ? String(promo.event_id) : "",
    cta_link: promo.cta_link || "",
    target_route: promo.target_route || "",
    target_id: promo.target_id || "",
    is_active: promo.is_active,
    hero_approved: promo.hero_approved,
    sponsored_label: promo.sponsored_label || "",
    admin_note: promo.admin_note || "",
  };
}

export function formValuesToPayload(values: PromotionFormValues) {
  return {
    advertiser_name: values.advertiser_name.trim(),
    title: values.title.trim(),
    subtitle: values.subtitle.trim(),
    placement: values.placement,
    channel: values.channel.trim(),
    starts_at: fromDatetimeLocal(values.starts_at),
    ends_at: fromDatetimeLocal(values.ends_at),
    display_priority: Number(values.display_priority) || 0,
    cta_text: values.cta_text.trim(),
    destination_type: values.destination_type,
    listing_id: values.listing_id ? Number(values.listing_id) : null,
    event_id: values.event_id ? Number(values.event_id) : null,
    cta_link: values.cta_link.trim(),
    target_route: values.target_route.trim(),
    target_id: values.target_id.trim(),
    is_active: values.is_active,
    hero_approved: values.hero_approved,
    sponsored_label: values.sponsored_label.trim(),
    admin_note: values.admin_note.trim(),
  };
}

export function buildPromotionListEndpoint(params: {
  page: number;
  search: string;
  status: string;
  placement: string;
  advertiser: string;
  lifecycle: string;
  ordering: string;
}) {
  const query = new URLSearchParams();
  query.set("page", String(params.page));
  query.set("page_size", "20");
  if (params.search) query.set("search", params.search);
  if (params.status) query.set("status", params.status);
  if (params.placement) query.set("placement", params.placement);
  if (params.advertiser) query.set("advertiser", params.advertiser);
  if (params.lifecycle) query.set("lifecycle", params.lifecycle);
  if (params.ordering) query.set("ordering", params.ordering);
  return `/admin/promotions/?${query.toString()}`;
}
