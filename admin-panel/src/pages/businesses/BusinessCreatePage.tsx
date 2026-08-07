import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import { ApiError, apiFetch } from "../../api";
import { StatusBanner } from "../adminShared";
import BusinessFormFields from "./BusinessFormFields";
import {
  emptyBusinessForm,
  formValuesToPayload,
  type BusinessDetail,
  type BusinessFormValues,
} from "./types";

export default function BusinessCreatePage() {
  const navigate = useNavigate();
  const [form, setForm] = useState<BusinessFormValues>(emptyBusinessForm);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});

  const updateField = (key: keyof BusinessFormValues, value: string | boolean) => {
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
    if (saving) return;

    if (!form.title.trim() || !form.city.trim() || !form.state.trim() || !form.contact_info.trim()) {
      setError("Title, city, state, and contact email/info are required.");
      return;
    }
    if (!form.owner_id.trim()) {
      setError("Owner user ID is required.");
      setFieldErrors({ owner_id: ["Owner user ID is required."] });
      return;
    }

    setSaving(true);
    setError("");
    setFieldErrors({});
    try {
      const created = await apiFetch<BusinessDetail>("/admin/businesses/", {
        method: "POST",
        body: JSON.stringify({
          ...formValuesToPayload(form),
          owner_id: Number(form.owner_id),
        }),
      });
      navigate(`/businesses/${created.id}`, {
        replace: true,
        state: { message: "Business created." },
      });
    } catch (e) {
      if (e instanceof ApiError) {
        setError(e.message);
        setFieldErrors(e.fieldErrors);
      } else {
        setError(e instanceof Error ? e.message : String(e));
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <Link to="/businesses" className="back-link">← Back to businesses</Link>
          <h1>Create business</h1>
          <p className="muted">Create a business using the existing admin API.</p>
        </div>
      </div>

      <StatusBanner error={error} message="" />

      <section className="panel">
        <p className="muted phase-note">
          Image upload is not included in this phase and will be added in Phase 3.
        </p>
        <form onSubmit={handleSubmit}>
          <BusinessFormFields
            values={form}
            errors={fieldErrors}
            onChange={updateField}
            includeOwner
          />
          <div className="form-actions">
            <button type="submit" disabled={saving}>
              {saving ? "Creating…" : "Create business"}
            </button>
            <Link to="/businesses" className="button-link secondary">
              Cancel
            </Link>
          </div>
        </form>
      </section>
    </div>
  );
}
