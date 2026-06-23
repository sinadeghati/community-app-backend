import { useEffect, useState } from "react";
import { apiFetch, type Paginated } from "../api";

type Column<T> = {
  key: string;
  label: string;
  render?: (row: T) => React.ReactNode;
};

export default function AdminListPage<T extends Record<string, unknown>>({
  title,
  endpoint,
  columns,
}: {
  title: string;
  endpoint: string;
  columns: Column<T>[];
}) {
  const [rows, setRows] = useState<T[]>([]);
  const [count, setCount] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch<Paginated<T>>(endpoint)
      .then((data) => {
        setRows(data.results);
        setCount(data.count);
      })
      .catch((e) => setError(String(e.message || e)));
  }, [endpoint]);

  if (error) return <p className="error">{error}</p>;
  if (!rows) return <p>Loading…</p>;

  return (
    <div>
      <h1>{title}</h1>
      <p className="muted">{count} total</p>
      <div className="panel">
        <table>
          <thead>
            <tr>
              {columns.map((c) => (
                <th key={c.key}>{c.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length}>No records yet.</td>
              </tr>
            ) : (
              rows.map((row, i) => (
                <tr key={String(row.id ?? i)}>
                  {columns.map((c) => (
                    <td key={c.key}>
                      {c.render ? c.render(row) : String(row[c.key] ?? "")}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
