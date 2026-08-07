import { Link, useLocation, useNavigate } from "react-router-dom";
import { useCallback, useEffect, useState } from "react";
import { apiFetch, type Paginated } from "../../api";
import { DataTable, StatusBanner } from "../adminShared";
import {
  buildBusinessListEndpoint,
  STATUS_OPTIONS,
  type BusinessListRow,
} from "./types";

export default function BusinessesListPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [search, setSearch] = useState("");
  const [city, setCity] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [rows, setRows] = useState<BusinessListRow[]>([]);
  const [count, setCount] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [hasPrev, setHasPrev] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

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
    return apiFetch<Paginated<BusinessListRow>>(
      buildBusinessListEndpoint({ page, search, city, status })
    )
      .then((data) => {
        setRows(data.results);
        setCount(data.count);
        setHasNext(Boolean(data.next));
        setHasPrev(Boolean(data.previous));
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [page, search, city, status]);

  useEffect(() => {
    load();
  }, [load]);

  const applyFilters = () => {
    setPage(1);
    load();
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Businesses</h1>
          <p className="muted">{count} total</p>
        </div>
        <Link className="button-link" to="/businesses/new">
          Create business
        </Link>
      </div>

      <StatusBanner error={error} message={message} />

      <section className="panel filters-panel">
        <div className="filters-grid">
          <label className="form-field">
            <span>Search title or name</span>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search businesses"
              onKeyDown={(e) => {
                if (e.key === "Enter") applyFilters();
              }}
            />
          </label>
          <label className="form-field">
            <span>City</span>
            <input
              value={city}
              onChange={(e) => setCity(e.target.value)}
              placeholder="Filter by city"
              onKeyDown={(e) => {
                if (e.key === "Enter") applyFilters();
              }}
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
          <div className="filter-actions">
            <button type="button" onClick={applyFilters}>
              Apply filters
            </button>
            <button
              type="button"
              className="secondary"
              onClick={() => {
                setSearch("");
                setCity("");
                setStatus("");
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
          <p className="muted">Loading businesses…</p>
        ) : rows.length === 0 ? (
          <p className="muted">No businesses match your filters.</p>
        ) : (
          <DataTable
            rows={rows}
            columns={[
              { key: "id", label: "ID" },
              {
                key: "title",
                label: "Business",
                render: (row) => (
                  <div className="business-cell">
                    {row.thumbnail_url ? (
                      <img src={row.thumbnail_url} alt="" className="thumb" />
                    ) : (
                      <div className="thumb thumb-empty" />
                    )}
                    <div>
                      <div>{row.title}</div>
                      {row.business_name && row.business_name !== row.title ? (
                        <small className="muted">{row.business_name}</small>
                      ) : null}
                    </div>
                  </div>
                ),
              },
              { key: "city", label: "City" },
              { key: "status", label: "Status" },
              {
                key: "is_featured",
                label: "Featured",
                render: (row) => (row.is_featured ? "Yes" : "No"),
              },
            ]}
            actions={(row) => (
              <button
                type="button"
                onClick={() => navigate(`/businesses/${row.id}`)}
              >
                View
              </button>
            )}
          />
        )}

        <div className="pagination-row">
          <button
            type="button"
            className="secondary"
            disabled={!hasPrev || loading}
            onClick={() => setPage((current) => Math.max(1, current - 1))}
          >
            Previous
          </button>
          <span className="muted">Page {page}</span>
          <button
            type="button"
            className="secondary"
            disabled={!hasNext || loading}
            onClick={() => setPage((current) => current + 1)}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
