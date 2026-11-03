import { useState } from "react";
import { apiFetch, type Paginated } from "../api";
import { DataTable, StatusBanner, useAdminList } from "./adminShared";

type ReviewRow = {
  id: number;
  business_name: string;
  author_username: string;
  rating: number;
  text: string;
  status: string;
  report_count: number;
  created_at: string;
};

type ReviewReport = {
  id: number;
  reason: string;
  description: string;
  status: string;
  created_at: string;
};

const FILTERS = [
  { value: "", label: "All" },
  { value: "pending", label: "Pending" },
  { value: "approved", label: "Published" },
  { value: "hidden", label: "Hidden" },
  { value: "removed", label: "Removed" },
  { value: "reported", label: "Reported" },
];

const STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  approved: "Published",
  hidden: "Hidden",
  removed: "Removed",
};

function reviewEndpoint(status: string) {
  const params = new URLSearchParams({ page_size: "25" });
  if (status) params.set("status", status);
  return `/admin/reviews/?${params.toString()}`;
}

function ReviewReports({ reviewId, reportCount }: { reviewId: number; reportCount: number }) {
  const [reports, setReports] = useState<ReviewReport[] | null>(null);
  const [error, setError] = useState("");

  if (reportCount === 0) return <span>None</span>;
  if (reports === null && !error) {
    return (
      <button
        type="button"
        className="secondary"
        onClick={() => {
          apiFetch<Paginated<ReviewReport>>(
            `/admin/reports/?object_type=review&object_id=${reviewId}&page_size=25`
          )
            .then((data) => setReports(data.results))
            .catch((e) => setError(e instanceof Error ? e.message : String(e)));
        }}
      >
        View {reportCount}
      </button>
    );
  }
  if (error) return <span className="error">{error}</span>;
  return (
    <ul className="review-reports">
      {(reports || []).map((report) => (
        <li key={report.id}>
          <strong>{report.reason}</strong>
          <div>{report.description || "No details"}</div>
        </li>
      ))}
    </ul>
  );
}

export default function ReviewsModerationPage() {
  const [status, setStatus] = useState("pending");
  const { rows, count, error, message, runAction } = useAdminList<ReviewRow>(
    reviewEndpoint(status)
  );

  const act = (reviewId: number, action: "approve" | "hide" | "remove" | "restore", label: string) => {
    void runAction(label, () =>
      apiFetch(`/admin/reviews/${reviewId}/${action}/`, { method: "POST" })
    );
  };

  return (
    <div>
      <h1>Reviews Moderation</h1>
      <p className="muted">{count} total</p>
      <StatusBanner error={error} message={message} />
      <section className="panel filters-panel">
        <div className="filters-grid">
          <label className="form-field">
            <span>Queue</span>
            <select value={status} onChange={(event) => setStatus(event.target.value)}>
              {FILTERS.map((filter) => (
                <option key={filter.value || "all"} value={filter.value}>
                  {filter.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>
      <div className="panel">
        <DataTable
          rows={rows}
          columns={[
            { key: "business_name", label: "Business" },
            { key: "author_username", label: "Reviewer" },
            { key: "rating", label: "Rating" },
            {
              key: "text",
              label: "Text",
              render: (row) =>
                row.text.length > 160 ? `${row.text.slice(0, 160)}…` : row.text,
            },
            {
              key: "created_at",
              label: "Submitted",
              render: (row) => new Date(row.created_at).toLocaleString(),
            },
            {
              key: "status",
              label: "Status",
              render: (row) => STATUS_LABELS[row.status] || row.status,
            },
            { key: "report_count", label: "Reports" },
            {
              key: "report_detail",
              label: "Report details",
              render: (row) => (
                <ReviewReports reviewId={row.id} reportCount={row.report_count} />
              ),
            },
          ]}
          actions={(row) => (
            <>
              {row.status === "pending" ? (
                <button type="button" onClick={() => act(row.id, "approve", `Approved review ${row.id}`)}>
                  Approve
                </button>
              ) : null}{" "}
              {row.status !== "hidden" ? (
                <button type="button" className="secondary" onClick={() => act(row.id, "hide", `Hid review ${row.id}`)}>
                  Hide
                </button>
              ) : null}{" "}
              {row.status !== "removed" ? (
                <button type="button" className="danger" onClick={() => act(row.id, "remove", `Removed review ${row.id}`)}>
                  Remove
                </button>
              ) : null}{" "}
              {row.status === "hidden" || row.status === "removed" ? (
                <button type="button" onClick={() => act(row.id, "restore", `Restored review ${row.id}`)}>
                  Restore
                </button>
              ) : null}
            </>
          )}
        />
      </div>
    </div>
  );
}
