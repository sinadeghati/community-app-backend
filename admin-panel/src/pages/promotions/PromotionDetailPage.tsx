import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { ApiError, apiFetch, type Paginated } from "../../api";
import { StatusBanner } from "../adminShared";
import PromotionHeroSection from "./PromotionHeroSection";
import {
  DESTINATION_OPTIONS,
  PLACEMENT_OPTIONS,
  formatDate,
  formValuesToPayload,
  placementLabel,
  promotionToFormValues,
  statusBadgeClass,
  type PromotionDetail,
  type PromotionFormValues,
} from "./types";

type AuditRow = { id: number; actor_username: string; action_type: string; summary: string; created_at: string };

function MobileHeroPreview({ promo }: { promo: PromotionDetail }) {
  return (
    <div className="mobile-hero-preview">
      <p className="muted preview-disclaimer">Admin preview only — may differ from actual mobile rendering.</p>
      <div className="mobile-hero-frame">
        {promo.image_url ? <img src={promo.image_url} alt="" className="mobile-hero-image" loading="lazy" /> : <div className="thumb thumb-empty wide" />}
        <div className="mobile-hero-overlay">
          {promo.sponsored_label ? <span className="badge accent">{promo.sponsored_label}</span> : null}
          <h3>{promo.title}</h3>
          {promo.subtitle ? <p>{promo.subtitle}</p> : null}
          {promo.cta_text ? <button type="button" className="hero-cta-button">{promo.cta_text}</button> : null}
        </div>
      </div>
    </div>
  );
}

