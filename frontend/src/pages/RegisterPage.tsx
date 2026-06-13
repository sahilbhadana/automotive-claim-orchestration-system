import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { register } from "../api/endpoints";
import { useAuth } from "../auth/AuthContext";
import { AuthHero } from "./LoginPage";

export function RegisterPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [form, setForm] = useState({
    username: "",
    email: "",
    full_name: "",
    password: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const update = (key: keyof typeof form) => (value: string) =>
    setForm((f) => ({ ...f, [key]: value }));

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await register(form);
      await login(form.username, form.password);
      navigate("/claims", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-page">
      <AuthHero />
      <div className="auth-panel">
        <div className="auth-card">
          <h1>Create account</h1>
          <p className="auth-subtitle">Join the ClaimFlow workspace</p>
          <form onSubmit={handleSubmit}>
            {error && <div className="alert alert-error">{error}</div>}
            <label className="field">
              <span>Full name</span>
              <input
                value={form.full_name}
                onChange={(e) => update("full_name")(e.target.value)}
                required
                minLength={2}
                placeholder="Jane Doe"
              />
            </label>
            <label className="field">
              <span>Username</span>
              <input
                value={form.username}
                onChange={(e) => update("username")(e.target.value)}
                required
                minLength={3}
                placeholder="jane.doe"
              />
            </label>
            <label className="field">
              <span>Email</span>
              <input
                type="email"
                value={form.email}
                onChange={(e) => update("email")(e.target.value)}
                required
                placeholder="jane@example.com"
              />
            </label>
            <label className="field">
              <span>Password</span>
              <input
                type="password"
                value={form.password}
                onChange={(e) => update("password")(e.target.value)}
                required
                minLength={8}
                placeholder="Minimum 8 characters"
              />
            </label>
            <button className="btn btn-primary btn-full" disabled={busy}>
              {busy ? "Creating…" : "Create account"}
            </button>
          </form>
          <p className="auth-switch">
            Already registered? <Link to="/login">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
