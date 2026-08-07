export type BusinessListRow = {
  id: number;
  title: string;
  business_name: string;
  city: string;
  status: string;
  is_featured: boolean;
  thumbnail_url: string | null;
};

export type BusinessImage = {
  id: number;
  image: string;
  image_url: string | null;
  role: "cover" | "logo" | "gallery";
  media_status: string;
  moderation_reason: string;
  uploaded_at: string;
  reviewed_at: string | null;
};

export type BusinessDetail = {
  id: number;
  user_id: number;
  owner_id: number | null;
  title: string;
  business_name: string;
  city: string;
  state: string;
  address: string;
  price: string | null;
  description: string | null;
  about: string | null;
  contact_info: string;
  phone: string;
  website: string;
  instagram: string;
  category: string;
  latitude: number | null;
  longitude: number | null;
  status: string;
  is_featured: boolean;
  is_sponsored: boolean;
  premium_status: string;
  premium_start_date: string | null;
  premium_end_date: string | null;
  display_priority: number;
  verified_badge: boolean;
  verified_at: string | null;
  admin_note: string;
  created_at: string;
  updated_at: string;
  images: BusinessImage[];
};

export type BusinessFormValues = {
  title: string;
  business_name: string;
  description: string;
  about: string;
  category: string;
  address: string;
  city: string;
  state: string;
  latitude: string;
  longitude: string;
  phone: string;
  contact_info: string;
  website: string;
  instagram: string;
  status: string;
  is_featured: boolean;
  is_sponsored: boolean;
  premium_status: string;
  premium_start_date: string;
  premium_end_date: string;
  display_priority: string;
  verified_badge: boolean;
  admin_note: string;
  price: string;
  owner_id: string;
};

export const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "draft", label: "Draft" },
  { value: "published", label: "Published" },
  { value: "hidden", label: "Hidden" },
];

export const PREMIUM_STATUS_OPTIONS = [
  { value: "none", label: "None" },
  { value: "trial", label: "Trial" },
  { value: "active", label: "Active" },
  { value: "expired", label: "Expired" },
  { value: "paused", label: "Paused" },
];

function toDateTimeLocal(value: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const offset = date.getTimezoneOffset();
  const local = new Date(date.getTime() - offset * 60_000);
  return local.toISOString().slice(0, 16);
}

export function emptyBusinessForm(): BusinessFormValues {
  return {
    title: "",
    business_name: "",
    description: "",
    about: "",
    category: "",
    address: "",
    city: "",
    state: "",
    latitude: "",
    longitude: "",
    phone: "",
    contact_info: "",
    website: "",
    instagram: "",
    status: "draft",
    is_featured: false,
    is_sponsored: false,
    premium_status: "none",
    premium_start_date: "",
    premium_end_date: "",
    display_priority: "0",
    verified_badge: false,
    admin_note: "",
    price: "",
    owner_id: "",
  };
}

export function businessToFormValues(business: BusinessDetail): BusinessFormValues {
  return {
    title: business.title || "",
    business_name: business.business_name || "",
    description: business.description || "",
    about: business.about || "",
    category: business.category || "",
    address: business.address || "",
    city: business.city || "",
    state: business.state || "",
    latitude: business.latitude != null ? String(business.latitude) : "",
    longitude: business.longitude != null ? String(business.longitude) : "",
    phone: business.phone || "",
    contact_info: business.contact_info || "",
    website: business.website || "",
    instagram: business.instagram || "",
    status: business.status || "draft",
    is_featured: business.is_featured,
    is_sponsored: business.is_sponsored,
    premium_status: business.premium_status || "none",
    premium_start_date: toDateTimeLocal(business.premium_start_date),
    premium_end_date: toDateTimeLocal(business.premium_end_date),
    display_priority: String(business.display_priority ?? 0),
    verified_badge: business.verified_badge,
    admin_note: business.admin_note || "",
    price: business.price ?? "",
    owner_id: business.owner_id != null ? String(business.owner_id) : "",
  };
}

export function formValuesToPayload(values: BusinessFormValues): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    title: values.title.trim(),
    business_name: values.business_name.trim() || values.title.trim(),
    description: values.description.trim() || null,
    about: values.about.trim() || null,
    category: values.category.trim(),
    address: values.address.trim(),
    city: values.city.trim(),
    state: values.state.trim(),
    contact_info: values.contact_info.trim(),
    phone: values.phone.trim(),
    website: values.website.trim(),
    instagram: values.instagram.trim(),
    status: values.status,
    is_featured: values.is_featured,
    is_sponsored: values.is_sponsored,
    premium_status: values.premium_status,
    premium_start_date: values.premium_start_date || null,
    premium_end_date: values.premium_end_date || null,
    display_priority: Number(values.display_priority || 0),
    verified_badge: values.verified_badge,
    admin_note: values.admin_note.trim(),
    price: values.price.trim() ? values.price.trim() : null,
    latitude: values.latitude.trim() ? Number(values.latitude) : null,
    longitude: values.longitude.trim() ? Number(values.longitude) : null,
  };
  if (values.owner_id.trim()) {
    payload.owner_id = Number(values.owner_id);
  }
  return payload;
}

export function buildBusinessListEndpoint(params: {
  page: number;
  search: string;
  city: string;
  status: string;
}): string {
  const qs = new URLSearchParams();
  qs.set("page_size", "25");
  qs.set("page", String(params.page));
  if (params.search.trim()) qs.set("search", params.search.trim());
  if (params.city.trim()) qs.set("city", params.city.trim());
  if (params.status) qs.set("status", params.status);
  return `/admin/businesses/?${qs.toString()}`;
}
