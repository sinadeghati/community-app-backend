import { Link, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { apiFetch, type Paginated } from "../../api";
import { StatusBanner } from "../adminShared";
import {
  formatDate,
  statusBadgeClass,
  type UserBusinessSummary,
  type UserClaimSummary,
  type UserDetail,
  type UserEventSummary,
  type UserReportSummary,
} from "./types";

type ConfirmAction = "suspend" | "unsuspend" | null;

export default function UserDetailPage() {
  const { id } = useParams();
  const userId = Number(id);
  const [user, setUser] = useState<UserDetail | null>(null);
  const [businesses, setBusinesses] = useState<UserBusinessSummary[]>([]);
  const [events, setEvents] = useState<UserEventSummary[]>([]);
  const [claims, setClaims] = useState<UserClaimSummary[]>([]);
  const [reports, setReports] = useState<UserReportSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [confirmAction, setConfirmAction] = useState<ConfirmAction>(null);
  const [adminNote, setAdminNote] = useState("");

  const loadUser = () => {
    if (!userId) {
      setError("Invalid user ID.");
      setLoading(false);
      return Promise.resolve();
    }
    setLoading(true);
    setError("");
    return Promise.all([
      apiFetch<UserDetail>(`/admin/users/${userId}/`),
      apiFetch<Paginated<UserBusinessSummary>>(`/admin/users/${userId}/businesses/?page_size=10`),
      apiFetch<Paginated<UserEventSummary>>(`/admin/users/${userId}/events/?page_size=10`),
      apiFetch<Paginated<UserClaimSummary>>(`/admin/users/${userId}/claims/?page_size=10`),
      apiFetch<Paginated<UserReportSummary>>(`/admin/users/${userId}/reports/?page_size=10`),
    ])
      .then(([detail, biz, ev, cl, rep]) => {
        setUser(detail);
        setAdminNote(detail.admin_note || "");
        setBusinesses(biz.results);
        setEvents(ev.results);
        setClaims(cl.results);
        setReports(rep.results);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadUser();
  }, [userId]);

  const runAction = async (label: string, fn: () => Promise<unknown>) => {
    setActionLoading(true);
    setError("");
    setMessage("");
    try {
      await fn();
      setMessage(label);
      setConfirmAction(null);
      await loadUser();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setConfirmAction(null);
    } finally {
      setActionLoading(false);
    }
  };

  const saveAdminNote = async () => {
    if (!user || actionLoading) return;
    await runAction("Admin note saved.", () =>
      apiFetch(`/admin/users/${user.id}/`, {
        method: "PATCH",
        body: JSON.stringify({ admin_note: adminNote }),
      })
    );
  };

  if (loading) {
    return <p className="muted">Loading user…</p>;
  }

  if (!user) {
    return (
      <div>
        <Link to="/users" className="back-link">← Back to users</Link>
        <p className="error">{error || "User not found."}</p>
      </div>
    );
  }

  const isSuspended = user.account_status === "suspended";
  const isProtected = user.is_staff || user.is_superuser;

  return (
    <div>
      <div className="page-header">
        <div>
          <Link to="/users" className="back-link">← Back to users</Link>
          <h1>{user.display_name}</h1>
          <div className="badge-row">
            <span className="badge">ID {user.id}</span>
            <span className={statusBadgeClass(user.account_status)}>{user.account_status}</span>
            <span className={user.email_verified ? "badge success" : "badge warning"}>
              {user.email_verified ? "Email verified" : "Email unverified"}
            </span>
            {user.is_staff ? <span className="badge accent">Staff</span> : null}
            {user.is_superuser ? <span className="badge accent">Superuser</span> : null}
          </div>
        </div>
      </div>

      <StatusBanner error={error} message={message} />

      <section className="panel detail-meta">
        <h2>Account overview</h2>
        <dl className="meta-grid">
          <div><dt>Username</dt><dd>{user.username}</dd></div>
          <div><dt>Email</dt><dd>{user.email}</dd></div>
          <div><dt>Role</dt><dd>{user.role}</dd></div>
          <div><dt>Active login</dt><dd>{user.is_active ? "Yes" : "No"}</dd></div>
          <div><dt>Joined</dt><dd>{formatDate(user.date_joined)}</dd></div>
          <div><dt>Last login</dt><dd>{formatDate(user.last_login)}</dd></div>
          <div><dt>Suspended at</dt><dd>{formatDate(user.suspended_at)}</dd></div>
          <div><dt>Suspended by</dt><dd>{user.suspended_by_username || "—"}</dd></div>
          <div><dt>Businesses linked</dt><dd>{user.businesses_count ?? 0}</dd></div>
          <div><dt>Events created</dt><dd>{user.events_count}</dd></div>
          <div><dt>Claims submitted</dt><dd>{user.claims_count}</dd></div>
          <div><dt>Reports against</dt><dd>{user.reports_count}</dd></div>
        </dl>
      </section>

      <section className="panel">
        <h2>Admin note</h2>
        <label className="form-field span-2">
          <span>Internal note</span>
          <textarea
            rows={3}
            value={adminNote}
            onChange={(e) => setAdminNote(e.target.value)}
          />
        </label>
        <div className="form-actions">
          <button type="button" disabled={actionLoading} onClick={saveAdminNote}>
            {actionLoading ? "Saving…" : "Save note"}
          </button>
        </div>
      </section>

      <RelatedSection
        title="Businesses"
        empty="No linked businesses."
        columns={["ID", "Business", "City", "Status"]}
        hasItems={businesses.length > 0}
      >
        {businesses.map((item) => (
          <tr key={item.id}>
            <td>{item.id}</td>
            <td>
              <Link to={`/businesses/${item.id}`}>{item.title}</Link>
            </td>
            <td>{item.city}</td>
            <td><span className={statusBadgeClass(item.status)}>{item.status}</span></td>
          </tr>
        ))}
      </RelatedSection>

      <RelatedSection
        title="Events"
        empty="No events created."
        columns={["ID", "Event", "City", "Status", "Starts"]}
        hasItems={events.length > 0}
      >
        {events.map((item) => (
          <tr key={item.id}>
            <td>{item.id}</td>
            <td>{item.title}</td>
            <td>{item.city}</td>
            <td><span className={statusBadgeClass(item.status)}>{item.status}</span></td>
            <td>{formatDate(item.starts_at)}</td>
          </tr>
        ))}
      </RelatedSection>

      <RelatedSection
        title="Claims submitted"
        empty="No claims submitted."
        columns={["ID", "Business", "Status", "Submitted"]}
        hasItems={claims.length > 0}
      >
        {claims.map((item) => (
          <tr key={item.id}>
            <td>{item.id}</td>
            <td>
              <Link to={`/businesses/${item.listing}`}>{item.listing_title}</Link>
            </td>
            <td><span className={statusBadgeClass(item.status)}>{item.status}</span></td>
            <td>{formatDate(item.created_at)}</td>
          </tr>
        ))}
      </RelatedSection>

      <RelatedSection
        title="Reports against user"
        empty="No reports against this user."
        columns={["ID", "Type", "Reason", "Status", "Created"]}
        hasItems={reports.length > 0}
      >
        {reports.map((item) => (
          <tr key={item.id}>
            <td>{item.id}</td>
            <td>{item.reported_object_type}</td>
            <td>{item.reason}</td>
            <td><span className={statusBadgeClass(item.status)}>{item.status}</span></td>
            <td>{formatDate(item.created_at)}</td>
          </tr>
        ))}
      </RelatedSection>

      <section className="panel actions-panel">
        <h2>Account actions</h2>
        <div className="row">
          {!isSuspended ? (
            <button
              type="button"
              className="danger"
              disabled={actionLoading || isProtected}
              onClick={() => setConfirmAction("suspend")}
            >
              Suspend user
            </button>
          ) : (
            <button
              type="button"
              disabled={actionLoading}
              onClick={() => setConfirmAction("unsuspend")}
            >
              Unsuspend user
            </button>
          )}
          {!user.email_verified ? (
            <button
              type="button"
              className="secondary"
              disabled={actionLoading}
              onClick={() =>
                runAction("Email verified.", () =>
                  apiFetch(`/admin/users/${user.id}/verify-email/`, { method: "POST" })
                )
              }
            >
              Verify email
            </button>
          ) : (
            <button
              type="button"
              className="secondary"
              disabled={actionLoading}
              onClick={() =>
                runAction("Email verification removed.", () =>
                  apiFetch(`/admin/users/${user.id}/unverify-email/`, { method: "POST" })
                )
              }
            >
              Remove verification
            </button>
          )}
        </div>
        {isProtected ? (
          <p className="muted phase-note">
            Staff and superuser accounts cannot be suspended from this panel.
          </p>
        ) : null}
        <p className="muted phase-note">
          Delete user is not available in this release. Deleting accounts would cascade-remove
          listings, events, and claims tied to the user. A safe ownership transfer or soft-delete
          strategy is required before delete can be enabled.
        </p>
      </section>

      {confirmAction ? (
        <div className="modal-backdrop">
          <div className="modal-card" role="dialog" aria-modal="true">
            <h3>{confirmAction === "suspend" ? "Suspend user?" : "Unsuspend user?"}</h3>
            <p>
              {confirmAction === "suspend" ? (
                <>
                  This will suspend <strong>{user.display_name}</strong> ({user.email}) and
                  prevent them from signing in.
                </>
              ) : (
                <>
                  This will restore access for <strong>{user.display_name}</strong> ({user.email}).
                </>
              )}
            </p>
            <div className="modal-actions">
              <button
                type="button"
                className="secondary"
                onClick={() => setConfirmAction(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className={confirmAction === "suspend" ? "danger" : undefined}
                disabled={actionLoading}
                onClick={() =>
                  runAction(
                    confirmAction === "suspend" ? "User suspended." : "User unsuspended.",
                    () =>
                      apiFetch(`/admin/users/${user.id}/${confirmAction}/`, { method: "POST" })
                  )
                }
              >
                {actionLoading
                  ? "Working…"
                  : confirmAction === "suspend"
                    ? "Suspend"
                    : "Unsuspend"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function RelatedSection({
  title,
  empty,
  columns,
  hasItems,
  children,
}: {
  title: string;
  empty: string;
  columns: string[];
  hasItems: boolean;
  children: React.ReactNode;
}) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      {!hasItems ? (
        <p className="muted">{empty}</p>
      ) : (
        <table>
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>{children}</tbody>
        </table>
      )}
    </section>
  );
}
