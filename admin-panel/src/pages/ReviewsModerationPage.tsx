import { useEffect, useRef, useState, type KeyboardEvent } from "react";
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

function QueueSelect({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const selectedIndex = Math.max(0, FILTERS.findIndex((filter) => filter.value === value));
  const selected = FILTERS[selectedIndex];

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  const openMenu = () => {
    setActiveIndex(selectedIndex);
    setOpen(true);
  };

  const choose = (index: number) => {
    const filter = FILTERS[index];
    if (!filter) return;
    onChange(filter.value);
    setOpen(false);
    triggerRef.current?.focus();
  };

  const onMenuKeyDown = (event: KeyboardEvent<HTMLUListElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      setOpen(false);
      triggerRef.current?.focus();
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((index) => (index + 1) % FILTERS.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((index) => (index - 1 + FILTERS.length) % FILTERS.length);
    } else if (event.key === "Home") {
      event.preventDefault();
      setActiveIndex(0);
    } else if (event.key === "End") {
      event.preventDefault();
      setActiveIndex(FILTERS.length - 1);
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      choose(activeIndex);
    }
  };

  return (
    <div className="queue-select" ref={rootRef}>
      <button
        ref={triggerRef}
        type="button"
        className="queue-select-trigger"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls="review-queue-listbox"
        onClick={() => (open ? setOpen(false) : openMenu())}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" || event.key === "ArrowUp" || event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            openMenu();
          }
        }}
      >
        {selected.label}
      </button>
      {open ? (
        <ul
          id="review-queue-listbox"
          className="queue-select-menu"
          role="listbox"
          aria-label="Queue"
          tabIndex={-1}
          autoFocus
          onKeyDown={onMenuKeyDown}
        >
          {FILTERS.map((filter, index) => (
            <li key={filter.value || "all"} role="presentation">
              <button
                type="button"
                role="option"
                aria-selected={filter.value === value}
                className={index === activeIndex ? "is-active" : undefined}
                onMouseEnter={() => setActiveIndex(index)}
                onClick={() => choose(index)}
              >
                {filter.label}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

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
            <QueueSelect value={status} onChange={setStatus} />
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
