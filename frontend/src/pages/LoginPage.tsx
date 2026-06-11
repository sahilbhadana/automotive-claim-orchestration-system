import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Banknote,
  GitBranch,
  ShieldCheck,
  Siren,
} from "lucide-react";
import { useAuth } from "../auth/AuthContext";

const FEATURES = [
  {
    icon: GitBranch,
    title: "9-stage claim workflow",
    desc: "Guided state machine from intake to payout — nothing falls through.",
  },
  {
    icon: Siren,
    title: "Real-time fraud scoring",
    desc: "Rule-based risk engine flags duplicates, patterns, and high-risk garages.",
  },
  {
    icon: Banknote,
    title: "Resilient settlements",
    desc: "Automatic retries with exponential backoff and full audit trails.",
  },
];

export function AuthHero() {
  return (
    <div className="auth-hero">
      <div className="auth-hero-content">
        <div className="brand-logo">
          <ShieldCheck size={26} />
        </div>
        <h2>
          Insurance claims,
          <br />
          <span className="gradient-text">orchestrated end to end.</span>
        </h2>
        <p>
          ClaimFlow automates the full automotive claim lifecycle — intake,
          verification, fraud analysis, adjuster assignment, and payout — on a
          production-grade event-driven platform.
        </p>
        {FEATURES.map((f) => {
          const Icon = f.icon;
          return (
            <div key={f.title} className="auth-feature">
              <div className="auth-feature-icon">
                <Icon size={18} />
              </div>
              <div>
                <div className="auth-feature-title">{f.title}</div>
                <div className="auth-feature-desc">{f.desc}</div>
              </div>
            </div>
          );
        })}
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
          <h1>Welcome back</h1>
          <p className="auth-subtitle">Sign in to your ClaimFlow workspace</p>
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
