import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import { ApiError, apiFetch } from "../../api";
import { StatusBanner } from "../adminShared";
import { VISIBILITY_OPTIONS, formValuesToPayload, type EventFormValues } from "./types";

const INITIAL: EventFormValues = {
  title: "",
  description: "",
  category: "",
  starts_at: "",
  ends_at: "",
  location: "",
  address: "",
  city: "",
  state: "CA",
  zip_code: "",
  country: "US",
  organizer: "",
  ticket_url: "",
  phone: "",
  website: "",
  instagram: "",
  tags: "",
  listing_id: "",
  owner_id: "",
  status: "draft",
  is_featured: false,
  visibility: "draft",
  admin_note_text: "",
};

export default function EventCreatePage() {
  const navigate = useNavigate();
  const [form, setForm] = useState<EventFormValues>(INITIAL);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});

  const update = (key: keyof EventFormValues, value: string | boolean) => {
    setForm((current) => ({ ...current, [key]: value }));
    setFieldErrors((current) => {
      if (!current[key]) return current;
      const next = { ...current };
      delete next[key];
      return next;
    });
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!form.title.trim() || !form.starts_at || !form.owner_id) {
      setError("Title, start date, and owner ID are required.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const created = await apiFetch<{ id: number }>("/admin/events/", {
        method: "POST",
        body: JSON.stringify({
          ...formValuesToPayload(form),
          owner_id: Number(form.owner_id),
        }),
      });
      navigate(`/events/${created.id}`, { state: { message: "Event created." } });
    } catch (e) {
      if (e instanceof ApiError) {
        setError(e.message);
        setFieldErrors(e.fieldErrors);
      } else {
        setError(String(e));
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Create event</h1>
          <p className="muted">Add a new event to the Korook platform.</p>
        </div>
        <Link className="button-link secondary" to="/events">
          Back to events
        </Link>
      </div>

      <StatusBanner error={error} message="" />

      <form className="panel form-grid" onSubmit={handleSubmit}>
        <label className="form-field span-2">
          <span>Title</span>
          <input value={form.title} onChange={(e) => update("title", e.target.value)} />
          {fieldErrors.title?.map((msg) => <small key={msg} className="error">{msg}</small>)}
        </label>
        <label className="form-field span-2">
          <span>Description</span>
          <textarea rows={4} value={form.description} onChange={(e) => update("description", e.target.value)} />
        </label>
        <label className="form-field">
          <span>Category</span>
          <input value={form.category} onChange={(e) => update("category", e.target.value)} />
        </label>
        <label className="form-field">
          <span>Tags (comma separated)</span>
          <input value={form.tags} onChange={(e) => update("tags", e.target.value)} />
        </label>
        <label className="form-field">
          <span>Start date</span>
          <input type="datetime-local" value={form.starts_at} onChange={(e) => update("starts_at", e.target.value)} />
        </label>
        <label className="form-field">
          <span>End date</span>
          <input type="datetime-local" value={form.ends_at} onChange={(e) => update("ends_at", e.target.value)} />
        </label>
        <label className="form-field">
          <span>City</span>
          <input value={form.city} onChange={(e) => update("city", e.target.value)} />
        </label>
        <label className="form-field">
          <span>State</span>
          <input value={form.state} onChange={(e) => update("state", e.target.value)} />
        </label>
        <label className="form-field span-2">
          <span>Address</span>
          <input value={form.address} onChange={(e) => update("address", e.target.value)} />
        </label>
        <label className="form-field">
          <span>Owner user ID</span>
          <input value={form.owner_id} onChange={(e) => update("owner_id", e.target.value)} />
        </label>
        <label className="form-field">
          <span>Linked business ID</span>
          <input value={form.listing_id} onChange={(e) => update("listing_id", e.target.value)} />
        </label>
        <label className="form-field">
          <span>Visibility</span>
          <select value={form.visibility} onChange={(e) => update("visibility", e.target.value)}>
            {VISIBILITY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>
        <label className="form-field checkbox-field">
          <span>Featured</span>
          <input type="checkbox" checked={form.is_featured} onChange={(e) => update("is_featured", e.target.checked)} />
        </label>
        <div className="form-actions span-2">
          <button type="submit" disabled={saving}>{saving ? "Creating…" : "Create event"}</button>
        </div>
      </form>
    </div>
  );
}
