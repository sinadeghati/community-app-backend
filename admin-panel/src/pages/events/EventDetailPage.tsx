import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { ApiError, apiFetch, type Claim, type Paginated } from "../../api";
import { StatusBanner } from "../adminShared";
import EventMediaSection from "./EventMediaSection";
import {
  VISIBILITY_OPTIONS,
  eventToFormValues,
  formatDate,
  formValuesToPayload,
  statusBadgeClass,
  type EventDetail,
  type EventFormValues,
} from "./types";

type AuditRow = {
  id: number;
  actor_username: string;
  action_type: string;
  summary: string;
  created_at: string;
};

type ReportRow = {
  id: number;
  reason: string;
  status: string;
  created_at: string;
};

type PromotionRow = {
  id: number;
  title: string;
  placement: string;
  status: string;
};

export default function EventDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const eventId = Number(id);

  const [event, setEvent] = useState<EventDetail | null>(null);
  const [form, setForm] = useState<EventFormValues | null>(null);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [reports, setReports] = useState<ReportRow[]>([]);
  const [promotions, setPromotions] = useState<PromotionRow[]>([]);
  const [auditRows, setAuditRows] = useState<AuditRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});
  const [deleteStep, setDeleteStep] = useState<0 | 1>(0);
  const [deleteConfirmTitle, setDeleteConfirmTitle] = useState("");
  const [previewMode, setPreviewMode] = useState<"mobile" | "website" | null>(null);

  const loadEvent = () => {
    if (!eventId) {
      setError("Invalid event ID.");
      setLoading(false);
      return Promise.resolve();
    }
    setLoading(true);
    setError("");
    return Promise.all([
      apiFetch<EventDetail>(`/admin/events/${eventId}/`),
      apiFetch<Paginated<ReportRow>>(
        `/admin/reports/?object_type=event&object_id=${eventId}&page_size=10`
      ),
      apiFetch<Paginated<PromotionRow>>(`/admin/promotions/?event=${eventId}&page_size=10`),
      apiFetch<Paginated<AuditRow>>(
        `/admin/audit-log/?object_type=event&object_id=${eventId}&page_size=10`
      ),
    ])
      .then(async ([detail, reportData, promotionData, auditData]) => {
        setEvent(detail);
        setForm(eventToFormValues(detail));
        setReports(reportData.results);
        setPromotions(promotionData.results);
        setAuditRows(auditData.results);
        if (detail.listing_id) {
          const claimData = await apiFetch<Paginated<Claim>>(
            `/admin/claims/?status=all&listing=${detail.listing_id}&page_size=10`
          );
          setClaims(claimData.results);
        } else {
          setClaims([]);
        }
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
    loadEvent();
  }, [eventId]);

  const showToast = (text: string, isError = false) => {
    if (isError) setError(text);
    else {
      setError("");
      setMessage(text);
    }
  };

  const updateField = (key: keyof EventFormValues, value: string | boolean) => {
    setForm((current) => (current ? { ...current, [key]: value } : current));
    setFieldErrors((current) => {
      if (!current[key]) return current;
      const next = { ...current };
      delete next[key];
      return next;
    });
  };

  const runAction = async (label: string, path: string) => {
    setActionLoading(true);
    setError("");
    try {
      await apiFetch(path, { method: "POST" });
      setMessage(label);
      await loadEvent();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setActionLoading(false);
    }
  };

  const handleSave = async (submitEvent: React.FormEvent) => {
    submitEvent.preventDefault();
    if (!form || saving) return;
    setSaving(true);
    setError("");
    try {
      const updated = await apiFetch<EventDetail>(`/admin/events/${eventId}/`, {
        method: "PATCH",
        body: JSON.stringify(formValuesToPayload(form)),
      });
      setEvent(updated);
      setForm(eventToFormValues(updated));
      setMessage("Event saved.");
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

  const handleDelete = async () => {
    if (!event) return;
    if (deleteStep === 0) {
      setDeleteStep(1);
      return;
    }
    if (deleteConfirmTitle.trim() !== event.title.trim()) {
      setError("Event title does not match.");
      return;
    }
    setActionLoading(true);
    try {
      await apiFetch(`/admin/events/${eventId}/`, { method: "DELETE" });
      navigate("/events", { state: { message: `Deleted ${event.title}.` } });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) return <div className="skeleton-panel">Loading event…</div>;
  if (!event || !form) return <p className="error">{error || "Event not found."}</p>;

  return (
    <div className="business-detail-layout">
      <div className="page-header">
        <div>
          <h1>{event.title}</h1>
          <p className="muted">
            <span className={statusBadgeClass(event.status)}>{event.status}</span>
            {" · "}
            {event.is_featured ? "Featured" : "Not featured"}
            {" · "}
            {event.media_count} media
          </p>
        </div>
        <div className="inline-actions">
          <Link className="button-link secondary" to="/events">Back</Link>
          <button type="button" className="secondary" onClick={() => setPreviewMode("mobile")}>Preview mobile</button>
          <button type="button" className="secondary" onClick={() => setPreviewMode("website")}>Preview website</button>
          <button type="button" className="secondary" onClick={() => window.open("/api/events/", "_blank")}>
            Open public feed
          </button>
        </div>
      </div>

      <nav className="detail-nav">
        <a href="#general">General</a>
        <a href="#business">Business</a>
        <a href="#organizer">Organizer</a>
        <a href="#location">Location</a>
        <a href="#categories">Categories</a>
        <a href="#description">Description</a>
        <a href="#status">Status</a>
        <a href="#media">Media</a>
        <a href="#audit">Audit</a>
        <a href="#reports">Reports</a>
        <a href="#claims">Claims</a>
        <a href="#preview">Preview</a>
      </nav>

      <StatusBanner error={error} message={message} />

      <section className="panel" id="general">
        <h2>General information</h2>
        <form className="form-grid" onSubmit={handleSave}>
          <label className="form-field span-2">
            <span>Title</span>
            <input value={form.title} onChange={(e) => updateField("title", e.target.value)} />
          </label>
          <label className="form-field">
            <span>Start date</span>
            <input type="datetime-local" value={form.starts_at} onChange={(e) => updateField("starts_at", e.target.value)} />
          </label>
          <label className="form-field">
            <span>End date</span>
            <input type="datetime-local" value={form.ends_at} onChange={(e) => updateField("ends_at", e.target.value)} />
          </label>
          <label className="form-field">
            <span>Phone</span>
            <input value={form.phone} onChange={(e) => updateField("phone", e.target.value)} />
          </label>
          <label className="form-field">
            <span>Website</span>
            <input value={form.website} onChange={(e) => updateField("website", e.target.value)} />
          </label>
          <label className="form-field">
            <span>Instagram</span>
            <input value={form.instagram} onChange={(e) => updateField("instagram", e.target.value)} />
          </label>
          <label className="form-field">
            <span>Ticket URL</span>
            <input value={form.ticket_url} onChange={(e) => updateField("ticket_url", e.target.value)} />
          </label>
          <div className="form-actions span-2">
            <button type="submit" disabled={saving}>{saving ? "Saving…" : "Save changes"}</button>
          </div>
        </form>
      </section>

      <section className="panel" id="business">
        <h2>Business</h2>
        <p>
          {event.listing_title ? (
            <Link to={`/businesses/${event.listing_id}`}>{event.listing_title}</Link>
          ) : (
            "No linked business"
          )}
        </p>
        <label className="form-field">
          <span>Linked business ID</span>
          <input value={form.listing_id} onChange={(e) => updateField("listing_id", e.target.value)} />
        </label>
        <p className="muted compact-meta">Promotions: {event.promotions_count}</p>
        {promotions.length > 0 ? (
          <ul>
            {promotions.map((promotion) => (
              <li key={promotion.id}>{promotion.title} · {promotion.placement} · {promotion.status}</li>
            ))}
          </ul>
        ) : null}
      </section>

      <section className="panel" id="organizer">
        <h2>Organizer</h2>
        <p><strong>Owner:</strong> <Link to={`/users/${event.owner_id}`}>{event.owner_username}</Link></p>
        <label className="form-field">
          <span>Organizer display name</span>
          <input value={form.organizer} onChange={(e) => updateField("organizer", e.target.value)} />
        </label>
      </section>

      <section className="panel" id="location">
        <h2>Location</h2>
        <div className="form-grid">
          <label className="form-field span-2">
            <span>Address</span>
            <input value={form.address} onChange={(e) => updateField("address", e.target.value)} />
          </label>
          <label className="form-field">
            <span>City</span>
            <input value={form.city} onChange={(e) => updateField("city", e.target.value)} />
          </label>
          <label className="form-field">
            <span>State</span>
            <input value={form.state} onChange={(e) => updateField("state", e.target.value)} />
          </label>
          <label className="form-field">
            <span>Location label</span>
            <input value={form.location} onChange={(e) => updateField("location", e.target.value)} />
          </label>
        </div>
      </section>

      <section className="panel" id="categories">
        <h2>Categories</h2>
        <label className="form-field">
          <span>Category</span>
          <input value={form.category} onChange={(e) => updateField("category", e.target.value)} />
        </label>
        <label className="form-field">
          <span>Tags</span>
          <input value={form.tags} onChange={(e) => updateField("tags", e.target.value)} placeholder="Comma separated" />
        </label>
      </section>

      <section className="panel" id="description">
        <h2>Description</h2>
        <textarea rows={6} value={form.description} onChange={(e) => updateField("description", e.target.value)} />
      </section>

      <section className="panel" id="status">
        <h2>Status</h2>
        <div className="form-grid">
          <label className="form-field">
            <span>Visibility</span>
            <select value={form.visibility} onChange={(e) => updateField("visibility", e.target.value)}>
              {VISIBILITY_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
          <label className="form-field checkbox-field">
            <span>Featured</span>
            <input type="checkbox" checked={form.is_featured} onChange={(e) => updateField("is_featured", e.target.checked)} />
          </label>
          <label className="form-field span-2">
            <span>Admin note</span>
            <textarea rows={3} value={form.admin_note_text} onChange={(e) => updateField("admin_note_text", e.target.value)} />
          </label>
        </div>
        <div className="inline-actions">
          <button type="button" disabled={actionLoading} onClick={() => runAction("Event published.", `/admin/events/${eventId}/publish/`)}>Publish</button>
          <button type="button" disabled={actionLoading} onClick={() => runAction("Event unpublished.", `/admin/events/${eventId}/unpublish/`)}>Unpublish</button>
          <button type="button" disabled={actionLoading} onClick={() => runAction("Event hidden.", `/admin/events/${eventId}/hide/`)}>Hide</button>
          <button type="button" disabled={actionLoading} onClick={() => runAction("Event archived.", `/admin/events/${eventId}/archive/`)}>Archive</button>
          <button type="button" disabled={actionLoading} onClick={() => runAction("Event featured.", `/admin/events/${eventId}/feature/`)}>Feature</button>
          <button type="button" disabled={actionLoading} onClick={() => runAction("Event duplicated.", `/admin/events/${eventId}/duplicate/`)}>Duplicate</button>
        </div>
        <p className="muted compact-meta">Created {formatDate(event.created_at)} · Updated {formatDate(event.updated_at)}</p>
      </section>

      <EventMediaSection
        eventId={eventId}
        coverImageUrl={event.cover_image_url}
        gallery={event.gallery}
        onChange={loadEvent}
        onToast={showToast}
      />

      <section className="panel" id="audit">
        <h2>Audit log</h2>
        {auditRows.length === 0 ? (
          <p className="muted">No audit entries yet.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>When</th>
                <th>Actor</th>
                <th>Action</th>
                <th>Summary</th>
              </tr>
            </thead>
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

      <section className="panel" id="reports">
        <h2>Related reports</h2>
        <p className="muted">{event.reports_count} total</p>
        {reports.length === 0 ? (
          <p className="muted">No reports for this event.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Reason</th>
                <th>Status</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((row) => (
                <tr key={row.id}>
                  <td>{row.id}</td>
                  <td>{row.reason}</td>
                  <td>{row.status}</td>
                  <td>{formatDate(row.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="panel" id="claims">
        <h2>Related claims</h2>
        <p className="muted">{event.claims_count} on linked business</p>
        {claims.length === 0 ? (
          <p className="muted">No related claims.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Business</th>
                <th>Requester</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {claims.map((claim) => (
                <tr key={claim.id}>
                  <td>{claim.id}</td>
                  <td>{claim.listing_title}</td>
                  <td>{claim.requester_username}</td>
                  <td>{claim.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="panel" id="preview">
        <h2>Preview</h2>
        <div className="preview-grid">
          <article className="preview-card mobile-preview">
            <h3>Mobile preview</h3>
            {event.cover_image_url ? <img src={event.cover_image_url} alt="" className="preview-cover" loading="lazy" /> : <div className="thumb thumb-empty" />}
            <strong>{event.title}</strong>
            <p className="muted">{formatDate(event.starts_at)} · {event.city}</p>
            <p>{event.description.slice(0, 140)}{event.description.length > 140 ? "…" : ""}</p>
          </article>
          <article className="preview-card website-preview">
            <h3>Website preview</h3>
            {event.cover_image_url ? <img src={event.cover_image_url} alt="" className="preview-cover wide" loading="lazy" /> : <div className="thumb thumb-empty wide" />}
            <strong>{event.title}</strong>
            <p className="muted">{event.category} · {event.city}, {event.state}</p>
            <p>{event.description}</p>
          </article>
        </div>
      </section>

      <section className="panel danger-panel">
        <h2>Delete event</h2>
        <p className="muted">This permanently removes the event and cannot be undone.</p>
        {deleteStep === 0 ? (
          <button type="button" className="danger" onClick={() => setDeleteStep(1)}>Delete event</button>
        ) : (
          <div className="form-grid">
            <label className="form-field span-2">
              <span>Type the event title to confirm: <strong>{event.title}</strong></span>
              <input value={deleteConfirmTitle} onChange={(e) => setDeleteConfirmTitle(e.target.value)} />
            </label>
            <div className="form-actions span-2">
              <button type="button" className="secondary" onClick={() => { setDeleteStep(0); setDeleteConfirmTitle(""); }}>Cancel</button>
              <button type="button" className="danger" disabled={actionLoading} onClick={handleDelete}>Confirm delete</button>
            </div>
          </div>
        )}
      </section>

      {previewMode ? (
        <div className="modal-backdrop" onClick={() => setPreviewMode(null)}>
          <div className={`modal-card preview-modal ${previewMode}`} onClick={(e) => e.stopPropagation()}>
            <h3>{previewMode === "mobile" ? "Mobile preview" : "Website preview"}</h3>
            {event.cover_image_url ? <img src={event.cover_image_url} alt="" className="media-preview-image" loading="lazy" /> : null}
            <strong>{event.title}</strong>
            <p className="muted">{formatDate(event.starts_at)} · {event.city}</p>
            <p>{event.description}</p>
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={() => setPreviewMode(null)}>Close</button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
