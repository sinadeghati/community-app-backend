import { Link, useLocation, useNavigate } from "react-router-dom";
import { useCallback, useEffect, useState } from "react";
import { ApiError, apiFetch, type Paginated } from "../../api";
import { DataTable, StatusBanner } from "../adminShared";
import {
  ORDERING_OPTIONS,
  STATUS_OPTIONS,
  buildEventListEndpoint,
  formatDate,
  statusBadgeClass,
  type EventListRow,
} from "./types";

export default function EventsListPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [category, setCategory] = useState("");
  const [featured, setFeatured] = useState("");
  const [startsAfter, setStartsAfter] = useState("");
  const [startsBefore, setStartsBefore] = useState("");
  const [ordering, setOrdering] = useState("-starts_at");
  const [page, setPage] = useState(1);
  const [rows, setRows] = useState<EventListRow[]>([]);
  const [count, setCount] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [hasPrev, setHasPrev] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [actionId, setActionId] = useState<number | null>(null);

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
    return apiFetch<Paginated<EventListRow>>(
      buildEventListEndpoint({
        page,
        search,
        status,
        category,
        featured,
        startsAfter,
        startsBefore,
        ordering,
      })
    )
      .then((data) => {
        setRows(data.results);
        setCount(data.count);
        setHasNext(Boolean(data.next));
        setHasPrev(Boolean(data.previous));
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [page, search, status, category, featured, startsAfter, startsBefore, ordering]);

  useEffect(() => {
    load();
  }, [load]);

  const runRowAction = async (eventId: number, label: string, path: string, method = "POST") => {
    setActionId(eventId);
    setError("");
    try {
      if (method === "POST") {
        const result = await apiFetch<{ id?: number }>(path, { method: "POST" });
        if (path.endsWith("/duplicate/") && result.id) {
          navigate(`/events/${result.id}`, { state: { message: label } });
          return;
        }
      } else {
        await apiFetch(path, { method: "DELETE" });
      }
      setMessage(label);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setActionId(null);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Events</h1>
          <p className="muted">{count} total</p>
        </div>
        <Link className="button-link" to="/events/new">
          Create event
        </Link>
      </div>

      <StatusBanner error={error} message={message} />

      <section className="panel filters-panel">
        <div className="filters-grid">
          <label className="form-field">
            <span>Search</span>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Event, business, organizer, city"
            />
          </label>
          <label className="form-field">
            <span>Status</span>
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              {STATUS_OPTIONS.map((option) => (
                <option key={option.value || "all"} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field">
            <span>Category</span>
            <input value={category} onChange={(e) => setCategory(e.target.value)} placeholder="Category" />
          </label>
          <label className="form-field">
            <span>Featured</span>
            <select value={featured} onChange={(e) => setFeatured(e.target.value)}>
              <option value="">All</option>
              <option value="true">Featured</option>
              <option value="false">Not featured</option>
            </select>
          </label>
          <label className="form-field">
            <span>Starts after</span>
            <input type="date" value={startsAfter} onChange={(e) => setStartsAfter(e.target.value)} />
          </label>
          <label className="form-field">
            <span>Starts before</span>
            <input type="date" value={startsBefore} onChange={(e) => setStartsBefore(e.target.value)} />
          </label>
          <label className="form-field">
            <span>Sort</span>
            <select value={ordering} onChange={(e) => setOrdering(e.target.value)}>
              {ORDERING_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <div className="filter-actions">
            <button type="button" onClick={() => { setPage(1); load(); }}>
              Apply filters
            </button>
            <button
              type="button"
              className="secondary"
              onClick={() => {
                setSearch("");
                setStatus("");
                setCategory("");
                setFeatured("");
                setStartsAfter("");
                setStartsBefore("");
                setOrdering("-starts_at");
                setPage(1);
              }}
            >
              Clear
            </button>
          </div>
        </div>
      </section>

      <div className="panel">
        {loading ? (
          <div className="skeleton-panel">Loading events…</div>
        ) : rows.length === 0 ? (
          <div className="media-empty">No events match your filters.</div>
        ) : (
          <DataTable
            rows={rows}
            columns={[
              {
                key: "cover_image_url",
                label: "Cover",
                render: (row) =>
                  row.cover_image_url ? (
                    <img src={row.cover_image_url} alt="" className="thumb" loading="lazy" />
                  ) : (
                    <div className="thumb thumb-empty" />
                  ),
              },
              {
                key: "title",
                label: "Event",
                render: (row) => (
                  <div>
                    <div>{row.title}</div>
                    <small className="muted">#{row.id}</small>
                  </div>
                ),
              },
              {
                key: "listing_title",
                label: "Business",
                render: (row) => row.listing_title || "—",
              },
              {
                key: "organizer_name",
                label: "Organizer",
                render: (row) => row.organizer_name || row.owner_username,
              },
              { key: "category", label: "Category", render: (row) => row.category || "—" },
              { key: "city", label: "City", render: (row) => row.city || "—" },
              { key: "starts_at", label: "Start", render: (row) => formatDate(row.starts_at) },
              { key: "ends_at", label: "End", render: (row) => formatDate(row.ends_at) },
              {
                key: "status",
                label: "Status",
                render: (row) => <span className={statusBadgeClass(row.status)}>{row.status}</span>,
              },
              {
                key: "is_featured",
                label: "Featured",
                render: (row) => (row.is_featured ? "Yes" : "No"),
              },
              { key: "created_at", label: "Created", render: (row) => formatDate(row.created_at) },
              { key: "updated_at", label: "Updated", render: (row) => formatDate(row.updated_at) },
            ]}
            actions={(row) => (
              <div className="table-actions">
                <button type="button" onClick={() => navigate(`/events/${row.id}`)}>View</button>
                <button type="button" onClick={() => navigate(`/events/${row.id}#general`)}>Edit</button>
                {row.status !== "published" ? (
                  <button
                    type="button"
                    disabled={actionId === row.id}
                    onClick={() => runRowAction(row.id, "Event published.", `/admin/events/${row.id}/publish/`)}
                  >
                    Publish
                  </button>
                ) : (
                  <button
                    type="button"
                    disabled={actionId === row.id}
                    onClick={() => runRowAction(row.id, "Event unpublished.", `/admin/events/${row.id}/unpublish/`)}
                  >
                    Unpublish
                  </button>
                )}
                <button
                  type="button"
                  disabled={actionId === row.id}
                  onClick={() =>
                    runRowAction(
                      row.id,
                      row.is_featured ? "Event unfeatured." : "Event featured.",
                      row.is_featured
                        ? `/admin/events/${row.id}/unfeature/`
                        : `/admin/events/${row.id}/feature/`
                    )
                  }
                >
                  {row.is_featured ? "Unfeature" : "Feature"}
                </button>
                <button
                  type="button"
                  disabled={actionId === row.id}
                  onClick={() => runRowAction(row.id, "Event duplicated.", `/admin/events/${row.id}/duplicate/`)}
                >
                  Duplicate
                </button>
              </div>
            )}
          />
        )}

        <div className="pagination-row">
          <button type="button" className="secondary" disabled={!hasPrev || loading} onClick={() => setPage((p) => Math.max(1, p - 1))}>
            Previous
          </button>
          <span className="muted">Page {page}</span>
          <button type="button" className="secondary" disabled={!hasNext || loading} onClick={() => setPage((p) => p + 1)}>
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
