import { useState } from "react";
import { apiFetch } from "../api";
import { ActionPanel, DataTable, StatusBanner, useAdminList } from "./adminShared";

type BusinessRow = {
  id: number;
  title: string;
  city: string;
  status: string;
  is_featured: boolean;
};

export default function BusinessesPage() {
  const { rows, count, error, message, runAction } = useAdminList<BusinessRow>(
    "/admin/businesses/?page_size=25"
  );
  const [businessId, setBusinessId] = useState("");
  const [title, setTitle] = useState("Staging Demo Business");
  const [ownerId, setOwnerId] = useState("2");
  const [editTitle, setEditTitle] = useState("Updated Demo Business");

  return (
    <div>
      <h1>Businesses</h1>
      <p className="muted">{count} total</p>
      <StatusBanner error={error} message={message} />
      <ActionPanel>
        <h3>Create business</h3>
        <div className="row">
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Title" />
          <input value={ownerId} onChange={(e) => setOwnerId(e.target.value)} placeholder="Owner user ID" />
          <button
            type="button"
            onClick={() =>
              runAction("Business created", () =>
                apiFetch("/admin/businesses/", {
                  method: "POST",
                  body: JSON.stringify({
                    title,
                    business_name: title,
                    city: "Los Angeles",
                    state: "CA",
                    contact_info: "demo@korook.com",
                    category: "Restaurant",
                    owner_id: Number(ownerId),
                  }),
                })
              )
            }
          >
            Create
          </button>
        </div>
        <h3>Edit / hide</h3>
        <div className="row">
          <input value={businessId} onChange={(e) => setBusinessId(e.target.value)} placeholder="Business ID" />
          <input value={editTitle} onChange={(e) => setEditTitle(e.target.value)} placeholder="New title" />
          <button
            type="button"
            onClick={() =>
              runAction("Business updated", () =>
                apiFetch(`/admin/businesses/${businessId}/`, {
                  method: "PATCH",
                  body: JSON.stringify({ title: editTitle, business_name: editTitle }),
                })
              )
            }
          >
            Edit
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() =>
              runAction("Business hidden", () =>
                apiFetch(`/admin/businesses/${businessId}/hide/`, { method: "POST" })
              )
            }
          >
            Hide
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() =>
              runAction("Business published", () =>
                apiFetch(`/admin/businesses/${businessId}/publish/`, { method: "POST" })
              )
            }
          >
            Publish
          </button>
        </div>
      </ActionPanel>
      <div className="panel">
        <DataTable
          rows={rows}
          columns={[
            { key: "id", label: "ID" },
            { key: "title", label: "Title" },
            { key: "city", label: "City" },
            { key: "status", label: "Status" },
            { key: "is_featured", label: "Featured" },
          ]}
          actions={(row) => (
            <button type="button" onClick={() => setBusinessId(String(row.id))}>
              Select
            </button>
          )}
        />
      </div>
    </div>
  );
}
