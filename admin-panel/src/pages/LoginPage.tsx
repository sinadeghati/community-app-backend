import { useState } from "react";
import { apiFetch, ensureCsrf } from "../api";

export default function LoginPage({
  onLogin,
}: {
  onLogin: (user: { username: string }) => void;
}) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await ensureCsrf();
      const res = await apiFetch<{ user: { username: string } }>("/admin/auth/login/", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      onLogin(res.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  };

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={submit}>
        <h1>Korook Admin</h1>
        <p>Staff access only</p>
        <label>
          Username
          <input value={username} onChange={(e) => setUsername(e.target.value)} />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        {error ? <p className="error">{error}</p> : null}
        <button type="submit">Sign in</button>
      </form>
    </div>
  );
}
