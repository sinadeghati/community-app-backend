import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import { ApiError, apiFetch } from "../../api";
import { StatusBanner } from "../adminShared";
import BusinessCreateMediaSection, {
  emptyPendingBusinessMedia,
  type PendingBusinessMedia,
} from "./BusinessCreateMediaSection";
import BusinessFormFields from "./BusinessFormFields";
import { uploadPendingBusinessMedia } from "./businessMediaUpload";
import {
  emptyBusinessForm,
  formValuesToPayload,
  type BusinessDetail,
  type BusinessFormValues,
} from "./types";

export default function BusinessCreatePage() {
  const navigate = useNavigate();
  const [form, setForm] = useState<BusinessFormValues>(emptyBusinessForm);
  const [pendingMedia, setPendingMedia] = useState<PendingBusinessMedia>(
    emptyPendingBusinessMedia()
  );
  const [saving, setSaving] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
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

    if (!form.business_name.trim() || !form.city.trim() || !form.state.trim() || !form.contact_info.trim()) {
      setError("Business name, city, state, and contact email/info are required.");
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
    setUploadProgress(null);
    try {
      const created = await apiFetch<BusinessDetail>("/admin/businesses/", {
        method: "POST",
        body: JSON.stringify({
          ...formValuesToPayload(form),
          owner_id: Number(form.owner_id),
        }),
      });

      const hasMedia =
        pendingMedia.logo || pendingMedia.cover || pendingMedia.gallery.length > 0;
      if (hasMedia) {
        setUploadProgress(0);
        await uploadPendingBusinessMedia(created.id, pendingMedia, setUploadProgress);
      }

      navigate(`/businesses/${created.id}`, {
        replace: true,
        state: { message: hasMedia ? "Business created and media uploaded." : "Business created." },
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
      setUploadProgress(null);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <Link to="/businesses" className="back-link">← Back to businesses</Link>
          <h1>Create business</h1>
          <p className="muted">Enter business details, category, and media for Korook listings.</p>
        </div>
      </div>

      <StatusBanner error={error} message="" />

      <form onSubmit={handleSubmit}>
        <section className="panel">
          <BusinessFormFields
            values={form}
            errors={fieldErrors}
            onChange={updateField}
            includeOwner
          />
        </section>

        <BusinessCreateMediaSection media={pendingMedia} onChange={setPendingMedia} />

        {uploadProgress !== null ? (
          <section className="panel">
            <div className="upload-progress">
              <div className="upload-progress-bar" style={{ width: `${uploadProgress}%` }} />
              <span>Uploading media… {uploadProgress}%</span>
            </div>
          </section>
        ) : null}

        <section className="panel">
          <div className="form-actions">
            <button type="submit" disabled={saving}>
              {saving
                ? uploadProgress !== null
                  ? "Uploading media…"
                  : "Creating…"
                : "Create business"}
            </button>
            <Link to="/businesses" className="button-link secondary">
              Cancel
            </Link>
          </div>
        </section>
      </form>
    </div>
  );
}
