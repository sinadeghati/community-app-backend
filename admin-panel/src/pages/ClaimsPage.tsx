import { apiFetch } from "../api";
import { ActionPanel, DataTable, StatusBanner, useAdminList } from "./adminShared";

type ClaimRow = {
  id: number;
  listing_title: string;
  requester_username: string;
  status: string;
};

export default function ClaimsPage() {
  const { rows, count, error, message, runAction } = useAdminList<ClaimRow>(
    "/admin/claims/?status=all&page_size=25"
  );

  return (
    <div>
      <h1>Claims Queue</h1>
      <p className="muted">{count} total</p>
      <StatusBanner error={error} message={message} />
      <ActionPanel>
        <p>Approve or reject pending ownership claims from the table below.</p>
      </ActionPanel>
      <div className="panel">
        <DataTable
          rows={rows}
          columns={[
            { key: "id", label: "ID" },
            { key: "listing_title", label: "Business" },
            { key: "requester_username", label: "Requester" },
            { key: "status", label: "Status" },
          ]}
          actions={(row) =>
            row.status === "pending" ? (
              <>
                <button
                  type="button"
                  onClick={() =>
                    runAction(`Approved claim ${row.id}`, () =>
                      apiFetch(`/admin/claims/${row.id}/approve/`, { method: "POST" })
                    )
                  }
                >
                  Approve
                </button>{" "}
                <button
                  type="button"
                  className="secondary"
                  onClick={() =>
                    runAction(`Rejected claim ${row.id}`, () =>
                      apiFetch(`/admin/claims/${row.id}/reject/`, {
                        method: "POST",
                        body: JSON.stringify({ admin_note: "Rejected in staging QA" }),
                      })
                    )
                  }
                >
                  Reject
                </button>
              </>
            ) : (
              <span className="muted">—</span>
            )
          }
        />
      </div>
    </div>
  );
}
