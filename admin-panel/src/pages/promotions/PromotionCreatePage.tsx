import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import { ApiError, apiFetch } from "../../api";
import { StatusBanner } from "../adminShared";
import {
  DESTINATION_OPTIONS,
  PLACEMENT_OPTIONS,
  formValuesToPayload,
  type PromotionFormValues,
} from "./types";

const INITIAL: PromotionFormValues = {
  advertiser_name: "",
  title: "",
  subtitle: "",
  placement: "home_hero",
  channel: "",
  starts_at: "",
  ends_at: "",
  display_priority: "0",
  cta_text: "",
  destination_type: "none",
  listing_id: "",
  event_id: "",
  cta_link: "",
  target_route: "",
  target_id: "",
  is_active: false,
  hero_approved: false,
  sponsored_label: "",
  admin_note: "",
};

export default function PromotionCreatePage() {
  const navigate = useNavigate();
  const [form, setForm] = useState<PromotionFormValues>(INITIAL);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const update = (key: keyof PromotionFormValues, value: string | boolean) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!form.title.trim() || !form.advertiser_name.trim()) {
      setError("Title and advertiser are required.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const created = await apiFetch<{ id: number }>("/admin/promotions/", {
        method: "POST",
        body: JSON.stringify(formValuesToPayload(form)),
      });
      navigate(`/promotions/${created.id}`, { state: { message: "Promotion created." } });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Create promotion</h1>
          <p className="muted">Add a hero banner or sponsored placement.</p>
        </div>
        <Link className="button-link secondary" to="/promotions">Back</Link>
      </div>
      <StatusBanner error={error} message="" />
      <form className="panel form-grid" onSubmit={handleSubmit}>
        <label className="form-field"><span>Title</span><input value={form.title} onChange={(e) => update("title", e.target.value)} /></label>
        <label className="form-field"><span>Advertiser</span><input value={form.advertiser_name} onChange={(e) => update("advertiser_name", e.target.value)} /></label>
        <label className="form-field span-2"><span>Subtitle</span><input value={form.subtitle} onChange={(e) => update("subtitle", e.target.value)} /></label>
        <label className="form-field"><span>Placement</span>
          <select value={form.placement} onChange={(e) => update("placement", e.target.value)}>
            {PLACEMENT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </label>
        <label className="form-field"><span>Priority</span><input type="number" value={form.display_priority} onChange={(e) => update("display_priority", e.target.value)} /></label>
        <label className="form-field"><span>Start</span><input type="datetime-local" value={form.starts_at} onChange={(e) => update("starts_at", e.target.value)} /></label>
        <label className="form-field"><span>End</span><input type="datetime-local" value={form.ends_at} onChange={(e) => update("ends_at", e.target.value)} /></label>
        <label className="form-field"><span>CTA label</span><input value={form.cta_text} onChange={(e) => update("cta_text", e.target.value)} /></label>
        <label className="form-field"><span>Destination type</span>
          <select value={form.destination_type} onChange={(e) => update("destination_type", e.target.value)}>
            {DESTINATION_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </label>
        {form.destination_type === "business" ? <label className="form-field"><span>Business ID</span><input value={form.listing_id} onChange={(e) => update("listing_id", e.target.value)} /></label> : null}
        {form.destination_type === "event" ? <label className="form-field"><span>Event ID</span><input value={form.event_id} onChange={(e) => update("event_id", e.target.value)} /></label> : null}
        {form.destination_type === "external_url" ? <label className="form-field span-2"><span>External URL</span><input value={form.cta_link} onChange={(e) => update("cta_link", e.target.value)} /></label> : null}
        {form.destination_type === "internal" ? (
          <>
            <label className="form-field"><span>Route</span><input value={form.target_route} onChange={(e) => update("target_route", e.target.value)} /></label>
            <label className="form-field"><span>Target ID</span><input value={form.target_id} onChange={(e) => update("target_id", e.target.value)} /></label>
          </>
        ) : null}
        <div className="form-actions span-2"><button type="submit" disabled={saving}>{saving ? "Creating…" : "Create promotion"}</button></div>
      </form>
    </div>
  );
}
