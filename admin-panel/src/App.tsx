import { Link, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { apiFetch, ensureCsrf, type Claim, type DashboardStats, type Paginated } from "./api";
import LoginPage from "./pages/LoginPage";

const NAV = [
  ["Dashboard", "/"],
  ["Users", "/users"],
  ["Businesses", "/businesses"],
  ["Events", "/events"],
  ["Promotions", "/promotions"],
  ["Claims", "/claims"],
  ["Reports", "/reports"],
  ["Media", "/media"],
  ["Audit Log", "/audit-log"],
];

function Shell({ children, onLogout }: { children: React.ReactNode; onLogout: () => void }) {
  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">Korook Admin</div>
        <nav>
          {NAV.map(([label, path]) => (
            <Link key={path} to={path}>{label}</Link>
          ))}
        </nav>
        <button className="logout" onClick={onLogout}>Logout</button>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
}

function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      apiFetch<DashboardStats>("/admin/dashboard/stats/"),
      apiFetch<Paginated<Claim>>("/admin/claims/?page_size=5"),
    ])
      .then(([s, c]) => {
        setStats(s);
        setClaims(c.results);
      })
      .catch((e) => setError(String(e.message || e)));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!stats) return <p>Loading dashboard…</p>;

  const cards = [
    ["Users", stats.users_total],
    ["Businesses", stats.businesses_total],
    ["Events", stats.events_total],
    ["Pending Claims", stats.claims_pending],
    ["Open Reports", stats.reports_open],
    ["Active Promotions", stats.promotions_active],
    ["Premium Listings", stats.premium_active],
    ["Media Review", stats.media_pending_review],
  ];

  return (
    <div>
      <h1>Dashboard</h1>
      <div className="kpi-grid">
        {cards.map(([label, value]) => (
          <div key={label} className="kpi-card">
            <div className="kpi-label">{label}</div>
            <div className="kpi-value">{value}</div>
          </div>
        ))}
      </div>
      <section className="panel">
        <h2>Claim Queue</h2>
        {claims.length === 0 ? (
          <p>No pending claims.</p>
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
              {claims.map((c) => (
                <tr key={c.id}>
                  <td>{c.id}</td>
                  <td>{c.listing_title}</td>
                  <td>{c.requester_username}</td>
                  <td>{c.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

import AdminListPage from "./pages/AdminListPage";

function Placeholder({ title }: { title: string }) {
  return <div><h1>{title}</h1><p>Phase 1 shell — API wired; detailed UI next.</p></div>;
}

export default function App() {
  const [user, setUser] = useState<{ username: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    ensureCsrf()
      .then(() => apiFetch<{ username: string }>("/admin/auth/me/"))
      .then((me) => setUser(me))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const logout = async () => {
    await apiFetch("/admin/auth/logout/", { method: "POST" });
    setUser(null);
    navigate("/login");
  };

  if (loading) return <p className="center">Loading…</p>;

  return (
    <Routes>
      <Route path="/login" element={
        user ? <Navigate to="/" /> : <LoginPage onLogin={(u) => { setUser(u); navigate("/"); }} />
      } />
      <Route path="/*" element={
        user ? (
          <Shell onLogout={logout}>
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/users" element={
                <AdminListPage title="Users" endpoint="/admin/users/?page_size=25"
                  columns={[
                    { key: "id", label: "ID" },
                    { key: "username", label: "Username" },
                    { key: "email", label: "Email" },
                    { key: "role", label: "Role" },
                    { key: "account_status", label: "Status" },
                  ]} />
              } />
              <Route path="/businesses" element={
                <AdminListPage title="Businesses" endpoint="/admin/businesses/?page_size=25"
                  columns={[
                    { key: "id", label: "ID" },
                    { key: "title", label: "Title" },
                    { key: "city", label: "City" },
                    { key: "status", label: "Status" },
                    { key: "is_featured", label: "Featured" },
                  ]} />
              } />
              <Route path="/events" element={
                <AdminListPage title="Events" endpoint="/admin/events/?page_size=25"
                  columns={[
                    { key: "id", label: "ID" },
                    { key: "title", label: "Title" },
                    { key: "starts_at", label: "Starts" },
                    { key: "status", label: "Status" },
                  ]} />
              } />
              <Route path="/promotions" element={
                <AdminListPage title="Promotions / Hero Ads" endpoint="/admin/promotions/?page_size=25"
                  columns={[
                    { key: "id", label: "ID" },
                    { key: "title", label: "Title" },
                    { key: "placement", label: "Placement" },
                    { key: "status", label: "Status" },
                    { key: "advertiser_name", label: "Advertiser" },
                  ]} />
              } />
              <Route path="/claims" element={
                <AdminListPage title="Claims" endpoint="/admin/claims/?status=all&page_size=25"
                  columns={[
                    { key: "id", label: "ID" },
                    { key: "listing_title", label: "Business" },
                    { key: "requester_username", label: "Requester" },
                    { key: "status", label: "Status" },
                  ]} />
              } />
              <Route path="/reports" element={
                <AdminListPage title="Moderation / Reports" endpoint="/admin/reports/?page_size=25"
                  columns={[
                    { key: "id", label: "ID" },
                    { key: "reported_object_type", label: "Type" },
                    { key: "reason", label: "Reason" },
                    { key: "status", label: "Status" },
                  ]} />
              } />
              <Route path="/media" element={<Placeholder title="Media Review" />} />
              <Route path="/audit-log" element={<Placeholder title="Audit Log" />} />
            </Routes>
          </Shell>
        ) : <Navigate to="/login" />
      } />
    </Routes>
  );
}
