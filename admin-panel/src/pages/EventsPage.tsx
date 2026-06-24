import { useState } from "react";
import { apiFetch } from "../api";
import { ActionPanel, DataTable, StatusBanner, useAdminList } from "./adminShared";

type EventRow = {
  id: number;
  title: string;
  starts_at: string;
  status: string;
};

export default function EventsPage() {
  const { rows, count, error, message, runAction } = useAdminList<EventRow>(
    "/admin/events/?page_size=25"
  );
  const [title, setTitle] = useState("Staging Community Night");
  const [ownerId, setOwnerId] = useState("2");

  const startsAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString();

  return (
    <div>
      <h1>Events</h1>
      <p className="muted">{count} total</p>
      <StatusBanner error={error} message={message} />
      <ActionPanel>
        <h3>Create event</h3>
        <div className="row">
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Title" />
          <input value={ownerId} onChange={(e) => setOwnerId(e.target.value)} placeholder="Owner user ID" />
          <button
            type="button"
            onClick={() =>
              runAction("Event created", () =>
                apiFetch("/admin/events/", {
                  method: "POST",
                  body: JSON.stringify({
                    title,
                    description: "Created from admin staging UI",
                    category: "Community",
                    starts_at: startsAt,
                    city: "Los Angeles",
                    state: "CA",
                    owner_id: Number(ownerId),
                    status: "published",
                  }),
                })
              )
            }
          >
            Create event
          </button>
        </div>
      </ActionPanel>
      <div className="panel">
        <DataTable
          rows={rows}
          columns={[
            { key: "id", label: "ID" },
            { key: "title", label: "Title" },
            { key: "starts_at", label: "Starts" },
            { key: "status", label: "Status" },
          ]}
        />
      </div>
    </div>
  );
}
