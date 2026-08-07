export type EventListRow = {
  id: number;
  title: string;
  cover_image_url: string | null;
  listing_id: number | null;
  listing_title: string | null;
  owner_id: number;
  owner_username: string;
  organizer: string;
  organizer_name: string;
  category: string;
  city: string;
  starts_at: string;
  ends_at: string | null;
  status: string;
  is_featured: boolean;
  created_at: string;
  updated_at: string;
};

export type EventGalleryImage = {
  id: string;
  storage_path?: string;
  filename?: string;
  uploaded_at?: string;
  image_url?: string | null;
};

export type EventDetail = {
  id: number;
  title: string;
  description: string;
  category: string;
  starts_at: string;
  ends_at: string | null;
  location: string;
  address: string;
  city: string;
  state: string;
  zip_code: string;
  country: string;
  latitude: number | null;
  longitude: number | null;
  organizer: string;
  ticket_url: string;
  ticket_provider_label: string;
  listing_id: number | null;
  listing_title: string | null;
  owner_id: number;
  owner_username: string;
  status: string;
  is_featured: boolean;
  is_sponsored: boolean;
  display_priority: number;
  cover_image_url: string | null;
  cover_media_status: string;
  cover_moderation_reason: string;
  admin_note: string;
  admin_note_text: string;
  tags: string[];
  phone: string;
  website: string;
  instagram: string;
  visibility: "public" | "draft" | "hidden";
  gallery: EventGalleryImage[];
  media_count: number;
  promotions_count: number;
  reports_count: number;
  claims_count: number;
  created_at: string;
  updated_at: string;
};

export type EventFormValues = {
  title: string;
  description: string;
  category: string;
  starts_at: string;
  ends_at: string;
  location: string;
  address: string;
  city: string;
  state: string;
  zip_code: string;
  country: string;
  organizer: string;
  ticket_url: string;
  phone: string;
  website: string;
  instagram: string;
  tags: string;
  listing_id: string;
  owner_id: string;
  status: string;
  is_featured: boolean;
  visibility: string;
  admin_note_text: string;
};

export const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "draft", label: "Draft" },
  { value: "published", label: "Published" },
  { value: "hidden", label: "Hidden" },
];

export const VISIBILITY_OPTIONS = [
  { value: "draft", label: "Draft" },
  { value: "public", label: "Public" },
  { value: "hidden", label: "Hidden" },
];

export const ORDERING_OPTIONS = [
  { value: "-starts_at", label: "Start date (newest)" },
  { value: "starts_at", label: "Start date (oldest)" },
  { value: "-created_at", label: "Created (newest)" },
  { value: "title", label: "Title (A–Z)" },
];

export const ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];
export const ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"];

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

export function formatFileSize(bytes?: number | null): string {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
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

export function eventToFormValues(event: EventDetail): EventFormValues {
  return {
    title: event.title,
    description: event.description || "",
    category: event.category || "",
    starts_at: toDatetimeLocal(event.starts_at),
    ends_at: toDatetimeLocal(event.ends_at),
    location: event.location || "",
    address: event.address || "",
    city: event.city || "",
    state: event.state || "",
    zip_code: event.zip_code || "",
    country: event.country || "",
    organizer: event.organizer || "",
    ticket_url: event.ticket_url || "",
    phone: event.phone || "",
    website: event.website || "",
    instagram: event.instagram || "",
    tags: (event.tags || []).join(", "),
    listing_id: event.listing_id ? String(event.listing_id) : "",
    owner_id: String(event.owner_id),
    status: event.status,
    is_featured: event.is_featured,
    visibility: event.visibility,
    admin_note_text: event.admin_note_text || "",
  };
}

export function formValuesToPayload(values: EventFormValues) {
  return {
    title: values.title.trim(),
    description: values.description.trim(),
    category: values.category.trim(),
    starts_at: fromDatetimeLocal(values.starts_at),
    ends_at: fromDatetimeLocal(values.ends_at),
    location: values.location.trim(),
    address: values.address.trim(),
    city: values.city.trim(),
    state: values.state.trim(),
    zip_code: values.zip_code.trim(),
    country: values.country.trim(),
    organizer: values.organizer.trim(),
    ticket_url: values.ticket_url.trim(),
    phone: values.phone.trim(),
    website: values.website.trim(),
    instagram: values.instagram.trim(),
    tags: values.tags
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean),
    listing_id: values.listing_id ? Number(values.listing_id) : null,
    status: values.status,
    is_featured: values.is_featured,
    visibility: values.visibility,
    admin_note_text: values.admin_note_text.trim(),
  };
}

export function buildEventListEndpoint(params: {
  page: number;
  search: string;
  status: string;
  category: string;
  featured: string;
  startsAfter: string;
  startsBefore: string;
  ordering: string;
}) {
  const query = new URLSearchParams();
  query.set("page", String(params.page));
  query.set("page_size", "20");
  if (params.search) query.set("search", params.search);
  if (params.status) query.set("status", params.status);
  if (params.category) query.set("category", params.category);
  if (params.featured) query.set("featured", params.featured);
  if (params.startsAfter) query.set("starts_after", params.startsAfter);
  if (params.startsBefore) query.set("starts_before", params.startsBefore);
  if (params.ordering) query.set("ordering", params.ordering);
  return `/admin/events/?${query.toString()}`;
}

export function formatDate(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export function statusBadgeClass(status: string): string {
  if (status === "published") return "badge success";
  if (status === "hidden") return "badge warning";
  return "badge";
}
