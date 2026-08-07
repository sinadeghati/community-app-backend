import { Link, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { apiFetch, ensureCsrf, type Claim, type DashboardStats, type Paginated } from "./api";
import LoginPage from "./pages/LoginPage";
import UsersListPage from "./pages/users/UsersListPage";
import UserDetailPage from "./pages/users/UserDetailPage";
import BusinessesListPage from "./pages/businesses/BusinessesListPage";
import BusinessCreatePage from "./pages/businesses/BusinessCreatePage";
import BusinessDetailPage from "./pages/businesses/BusinessDetailPage";
import EventsListPage from "./pages/events/EventsListPage";
import EventCreatePage from "./pages/events/EventCreatePage";
import EventDetailPage from "./pages/events/EventDetailPage";
import PromotionsPage from "./pages/PromotionsPage";
import ClaimsPage from "./pages/ClaimsPage";
import ReportsPage from "./pages/ReportsPage";

const NAV = [
  ["Dashboard", "/"],
  ["Users", "/users"],
  ["Businesses", "/businesses"],
  ["Events", "/events"],
  ["Promotions", "/promotions"],
  ["Claims", "/claims"],
  ["Reports", "/reports"],
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
              <Route path="/users/:id" element={<UserDetailPage />} />
              <Route path="/users" element={<UsersListPage />} />
              <Route path="/businesses/new" element={<BusinessCreatePage />} />
              <Route path="/businesses/:id" element={<BusinessDetailPage />} />
              <Route path="/businesses" element={<BusinessesListPage />} />
              <Route path="/events/new" element={<EventCreatePage />} />
              <Route path="/events/:id" element={<EventDetailPage />} />
              <Route path="/events" element={<EventsListPage />} />
              <Route path="/promotions" element={<PromotionsPage />} />
              <Route path="/claims" element={<ClaimsPage />} />
              <Route path="/reports" element={<ReportsPage />} />
            </Routes>
          </Shell>
        ) : <Navigate to="/login" />
      } />
    </Routes>
  );
}
