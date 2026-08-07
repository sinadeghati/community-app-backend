import { useNavigate } from "react-router-dom";
import { useCallback, useEffect, useState } from "react";
import { apiFetch, type Paginated } from "../../api";
import { DataTable, StatusBanner } from "../adminShared";
import {
  ACCOUNT_STATUS_OPTIONS,
  EMAIL_VERIFIED_OPTIONS,
  buildUsersListEndpoint,
  formatDate,
  statusBadgeClass,
  type UserListRow,
} from "./types";

export default function UsersListPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [accountStatus, setAccountStatus] = useState("");
  const [emailVerified, setEmailVerified] = useState("");
  const [page, setPage] = useState(1);
  const [rows, setRows] = useState<UserListRow[]>([]);
  const [count, setCount] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [hasPrev, setHasPrev] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    return apiFetch<Paginated<UserListRow>>(
      buildUsersListEndpoint({ page, search, accountStatus, emailVerified })
    )
      .then((data) => {
        setRows(data.results);
        setCount(data.count);
        setHasNext(Boolean(data.next));
        setHasPrev(Boolean(data.previous));
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [page, search, accountStatus, emailVerified]);

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
          <h1>Users</h1>
          <p className="muted">{count} total accounts</p>
        </div>
      </div>

      <StatusBanner error={error} message="" />

      <section className="panel filters-panel">
        <div className="filters-grid">
          <label className="form-field">
            <span>Search name, email, or username</span>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search users"
              onKeyDown={(e) => {
                if (e.key === "Enter") applyFilters();
              }}
            />
          </label>
          <label className="form-field">
            <span>Account status</span>
            <select
              value={accountStatus}
              onChange={(e) => setAccountStatus(e.target.value)}
            >
              {ACCOUNT_STATUS_OPTIONS.map((option) => (
                <option key={option.value || "all"} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field">
            <span>Email verification</span>
            <select
              value={emailVerified}
              onChange={(e) => setEmailVerified(e.target.value)}
            >
              {EMAIL_VERIFIED_OPTIONS.map((option) => (
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
                setAccountStatus("");
                setEmailVerified("");
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
          <p className="muted">Loading users…</p>
        ) : rows.length === 0 ? (
          <p className="muted">No users match your filters.</p>
        ) : (
          <DataTable
            rows={rows}
            columns={[
              { key: "id", label: "ID" },
              {
                key: "display_name",
                label: "User",
                render: (row) => (
                  <div>
                    <div>{row.display_name}</div>
                    <small className="muted">@{row.username}</small>
                  </div>
                ),
              },
              { key: "email", label: "Email" },
              {
                key: "account_status",
                label: "Status",
                render: (row) => (
                  <span className={statusBadgeClass(row.account_status)}>
                    {row.account_status}
                  </span>
                ),
              },
              {
                key: "is_active",
                label: "Active",
                render: (row) => (row.is_active ? "Yes" : "No"),
              },
              {
                key: "email_verified",
                label: "Verified",
                render: (row) => (
                  <span className={row.email_verified ? "badge success" : "badge warning"}>
                    {row.email_verified ? "Verified" : "Unverified"}
                  </span>
                ),
              },
              {
                key: "businesses_count",
                label: "Businesses",
                render: (row) => row.businesses_count ?? 0,
              },
              {
                key: "date_joined",
                label: "Joined",
                render: (row) => formatDate(row.date_joined),
              },
              {
                key: "last_login",
                label: "Last login",
                render: (row) => formatDate(row.last_login),
              },
            ]}
            actions={(row) => (
              <button type="button" onClick={() => navigate(`/users/${row.id}`)}>
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
