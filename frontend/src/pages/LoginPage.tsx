import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { useAuth } from "../auth/AuthContext";

const METRICS = [
  { value: "9", label: "workflow stages, enforced" },
  { value: "6", label: "fraud rule families" },
  { value: "100%", label: "of actions audit-logged" },
];

const FEATURES = [
  {
    title: "State-machine workflow.",
    desc: "Claims move intake → verification → fraud → payout. Skipped steps are rejected at the API.",
  },
  {
    title: "Fraud scoring before approval.",
    desc: "Duplicate vehicles, repeat incidents, inflated estimates, and flagged garages — scored on every claim.",
  },
  {
    title: "Payouts that survive failure.",
    desc: "Failed transfers retry with exponential backoff. Exhausted retries land in a dead-letter queue, never lost.",
  },
];

export function AuthHero() {
  return (
    <div className="auth-hero">
      <div className="auth-hero-content">
        <div className="brand-logo">
          <ShieldCheck size={20} />
        </div>
        <h2>
          Settle motor claims in days,
          <br />
          <span className="accent-text">not weeks.</span>
        </h2>
        <p>
          ClaimFlow runs the full automotive claim lifecycle — intake, document
          verification, fraud analysis, adjuster assignment, and payout — on a
          single audited workflow engine.
        </p>
        <div className="auth-metrics">
          {METRICS.map((m) => (
            <div key={m.label} className="auth-metric">
              <div className="auth-metric-value">{m.value}</div>
              <div className="auth-metric-label">{m.label}</div>
            </div>
          ))}
        </div>
        {FEATURES.map((f) => (
          <div key={f.title} className="auth-feature">
            <span className="auth-feature-icon">
              <ArrowRight size={14} />
            </span>
            <span>
              <span className="auth-feature-title">{f.title}</span>
              <span className="auth-feature-desc">{f.desc}</span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const from =
    (location.state as { from?: { pathname: string } })?.from?.pathname ??
    "/claims";

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(username, password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-page">
      <AuthHero />
      <div className="auth-panel">
        <div className="auth-card">
          <h1>Sign in</h1>
          <p className="auth-subtitle">Pick up where your team left off.</p>
          <form onSubmit={handleSubmit}>
            {error && <div className="alert alert-error">{error}</div>}
            <label className="field">
              <span>Username</span>
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                minLength={3}
                autoComplete="username"
                placeholder="your.username"
              />
            </label>
            <label className="field">
              <span>Password</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                autoComplete="current-password"
                placeholder="••••••••"
              />
            </label>
            <button className="btn btn-primary btn-full" disabled={busy}>
              {busy ? "Signing in…" : "Sign in"}
            </button>
          </form>
          <p className="auth-switch">
            No account? <Link to="/register">Create one</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
