import { useCallback, useEffect, useState } from "react";
import { apiFetch, type Paginated } from "../api";

export type Column<T> = {
  key: string;
  label: string;
  render?: (row: T) => React.ReactNode;
};

export function useAdminList<T>(endpoint: string) {
  const [rows, setRows] = useState<T[]>([]);
  const [count, setCount] = useState(0);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const reload = useCallback(() => {
    setError("");
    return apiFetch<Paginated<T>>(endpoint)
      .then((data) => {
        setRows(data.results);
        setCount(data.count);
      })
      .catch((e) => setError(String(e.message || e)));
  }, [endpoint]);

  useEffect(() => {
    reload();
  }, [reload]);

  const runAction = async (label: string, fn: () => Promise<unknown>) => {
    setMessage("");
    setError("");
    try {
      await fn();
      setMessage(label);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  return { rows, count, error, message, reload, runAction, setError, setMessage };
}

export function DataTable<T extends Record<string, unknown>>({
  columns,
  rows,
  actions,
}: {
  columns: Column<T>[];
  rows: T[];
  actions?: (row: T) => React.ReactNode;
}) {
  return (
    <table>
      <thead>
        <tr>
          {columns.map((c) => (
            <th key={c.key}>{c.label}</th>
          ))}
          {actions ? <th>Actions</th> : null}
        </tr>
      </thead>
      <tbody>
        {rows.length === 0 ? (
          <tr>
            <td colSpan={columns.length + (actions ? 1 : 0)}>No records yet.</td>
          </tr>
        ) : (
          rows.map((row, i) => (
            <tr key={String(row.id ?? i)}>
              {columns.map((c) => (
                <td key={c.key}>
                  {c.render ? c.render(row) : String(row[c.key] ?? "")}
                </td>
              ))}
              {actions ? <td>{actions(row)}</td> : null}
            </tr>
          ))
        )}
      </tbody>
    </table>
  );
}

export function ActionPanel({ children }: { children: React.ReactNode }) {
  return <section className="panel actions-panel">{children}</section>;
}

export function StatusBanner({ error, message }: { error: string; message: string }) {
  if (error) return <p className="error">{error}</p>;
  if (message) return <p className="success">{message}</p>;
  return null;
}
