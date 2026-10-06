import { apiFetch } from "../api";
import { ActionPanel, DataTable, StatusBanner, useAdminList } from "./adminShared";

type ClaimRow = {
  id: number;
  listing_title: string;
  requester_username: string;
  claimant_name: string;
  relationship_role: string;
  contact_email: string;
  contact_phone: string;
  verification_message: string;
  status: string;
  created_at: string;
};

function confirmAction(message: string): boolean {
  return window.confirm(message);
}

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
        <p>
          Review ownership requests. Approving links the business to the
          requester&apos;s existing Korook account. Rejecting does not change
          the current owner.
        </p>
      </ActionPanel>
      <div className="panel">
        <DataTable
          rows={rows}
          columns={[
            { key: "id", label: "ID" },
            { key: "listing_title", label: "Business" },
            { key: "requester_username", label: "Korook user" },
            { key: "claimant_name", label: "Claimant name" },
            { key: "relationship_role", label: "Role" },
            { key: "contact_email", label: "Email" },
            { key: "contact_phone", label: "Phone" },
            { key: "status", label: "Status" },
            { key: "created_at", label: "Submitted" },
            {
              key: "verification_message",
              label: "Verification",
              render: (row) =>
                row.verification_message
                  ? String(row.verification_message).slice(0, 120) +
                    (String(row.verification_message).length > 120 ? "…" : "")
                  : "—",
            },
          ]}
          actions={(row) =>
            row.status === "pending" ? (
              <>
                <button
                  type="button"
                  onClick={() => {
                    if (
                      !confirmAction(
                        `Approve claim #${row.id} for "${row.listing_title}" and assign ownership to ${row.requester_username}?`
                      )
                    ) {
                      return;
                    }
                    void runAction(`Approved claim ${row.id}`, () =>
                      apiFetch(`/admin/claims/${row.id}/approve/`, { method: "POST" })
                    );
                  }}
                >
                  Approve
                </button>{" "}
                <button
                  type="button"
                  className="secondary"
                  onClick={() => {
                    if (
                      !confirmAction(
                        `Reject claim #${row.id} for "${row.listing_title}"? The business owner will not change.`
                      )
                    ) {
                      return;
                    }
                    void runAction(`Rejected claim ${row.id}`, () =>
                      apiFetch(`/admin/claims/${row.id}/reject/`, {
                        method: "POST",
                        body: JSON.stringify({ admin_note: "Rejected in admin review" }),
                      })
                    );
                  }}
                >
                  Reject
                </button>
              </>
            ) : (
              <span className="muted">Processed</span>
            )
          }
        />
      </div>
    </div>
  );
}
