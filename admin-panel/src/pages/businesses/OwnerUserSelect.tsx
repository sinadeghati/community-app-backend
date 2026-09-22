import { useEffect, useState } from "react";
import { apiFetch, type Paginated } from "../../api";

export type OwnerUserRow = {
  id: number;
  username: string;
  email: string;
  display_name: string;
};

type Props = {
  value: string;
  onChange: (ownerId: string) => void;
  error?: string;
};

function displayUser(row: OwnerUserRow): string {
  const name = row.display_name?.trim();
  if (name) return `${name} (${row.email || row.username})`;
  return row.email || row.username;
}

export default function OwnerUserSelect({ value, onChange, error }: Props) {
  const [search, setSearch] = useState("");
  const [rows, setRows] = useState<OwnerUserRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    if (!value || value === "unclaimed") return;
    const selectedId = Number(value);
    if (!selectedId) return;
    apiFetch<OwnerUserRow>(`/admin/users/${selectedId}/`)
      .then((user) => setSearch(displayUser(user)))
      .catch(() => undefined);
  }, [value]);

  useEffect(() => {
    if (!search.trim()) {
      setRows([]);
      return;
    }
    const timer = window.setTimeout(() => {
      setLoading(true);
      setLoadError("");
      const qs = new URLSearchParams();
      qs.set("page_size", "8");
      qs.set("search", search.trim());
      apiFetch<Paginated<OwnerUserRow>>(`/admin/users/?${qs.toString()}`)
        .then((data) => setRows(data.results))
        .catch((e) => setLoadError(e instanceof Error ? e.message : String(e)))
        .finally(() => setLoading(false));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [search]);

  return (
    <div className="form-field span-2 owner-user-select">
      <span>Owner</span>
      <div className="owner-choice">
        <label className="checkbox-field">
          <input
            type="radio"
            name="owner-mode"
            checked={!value || value === "unclaimed"}
            onChange={() => onChange("unclaimed")}
          />
          <span>No owner — Unclaimed</span>
        </label>
        <label className="checkbox-field">
          <input
            type="radio"
            name="owner-mode"
            checked={Boolean(value && value !== "unclaimed")}
            onChange={() => onChange(value && value !== "unclaimed" ? value : "")}
          />
          <span>Assign existing user</span>
        </label>
      </div>
      {value && value !== "unclaimed" ? (
        <>
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search by name, email, or username"
          />
          {loadError ? <small className="field-error">{loadError}</small> : null}
          {loading ? <p className="muted">Searching users…</p> : null}
          {!loading && search.trim() && rows.length === 0 ? (
            <p className="muted">No users match this search.</p>
          ) : null}
          <div className="picker-results">
            {rows.map((row) => {
              const active = value === String(row.id);
              return (
                <button
                  key={row.id}
                  type="button"
                  className={`picker-row${active ? " active" : ""}`}
                  onClick={() => {
                    onChange(String(row.id));
                    setSearch(displayUser(row));
                  }}
                >
                  <strong>{displayUser(row)}</strong>
                  <span>ID {row.id}</span>
                </button>
              );
            })}
          </div>
        </>
      ) : null}
      {error ? <small className="field-error">{error}</small> : null}
    </div>
  );
}
