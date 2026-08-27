import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { ApiError, apiFetch, type Claim, type Paginated } from "../../api";
import { StatusBanner } from "../adminShared";
import BusinessFormFields from "./BusinessFormFields";
import BusinessMediaSection from "./BusinessMediaSection";
import CategorySelect from "./CategorySelect";
import {
  businessToFormValues,
  formValuesToPayload,
  type BusinessDetail,
  type BusinessFormValues,
} from "./types";

type AuditRow = {
  id: number;
  actor_username: string;
  action_type: string;
  summary: string;
  created_at: string;
};

function formatDate(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export default function BusinessDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [business, setBusiness] = useState<BusinessDetail | null>(null);
  const [form, setForm] = useState<BusinessFormValues | null>(null);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [auditRows, setAuditRows] = useState<AuditRow[]>([]);
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
    return Promise.all([
      apiFetch<BusinessDetail>(`/admin/businesses/${businessId}/`),
      apiFetch<Paginated<Claim>>(`/admin/claims/?status=all&listing=${businessId}&page_size=10`),
      apiFetch<Paginated<AuditRow>>(
        `/admin/audit-log/?object_type=listing&object_id=${businessId}&page_size=10`
      ),
    ])
      .then(([detail, claimData, auditData]) => {
        setBusiness(detail);
        setForm(businessToFormValues(detail));
        setClaims(claimData.results);
        setAuditRows(auditData.results);
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

  const showToast = (text: string, isError = false) => {
    if (isError) setError(text);
    else {
      setError("");
      setMessage(text);
    }
  };

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
    return <div className="skeleton-panel">Loading business…</div>;
  }

  if (!business || !form) {
    return (
      <div>
        <Link to="/businesses" className="back-link">← Back to businesses</Link>
        <p className="error">{error || "Business not found."}</p>
      </div>
    );
  }

  const displayName = business.business_name || business.title;

  return (
    <div className="business-detail-layout">
      <div className="page-header">
        <div>
          <Link to="/businesses" className="back-link">← Back to businesses</Link>
          <h1>{displayName}</h1>
          <div className="badge-row">
            <span className="badge">ID {business.id}</span>
            <span className="badge">{business.status}</span>
            {business.is_featured ? <span className="badge accent">Featured</span> : null}
            {business.verified_badge ? <span className="badge accent">Verified</span> : null}
          </div>
        </div>
        <div className="detail-nav">
          <a href="#general">General</a>
          <a href="#location">Location</a>
          <a href="#contact">Contact</a>
          <a href="#owner">Owner</a>
          <a href="#status">Status</a>
          <a href="#media">Media</a>
          <a href="#claims">Claims</a>
          <a href="#audit">Audit</a>
        </div>
      </div>

      <StatusBanner error={error} message={message} />

      <section className="panel" id="general">
        <h2>General information</h2>
        <form onSubmit={handleSave}>
          <div className="form-grid">
            <label className="form-field">
              <span>Title</span>
              <input value={form.title} onChange={(e) => updateField("title", e.target.value)} />
            </label>
            <label className="form-field">
              <span>Business name</span>
              <input value={form.business_name} onChange={(e) => updateField("business_name", e.target.value)} />
            </label>
            <label className="form-field span-2">
              <span>Description</span>
              <textarea rows={4} value={form.description} onChange={(e) => updateField("description", e.target.value)} />
            </label>
            <label className="form-field span-2">
              <span>About</span>
              <textarea rows={3} value={form.about} onChange={(e) => updateField("about", e.target.value)} />
            </label>
          </div>
          <div className="form-actions">
            <button type="submit" disabled={saving || actionLoading}>{saving ? "Saving…" : "Save general info"}</button>
          </div>
        </form>
      </section>

      <section className="panel" id="location">
        <h2>Location</h2>
        <div className="form-grid">
          <label className="form-field span-2"><span>Address</span><input value={form.address} onChange={(e) => updateField("address", e.target.value)} /></label>
          <label className="form-field"><span>City</span><input value={form.city} onChange={(e) => updateField("city", e.target.value)} /></label>
          <label className="form-field"><span>State</span><input value={form.state} onChange={(e) => updateField("state", e.target.value)} /></label>
          <label className="form-field"><span>Latitude</span><input value={form.latitude} onChange={(e) => updateField("latitude", e.target.value)} /></label>
          <label className="form-field"><span>Longitude</span><input value={form.longitude} onChange={(e) => updateField("longitude", e.target.value)} /></label>
        </div>
      </section>

      <section className="panel" id="categories">
        <h2>Categories</h2>
        <CategorySelect
          value={form.category}
          onChange={(value) => updateField("category", value)}
          error={fieldErrors.category?.[0]}
        />
      </section>

      <section className="panel" id="contact">
        <h2>Contact</h2>
        <div className="form-grid">
          <label className="form-field"><span>Phone</span><input value={form.phone} onChange={(e) => updateField("phone", e.target.value)} /></label>
          <label className="form-field"><span>Contact email / info</span><input value={form.contact_info} onChange={(e) => updateField("contact_info", e.target.value)} /></label>
          <label className="form-field"><span>Website</span><input value={form.website} onChange={(e) => updateField("website", e.target.value)} /></label>
          <label className="form-field"><span>Instagram</span><input value={form.instagram} onChange={(e) => updateField("instagram", e.target.value)} /></label>
        </div>
      </section>

      <section className="panel" id="owner">
        <h2>Owner</h2>
        <dl className="meta-grid">
          <div><dt>Creator user ID</dt><dd>{business.user_id}</dd></div>
          <div><dt>Owner user ID</dt><dd>{business.owner_id ?? "—"}</dd></div>
          {business.owner_id ? (
            <div><dt>Owner profile</dt><dd><Link to={`/users/${business.owner_id}`}>View owner</Link></dd></div>
          ) : null}
        </dl>
        <label className="form-field"><span>Reassign owner user ID</span><input value={form.owner_id} onChange={(e) => updateField("owner_id", e.target.value)} /></label>
      </section>

      <section className="panel" id="status">
        <h2>Status</h2>
        <BusinessFormFields values={form} errors={fieldErrors} onChange={updateField} />
        <section className="actions-panel inline-actions">
          <div className="row">
            {business.status !== "published" ? (
              <button type="button" disabled={actionLoading || saving} onClick={() => runQuickAction("Business published.", () => apiFetch(`/admin/businesses/${business.id}/publish/`, { method: "POST" }))}>Publish</button>
            ) : null}
            {business.status !== "hidden" ? (
              <button type="button" className="secondary" disabled={actionLoading || saving} onClick={() => runQuickAction("Business hidden.", () => apiFetch(`/admin/businesses/${business.id}/hide/`, { method: "POST" }))}>Hide</button>
            ) : null}
            <button type="button" className="secondary" disabled={actionLoading || saving} onClick={() => runQuickAction(business.is_featured ? "Business unfeatured." : "Business featured.", () => apiFetch(`/admin/businesses/${business.id}/feature/`, { method: "POST", body: JSON.stringify({ is_featured: !business.is_featured }) }))}>{business.is_featured ? "Unfeature" : "Feature"}</button>
            <button type="button" className="danger" disabled={actionLoading || saving} onClick={() => { setDeleteConfirmName(""); setDeleteStep(1); }}>Delete business</button>
          </div>
          <dl className="meta-grid compact-meta">
            <div><dt>Created</dt><dd>{formatDate(business.created_at)}</dd></div>
            <div><dt>Updated</dt><dd>{formatDate(business.updated_at)}</dd></div>
            <div><dt>Premium</dt><dd>{business.premium_status}</dd></div>
          </dl>
        </section>
      </section>

      <BusinessMediaSection
        businessId={business.id}
        images={business.images}
        onChange={loadBusiness}
        onToast={showToast}
      />

      <section className="panel" id="claims">
        <h2>Related claims</h2>
        {claims.length === 0 ? (
          <p className="muted">No claims for this business.</p>
        ) : (
          <table>
            <thead><tr><th>ID</th><th>Requester</th><th>Status</th><th>Created</th></tr></thead>
            <tbody>
              {claims.map((claim) => (
                <tr key={claim.id}>
                  <td>{claim.id}</td>
                  <td>{claim.requester_username}</td>
                  <td>{claim.status}</td>
                  <td>{formatDate(claim.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="panel" id="audit">
        <h2>Audit</h2>
        {auditRows.length === 0 ? (
          <p className="muted">No audit entries for this business yet.</p>
        ) : (
          <table>
            <thead><tr><th>When</th><th>Actor</th><th>Action</th><th>Summary</th></tr></thead>
            <tbody>
              {auditRows.map((row) => (
                <tr key={row.id}>
                  <td>{formatDate(row.created_at)}</td>
                  <td>{row.actor_username}</td>
                  <td>{row.action_type}</td>
                  <td>{row.summary}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {deleteStep > 0 ? (
        <div className="modal-backdrop">
          <div className="modal-card" role="dialog" aria-modal="true">
            {deleteStep === 1 ? (
              <>
                <h3>Delete business?</h3>
                <p>This permanently deletes <strong>{displayName}</strong>.</p>
                <div className="modal-actions">
                  <button type="button" className="secondary" onClick={() => setDeleteStep(0)}>Cancel</button>
                  <button type="button" className="danger" onClick={() => setDeleteStep(2)}>Continue</button>
                </div>
              </>
            ) : (
              <>
                <h3>Confirm deletion</h3>
                <p>Type <strong>{displayName}</strong> to confirm.</p>
                <input value={deleteConfirmName} onChange={(e) => setDeleteConfirmName(e.target.value)} placeholder={displayName} />
                <div className="modal-actions">
                  <button type="button" className="secondary" onClick={() => setDeleteStep(1)}>Back</button>
                  <button type="button" className="danger" disabled={deleteConfirmName !== displayName || saving} onClick={handleDelete}>{saving ? "Deleting…" : "Delete permanently"}</button>
                </div>
              </>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
