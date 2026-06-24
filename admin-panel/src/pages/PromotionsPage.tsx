import { useState } from "react";
import { apiFetch } from "../api";
import { ActionPanel, DataTable, StatusBanner, useAdminList } from "./adminShared";

type PromoRow = {
  id: number;
  title: string;
  placement: string;
  status: string;
  advertiser_name: string;
};

export default function PromotionsPage() {
  const { rows, count, error, message, runAction } = useAdminList<PromoRow>(
    "/admin/promotions/?page_size=25"
  );
  const [title, setTitle] = useState("Korook Staging Hero");

  return (
    <div>
      <h1>Promotions / Hero Ads</h1>
      <p className="muted">{count} total</p>
      <StatusBanner error={error} message={message} />
      <ActionPanel>
        <h3>Create hero banner</h3>
        <div className="row">
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Title" />
          <button
            type="button"
            onClick={() =>
              runAction("Hero banner created", () =>
                apiFetch("/admin/promotions/", {
                  method: "POST",
                  body: JSON.stringify({
                    advertiser_name: "Korook",
                    placement: "home_hero",
                    title,
                    subtitle: "Persian community near you",
                    cta_text: "Explore",
                    cta_link: "https://korook.com",
                    channel: "curated_event",
                    is_active: true,
                    hero_approved: true,
                    status: "active",
                    display_priority: 1,
                  }),
                })
              )
            }
          >
            Create hero banner
          </button>
        </div>
      </ActionPanel>
      <div className="panel">
        <DataTable
          rows={rows}
          columns={[
            { key: "id", label: "ID" },
            { key: "title", label: "Title" },
            { key: "placement", label: "Placement" },
            { key: "status", label: "Status" },
            { key: "advertiser_name", label: "Advertiser" },
          ]}
        />
      </div>
    </div>
  );
}