export default function PromotionDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const promotionId = Number(id);
  const [promo, setPromo] = useState<PromotionDetail | null>(null);
  const [form, setForm] = useState<PromotionFormValues | null>(null);
  const [auditRows, setAuditRows] = useState<AuditRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [deleteStep, setDeleteStep] = useState<0 | 1>(0);
  const [deleteConfirmTitle, setDeleteConfirmTitle] = useState("");

  const load = () => {
    if (!promotionId) {
      setError("Invalid promotion ID.");
      setLoading(false);
      return Promise.resolve();
    }
    setLoading(true);
    return Promise.all([
      apiFetch<PromotionDetail>(`/admin/promotions/${promotionId}/`),
      apiFetch<Paginated<AuditRow>>(`/admin/audit-log/?object_type=promotion&object_id=${promotionId}&page_size=10`),
    ])
      .then(([detail, audit]) => {
        setPromo(detail);
        setForm(promotionToFormValues(detail));
        setAuditRows(audit.results);
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

  useEffect(() => { load(); }, [promotionId]);

  const showToast = (text: string, isError = false) => {
    if (isError) setError(text);
    else { setError(""); setMessage(text); }
  };

  const updateField = (key: keyof PromotionFormValues, value: string | boolean) => {
    setForm((c) => (c ? { ...c, [key]: value } : c));
  };

  const runAction = async (label: string, path: string) => {
    setActionLoading(true);
    try {
      const result = await apiFetch<{ id?: number }>(path, { method: "POST" });
      if (path.endsWith("/duplicate/") && result.id) {
        navigate(`/promotions/${result.id}`, { state: { message: label } });
        return;
      }
      setMessage(label);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setActionLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form || saving) return;
    setSaving(true);
    try {
      const updated = await apiFetch<PromotionDetail>(`/admin/promotions/${promotionId}/`, {
        method: "PATCH",
        body: JSON.stringify(formValuesToPayload(form)),
      });
      setPromo(updated);
      setForm(promotionToFormValues(updated));
      setMessage("Promotion saved.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!promo) return;
    if (deleteStep === 0) { setDeleteStep(1); return; }
    if (deleteConfirmTitle.trim() !== promo.title.trim()) {
      setError("Promotion title does not match.");
      return;
    }
    setActionLoading(true);
    try {
      await apiFetch(`/admin/promotions/${promotionId}/`, { method: "DELETE" });
      navigate("/promotions", { state: { message: `Deleted ${promo.title}.` } });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) return <div className="skeleton-panel">Loading promotion…</div>;
  if (!promo || !form) return <p className="error">{error || "Promotion not found."}</p>;

  return (
    <div className="business-detail-layout">
      <div className="page-header">
        <div>
          <h1>{promo.title}</h1>
          <p className="muted">
            <span className={statusBadgeClass(promo.status)}>{promo.status}</span>
            {" · "}{placementLabel(promo.placement)}
            {" · Priority "}{promo.display_priority}
          </p>
        </div>
        <Link className="button-link secondary" to="/promotions">Back</Link>
      </div>

      <nav className="detail-nav">
        <a href="#overview">Overview</a>
        <a href="#hero-media">Media</a>
        <a href="#content">Content</a>
        <a href="#destination">Destination</a>
        <a href="#schedule">Schedule</a>
        <a href="#status">Status</a>
        <a href="#preview">Preview</a>
        <a href="#audit">Audit</a>
      </nav>

      <StatusBanner error={error} message={message} />

      <section className="panel" id="overview">
        <h2>Overview</h2>
        <p><strong>Advertiser:</strong> {promo.advertiser_name}</p>
        <p><strong>Destination:</strong> {promo.destination_label}</p>
        <p><strong>Schedule state:</strong> {promo.schedule_state}</p>
        <p className="muted">Created {formatDate(promo.created_at)} · Updated {formatDate(promo.updated_at)}</p>
      </section>

      <PromotionHeroSection promotionId={promotionId} promotion={promo} onChange={load} onToast={showToast} />

      <section className="panel" id="content">
        <h2>Content</h2>
        <form className="form-grid" onSubmit={handleSave}>
          <label className="form-field span-2"><span>Title</span><input value={form.title} onChange={(e) => updateField("title", e.target.value)} /></label>
          <label className="form-field span-2"><span>Subtitle</span><input value={form.subtitle} onChange={(e) => updateField("subtitle", e.target.value)} /></label>
          <label className="form-field"><span>Placement</span>
            <select value={form.placement} onChange={(e) => updateField("placement", e.target.value)}>
              {PLACEMENT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </label>
          <label className="form-field"><span>Channel</span><input value={form.channel} onChange={(e) => updateField("channel", e.target.value)} /></label>
          <label className="form-field"><span>Sponsored label</span><input value={form.sponsored_label} onChange={(e) => updateField("sponsored_label", e.target.value)} /></label>
          <label className="form-field span-2"><span>Admin note</span><textarea rows={3} value={form.admin_note} onChange={(e) => updateField("admin_note", e.target.value)} /></label>
          <div className="form-actions span-2"><button type="submit" disabled={saving}>{saving ? "Saving…" : "Save content"}</button></div>
        </form>
      </section>

      <section className="panel" id="destination">
        <h2>Destination / CTA</h2>
        <div className="form-grid">
          <label className="form-field"><span>CTA label</span><input value={form.cta_text} onChange={(e) => updateField("cta_text", e.target.value)} /></label>
          <label className="form-field"><span>Destination type</span>
            <select value={form.destination_type} onChange={(e) => updateField("destination_type", e.target.value)}>
              {DESTINATION_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </label>
          {form.destination_type === "business" ? <label className="form-field"><span>Business ID</span><input value={form.listing_id} onChange={(e) => updateField("listing_id", e.target.value)} />{promo.listing_title ? <small className="muted">{promo.listing_title}</small> : null}</label> : null}
          {form.destination_type === "event" ? <label className="form-field"><span>Event ID</span><input value={form.event_id} onChange={(e) => updateField("event_id", e.target.value)} />{promo.event_title ? <small className="muted">{promo.event_title}</small> : null}</label> : null}
          {form.destination_type === "external_url" ? <label className="form-field span-2"><span>External URL</span><input value={form.cta_link} onChange={(e) => updateField("cta_link", e.target.value)} /></label> : null}
          {form.destination_type === "internal" ? (
            <>
              <label className="form-field"><span>Route</span><input value={form.target_route} onChange={(e) => updateField("target_route", e.target.value)} /></label>
              <label className="form-field"><span>Target ID</span><input value={form.target_id} onChange={(e) => updateField("target_id", e.target.value)} /></label>
            </>
          ) : null}
        </div>
      </section>

      <section className="panel" id="schedule">
        <h2>Schedule</h2>
        <div className="form-grid">
          <label className="form-field"><span>Start</span><input type="datetime-local" value={form.starts_at} onChange={(e) => updateField("starts_at", e.target.value)} /></label>
          <label className="form-field"><span>End</span><input type="datetime-local" value={form.ends_at} onChange={(e) => updateField("ends_at", e.target.value)} /></label>
          <label className="form-field"><span>Priority</span><input type="number" value={form.display_priority} onChange={(e) => updateField("display_priority", e.target.value)} /></label>
        </div>
      </section>

      <section className="panel" id="status">
        <h2>Status</h2>
        <label className="form-field checkbox-field"><span>Active</span><input type="checkbox" checked={form.is_active} onChange={(e) => updateField("is_active", e.target.checked)} /></label>
        <label className="form-field checkbox-field"><span>Hero approved</span><input type="checkbox" checked={form.hero_approved} onChange={(e) => updateField("hero_approved", e.target.checked)} /></label>
        <div className="inline-actions">
          <button type="button" disabled={actionLoading} onClick={() => runAction("Activated.", `/admin/promotions/${promotionId}/activate/`)}>Activate</button>
          <button type="button" disabled={actionLoading} onClick={() => runAction("Deactivated.", `/admin/promotions/${promotionId}/deactivate/`)}>Deactivate</button>
          <button type="button" disabled={actionLoading} onClick={() => runAction("Duplicated.", `/admin/promotions/${promotionId}/duplicate/`)}>Duplicate</button>
        </div>
      </section>

      <section className="panel" id="preview">
        <h2>Mobile-style preview</h2>
        <MobileHeroPreview promo={promo} />
      </section>

      <section className="panel" id="analytics">
        <h2>Analytics</h2>
        {promo.analytics_available ? <p>Analytics available.</p> : (
          <p className="muted">Impressions, clicks, and CTR are not tracked yet. Analytics requires a future scoped feature.</p>
        )}
      </section>

      <section className="panel" id="audit">
        <h2>Audit</h2>
        {auditRows.length === 0 ? <p className="muted">No audit entries.</p> : (
          <table><thead><tr><th>When</th><th>Actor</th><th>Action</th><th>Summary</th></tr></thead>
            <tbody>{auditRows.map((row) => (
              <tr key={row.id}><td>{formatDate(row.created_at)}</td><td>{row.actor_username}</td><td>{row.action_type}</td><td>{row.summary}</td></tr>
            ))}</tbody></table>
        )}
      </section>

      <section className="panel danger-panel">
        <h2>Delete promotion</h2>
        {deleteStep === 0 ? <button type="button" className="danger" onClick={() => setDeleteStep(1)}>Delete promotion</button> : (
          <div className="form-grid">
            <label className="form-field span-2"><span>Type title to confirm: <strong>{promo.title}</strong></span><input value={deleteConfirmTitle} onChange={(e) => setDeleteConfirmTitle(e.target.value)} /></label>
            <div className="form-actions span-2">
              <button type="button" className="secondary" onClick={() => { setDeleteStep(0); setDeleteConfirmTitle(""); }}>Cancel</button>
              <button type="button" className="danger" disabled={actionLoading} onClick={handleDelete}>Confirm delete</button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
