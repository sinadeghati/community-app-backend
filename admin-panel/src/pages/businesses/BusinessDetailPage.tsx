import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { ApiError, apiFetch } from "../../api";
import { StatusBanner } from "../adminShared";
import BusinessFormFields from "./BusinessFormFields";
import {
  businessToFormValues,
  formValuesToPayload,
  type BusinessDetail,
  type BusinessFormValues,
  type BusinessImage,
} from "./types";

function formatDate(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function imagesByRole(images: BusinessImage[], role: BusinessImage["role"]) {
  return images.filter((image) => image.role === role);
}

export default function BusinessDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [business, setBusiness] = useState<BusinessDetail | null>(null);
  const [form, setForm] = useState<BusinessFormValues | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});
  const [deleteStep, setDeleteStep] = useState<0 | 1 | 2>(0);
  const [deleteConfirmName, setDeleteConfirmName] = useState("");

  const businessId = Number(id);

  const loadBusiness = () => {
    if (!businessId) {
      setError("Invalid business ID.");
      setLoading(false);
      return Promise.resolve();
    }
    setLoading(true);
    setError("");
    return apiFetch<BusinessDetail>(`/admin/businesses/${businessId}/`)
      .then((data) => {
        setBusiness(data);
        setForm(businessToFormValues(data));
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    const state = location.state as { message?: string } | null;
    if (state?.message) {
      setMessage(state.message);
      window.history.replaceState({}, document.title);
    }
  }, [location.state]);

  useEffect(() => {
    loadBusiness();
  }, [businessId]);

  const updateField = (key: keyof BusinessFormValues, value: string | boolean) => {
    setForm((current) => (current ? { ...current, [key]: value } : current));
    setFieldErrors((current) => {
      if (!current[key]) return current;
      const next = { ...current };
      delete next[key];
      return next;
    });
  };

  const runQuickAction = async (label: string, fn: () => Promise<unknown>) => {
    setActionLoading(true);
    setError("");
    setMessage("");
    try {
      await fn();
      setMessage(label);
      await loadBusiness();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setActionLoading(false);
    }
  };

  const handleSave = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!form || saving) return;

    if (!form.title.trim() || !form.city.trim() || !form.state.trim() || !form.contact_info.trim()) {
      setError("Title, city, state, and contact email/info are required.");
      return;
    }

    setSaving(true);
    setError("");
    setMessage("");
    setFieldErrors({});
    try {
      const updated = await apiFetch<BusinessDetail>(`/admin/businesses/${businessId}/`, {
        method: "PATCH",
        body: JSON.stringify(formValuesToPayload(form)),
      });
      setBusiness(updated);
      setForm(businessToFormValues(updated));
      setMessage("Business saved.");
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

  const handleDelete = async () => {
    if (!business || saving || actionLoading) return;
    setSaving(true);
    setError("");
    try {
      await apiFetch(`/admin/businesses/${business.id}/`, { method: "DELETE" });
      navigate("/businesses", { replace: true, state: { message: "Business deleted." } });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setDeleteStep(0);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <p className="muted">Loading business…</p>;
  }

  if (!business || !form) {
    return (
      <div>
        <Link to="/businesses" className="back-link">← Back to businesses</Link>
        <p className="error">{error || "Business not found."}</p>
      </div>
    );
  }

  const coverImages = imagesByRole(business.images, "cover");
  const logoImages = imagesByRole(business.images, "logo");
  const galleryImages = imagesByRole(business.images, "gallery");
  const displayName = business.business_name || business.title;

  return (
    <div>
      <div className="page-header">
        <div>
          <Link to="/businesses" className="back-link">← Back to businesses</Link>
          <h1>{displayName}</h1>
          <div className="badge-row">
            <span className="badge">ID {business.id}</span>
            <span className="badge">{business.status}</span>
            {business.is_featured ? <span className="badge accent">Featured</span> : null}
            {business.verified_badge ? <span className="badge accent">Verified</span> : null}
            {business.is_sponsored ? <span className="badge">Sponsored</span> : null}
          </div>
        </div>
      </div>

      <StatusBanner error={error} message={message} />

      <section className="panel detail-meta">
        <h2>Overview</h2>
        <dl className="meta-grid">
          <div><dt>Creator user ID</dt><dd>{business.user_id}</dd></div>
          <div><dt>Owner user ID</dt><dd>{business.owner_id ?? "—"}</dd></div>
          <div><dt>Premium status</dt><dd>{business.premium_status}</dd></div>
          <div><dt>Verified at</dt><dd>{formatDate(business.verified_at)}</dd></div>
          <div><dt>Created</dt><dd>{formatDate(business.created_at)}</dd></div>
          <div><dt>Updated</dt><dd>{formatDate(business.updated_at)}</dd></div>
        </dl>
      </section>

      <section className="panel">
        <h2>Edit business</h2>
        <form onSubmit={handleSave}>
          <BusinessFormFields
            values={form}
            errors={fieldErrors}
            onChange={updateField}
          />
          <div className="form-actions">
            <button type="submit" disabled={saving || actionLoading}>
              {saving ? "Saving…" : "Save changes"}
            </button>
          </div>
        </form>
      </section>

      <section className="panel">
        <h2>Images</h2>
        <p className="muted phase-note">
          Image upload will be available in Phase 3. Existing images are shown read-only below.
        </p>
        <ImageGroup title="Cover" images={coverImages} />
        <ImageGroup title="Logo / avatar" images={logoImages} />
        <ImageGroup title="Gallery" images={galleryImages} />
      </section>

      <section className="panel actions-panel">
        <h2>Actions</h2>
        <div className="row">
          {business.status !== "published" ? (
            <button
              type="button"
              disabled={actionLoading || saving}
              onClick={() =>
                runQuickAction("Business published.", () =>
                  apiFetch(`/admin/businesses/${business.id}/publish/`, { method: "POST" })
                )
              }
            >
              Publish
            </button>
          ) : null}
          {business.status !== "hidden" ? (
            <button
              type="button"
              className="secondary"
              disabled={actionLoading || saving}
              onClick={() =>
                runQuickAction("Business hidden.", () =>
                  apiFetch(`/admin/businesses/${business.id}/hide/`, { method: "POST" })
                )
              }
            >
              Hide
            </button>
          ) : null}
          <button
            type="button"
            className="secondary"
            disabled={actionLoading || saving}
            onClick={() =>
              runQuickAction(
                business.is_featured ? "Business unfeatured." : "Business featured.",
                () =>
                  apiFetch(`/admin/businesses/${business.id}/feature/`, {
                    method: "POST",
                    body: JSON.stringify({ is_featured: !business.is_featured }),
                  })
              )
            }
          >
            {business.is_featured ? "Unfeature" : "Feature"}
          </button>
          <button
            type="button"
            className="secondary"
            disabled={actionLoading || saving}
            onClick={() =>
              runQuickAction(
                business.verified_badge ? "Verification removed." : "Business verified.",
                () =>
                  apiFetch(`/admin/businesses/${business.id}/verify/`, {
                    method: "POST",
                    body: JSON.stringify({ verified_badge: !business.verified_badge }),
                  })
              )
            }
          >
            {business.verified_badge ? "Unverify" : "Verify"}
          </button>
          <button
            type="button"
            className="danger"
            disabled={actionLoading || saving}
            onClick={() => {
              setDeleteConfirmName("");
              setDeleteStep(1);
            }}
          >
            Delete business
          </button>
        </div>
      </section>

      {deleteStep > 0 ? (
        <div className="modal-backdrop">
          <div className="modal-card" role="dialog" aria-modal="true">
            {deleteStep === 1 ? (
              <>
                <h3>Delete business?</h3>
                <p>
                  This permanently deletes <strong>{displayName}</strong>. This action cannot be undone.
                </p>
                <div className="modal-actions">
                  <button type="button" className="secondary" onClick={() => setDeleteStep(0)}>
                    Cancel
                  </button>
                  <button type="button" className="danger" onClick={() => setDeleteStep(2)}>
                    Continue
                  </button>
                </div>
              </>
            ) : (
              <>
                <h3>Confirm deletion</h3>
                <p>
                  Type <strong>{displayName}</strong> to confirm permanent deletion.
                </p>
                <input
                  value={deleteConfirmName}
                  onChange={(e) => setDeleteConfirmName(e.target.value)}
                  placeholder={displayName}
                />
                <div className="modal-actions">
                  <button type="button" className="secondary" onClick={() => setDeleteStep(1)}>
                    Back
                  </button>
                  <button
                    type="button"
                    className="danger"
                    disabled={deleteConfirmName !== displayName || saving}
                    onClick={handleDelete}
                  >
                    {saving ? "Deleting…" : "Delete permanently"}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function ImageGroup({ title, images }: { title: string; images: BusinessImage[] }) {
  return (
    <div className="image-group">
      <h3>{title}</h3>
      {images.length === 0 ? (
        <p className="muted">No {title.toLowerCase()} images.</p>
      ) : (
        <div className="image-grid">
          {images.map((image) => (
            <figure key={image.id} className="image-card">
              {image.image_url ? (
                <img src={image.image_url} alt={`${title} ${image.id}`} />
              ) : (
                <div className="image-placeholder">No preview</div>
              )}
              <figcaption>
                <span>{image.media_status}</span>
              </figcaption>
            </figure>
          ))}
        </div>
      )}
    </div>
  );
}
