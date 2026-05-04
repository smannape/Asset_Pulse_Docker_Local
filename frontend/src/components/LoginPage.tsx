import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { Logo } from "./Logo";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email.trim(), password);
      navigate("/", { replace: true });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <Logo height={36} />
          <div className="auth-brand-name">Asset Pulse</div>
          <div className="auth-brand-tag">Forecasting &amp; Decision Intelligence</div>
        </div>

        <div className="auth-divider" />

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          <div className="auth-field">
            <label htmlFor="ap-email">Email address</label>
            <input
              id="ap-email"
              type="email"
              autoComplete="username"
              placeholder="user@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={loading}
            />
          </div>

          <div className="auth-field">
            <label htmlFor="ap-password">Password</label>
            <input
              id="ap-password"
              type="password"
              autoComplete="current-password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading}
            />
          </div>

          {error && <div className="auth-error">! {error}</div>}

          <button
            type="submit"
            className="primary auth-submit"
            disabled={loading || !email || !password}
          >
            {loading ? "Signing in…" : "[ SIGN IN ]"}
          </button>
        </form>

        <div className="auth-footer">
          Access is granted by your administrator.
        </div>
      </div>
    </div>
  );
}
