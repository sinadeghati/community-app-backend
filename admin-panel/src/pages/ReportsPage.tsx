import { apiFetch } from "../api";
import { ActionPanel, DataTable, StatusBanner, useAdminList } from "./adminShared";

type ReportRow = {
  id: number;
  reported_object_type: string;
  reason: string;
  status: string;
};

export default function ReportsPage() {
  const { rows, count, error, message, runAction } = useAdminList<ReportRow>(
    "/admin/reports/?page_size=25"
  );

  return (
    <div>
      <h1>Moderation / Reports</h1>
      <p className="muted">{count} total</p>
      <StatusBanner error={error} message={message} />
      <ActionPanel>
        <p>Hide reported content or dismiss reports after review.</p>
      </ActionPanel>
      <div className="panel">
        <DataTable
          rows={rows}
          columns={[
            { key: "id", label: "ID" },
            { key: "reported_object_type", label: "Type" },
            { key: "reason", label: "Reason" },
            { key: "status", label: "Status" },
          ]}
          actions={(row) => (
            <>
              <button
                type="button"
                onClick={() =>
                  runAction(`Hid content for report ${row.id}`, () =>
                    apiFetch(`/admin/reports/${row.id}/hide-content/`, { method: "POST" })
                  )
                }
              >
                Hide
              </button>{" "}
              <button
                type="button"
                className="secondary"
                onClick={() =>
                  runAction(`Dismissed report ${row.id}`, () =>
                    apiFetch(`/admin/reports/${row.id}/dismiss/`, { method: "POST" })
                  )
                }
              >
                Dismiss
              </button>
            </>
          )}
        />
      </div>
    </div>
  );
}
