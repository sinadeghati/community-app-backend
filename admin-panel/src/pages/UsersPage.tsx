import { useState } from "react";
import { apiFetch } from "../api";
import { ActionPanel, DataTable, StatusBanner, useAdminList } from "./adminShared";

type UserRow = {
  id: number;
  username: string;
  email: string;
  role: string;
  account_status: string;
};

export default function UsersPage() {
  const { rows, count, error, message, runAction } = useAdminList<UserRow>(
    "/admin/users/?page_size=25"
  );
  const [userId, setUserId] = useState("");

  return (
    <div>
      <h1>Users</h1>
      <p className="muted">{count} total</p>
      <StatusBanner error={error} message={message} />
      <ActionPanel>
        <h3>Suspend user</h3>
        <div className="row">
          <input
            placeholder="User ID"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
          />
          <button
            type="button"
            onClick={() =>
              runAction(`Suspended user ${userId}`, () =>
                apiFetch(`/admin/users/${userId}/suspend/`, { method: "POST" })
              )
            }
          >
            Suspend
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() =>
              runAction(`Unsuspended user ${userId}`, () =>
                apiFetch(`/admin/users/${userId}/unsuspend/`, { method: "POST" })
              )
            }
          >
            Unsuspend
          </button>
        </div>
      </ActionPanel>
      <div className="panel">
        <DataTable
          rows={rows}
          columns={[
            { key: "id", label: "ID" },
            { key: "username", label: "Username" },
            { key: "email", label: "Email" },
            { key: "role", label: "Role" },
            { key: "account_status", label: "Status" },
          ]}
          actions={(row) => (
            <button type="button" onClick={() => setUserId(String(row.id))}>
              Select
            </button>
          )}
        />
      </div>
    </div>
  );
}
