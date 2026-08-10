import { Link, useLocation, useNavigate } from "react-router-dom";
import { useCallback, useEffect, useState } from "react";
import { ApiError, apiFetch, type Paginated } from "../../api";
import { DataTable, StatusBanner } from "../adminShared";
import {
  LIFECYCLE_OPTIONS,
  ORDERING_OPTIONS,
  PLACEMENT_OPTIONS,
  STATUS_OPTIONS,
  buildPromotionListEndpoint,
  formatDate,
  placementLabel,
  statusBadgeClass,
  type PromotionListRow,
} from "./types";

export default function PromotionsListPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [placement, setPlacement] = useState("");
  const [advertiser, setAdvertiser] = useState("");
  const [lifecycle, setLifecycle] = useState("");
  const [ordering, setOrdering] = useState("display_priority");
  const [page, setPage] = useState(1);
  const [rows, setRows] = useState<PromotionListRow[]>([]);
  const [count, setCount] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [hasPrev, setHasPrev] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [actionId, setActionId] = useState<number | null>(null);
  const [draggingId, setDraggingId] = useState<number | null>(null);

  useEffect(() => {
    const state = location.state as { message?: string } | null;
    if (state?.message) {
      setMessage(state.message);
      window.history.replaceState({}, document.title);
    }
  }, [location.state]);

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    return apiFetch<Paginated<PromotionListRow>>(
      buildPromotionListEndpoint({ page, search, status, placement, advertiser, lifecycle, ordering })
    )
      .then((data) => {
        setRows(data.results);
        setCount(data.count);
        setHasNext(Boolean(data.next));
        setHasPrev(Boolean(data.previous));
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [page, search, status, placement, advertiser, lifecycle, ordering]);

  useEffect(() => {
    load();
  }, [load]);

  const runAction = async (id: number, label: string, path: string) => {
    setActionId(id);
    setError("");
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
      setActionId(null);
    }
  };

  const persistOrder = async (order: number[]) => {
    try {
      await apiFetch("/admin/promotions/reorder/", {
        method: "POST",
        body: JSON.stringify({ order }),
      });
      setMessage("Promotion order saved.");
      await load();
    } catch {
      setError("Could not save promotion order.");
      await load();
    }
  };

  const onDrop = async (targetId: number) => {
    if (!draggingId || draggingId === targetId) return;
    const ids = rows.map((row) => row.id);
    const from = ids.indexOf(draggingId);
    const to = ids.indexOf(targetId);
    if (from < 0 || to < 0) return;
    const next = [...ids];
    next.splice(from, 1);
    next.splice(to, 0, draggingId);
    await persistOrder(next);
    setDraggingId(null);
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Promotions / Hero Ads</h1>
          <p className="muted">{count} total · drag rows to reorder priority</p>
        </div>
        <Link className="button-link" to="/promotions/new">Create promotion</Link>
      </div>

      <StatusBanner error={error} message={message} />

      <section className="panel filters-panel">
        <div className="filters-grid">
          <label className="form-field">
            <span>Search</span>
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Title, advertiser, subtitle" />
          </label>
          <label className="form-field">
            <span>Status</span>
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              {STATUS_OPTIONS.map((o) => <option key={o.value || "all"} value={o.value}>{o.label}</option>)}
            </select>
          </label>
          <label className="form-field">
            <span>Placement</span>
            <select value={placement} onChange={(e) => setPlacement(e.target.value)}>
              <option value="">All placements</option>
              {PLACEMENT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </label>
          <label className="form-field">
            <span>Advertiser</span>
            <input value={advertiser} onChange={(e) => setAdvertiser(e.target.value)} />
          </label>
          <label className="form-field">
            <span>Lifecycle</span>
            <select value={lifecycle} onChange={(e) => setLifecycle(e.target.value)}>
              {LIFECYCLE_OPTIONS.map((o) => <option key={o.value || "all"} value={o.value}>{o.label}</option>)}
            </select>
          </label>
          <label className="form-field">
            <span>Sort</span>
            <select value={ordering} onChange={(e) => setOrdering(e.target.value)}>
              {ORDERING_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </label>
          <div className="filter-actions">
            <button type="button" onClick={() => { setPage(1); load(); }}>Apply filters</button>
            <button type="button" className="secondary" onClick={() => {
              setSearch(""); setStatus(""); setPlacement(""); setAdvertiser(""); setLifecycle(""); setOrdering("display_priority"); setPage(1);
            }}>Clear</button>
          </div>
        </div>
      </section>

      <div className="panel">
        {loading ? <div className="skeleton-panel">Loading promotions…</div> : rows.length === 0 ? (
          <div className="media-empty">No promotions match your filters.</div>
        ) : (
          <DataTable
            rows={rows}
            columns={[
              { key: "drag", label: "", render: (row) => (
                <span className="drag-handle" draggable onDragStart={() => setDraggingId(row.id)} onDragOver={(e) => e.preventDefault()} onDrop={() => onDrop(row.id)}>⋮⋮</span>
              )},
              { key: "image_url", label: "Thumbnail", render: (row) => row.image_url ? <img src={row.image_url} alt="" className="thumb" loading="lazy" /> : <div className="thumb thumb-empty" /> },
              { key: "title", label: "Title", render: (row) => <div><div>{row.title}</div><small className="muted">#{row.id}</small></div> },
              { key: "placement", label: "Placement", render: (row) => placementLabel(row.placement) },
              { key: "advertiser_name", label: "Advertiser" },
              { key: "status", label: "Status", render: (row) => <span className={statusBadgeClass(row.status)}>{row.status}</span> },
              { key: "display_priority", label: "Priority" },
              { key: "starts_at", label: "Start", render: (row) => formatDate(row.starts_at) },
              { key: "ends_at", label: "End", render: (row) => formatDate(row.ends_at) },
              { key: "destination_label", label: "Destination" },
              { key: "created_at", label: "Created", render: (row) => formatDate(row.created_at) },
            ]}
            actions={(row) => (
              <div className="table-actions">
                <button type="button" onClick={() => navigate(`/promotions/${row.id}`)}>View</button>
                <button type="button" onClick={() => navigate(`/promotions/${row.id}#content`)}>Edit</button>
                <button type="button" disabled={actionId === row.id} onClick={() => runAction(row.id, "Promotion activated.", `/admin/promotions/${row.id}/activate/`)}>Activate</button>
                <button type="button" disabled={actionId === row.id} onClick={() => runAction(row.id, "Promotion deactivated.", `/admin/promotions/${row.id}/deactivate/`)}>Deactivate</button>
                <button type="button" disabled={actionId === row.id} onClick={() => runAction(row.id, "Promotion duplicated.", `/admin/promotions/${row.id}/duplicate/`)}>Duplicate</button>
              </div>
            )}
          />
        )}
        <div className="pagination-row">
          <button type="button" className="secondary" disabled={!hasPrev || loading} onClick={() => setPage((p) => Math.max(1, p - 1))}>Previous</button>
          <span className="muted">Page {page}</span>
          <button type="button" className="secondary" disabled={!hasNext || loading} onClick={() => setPage((p) => p + 1)}>Next</button>
        </div>
      </div>
    </div>
  );
}
