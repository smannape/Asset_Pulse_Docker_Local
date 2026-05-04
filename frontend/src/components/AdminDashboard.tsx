import { FormEvent, useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import {
  AdminUser, ActivityEntry,
  adminActivityLog, adminCreateUser, adminDeleteUser,
  adminListUsers, adminUpdateUser,
} from "../lib/api";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmt(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" });
}

function Badge({ role, active }: { role: string; active: boolean }) {
  if (!active) return <span className="user-badge inactive">Inactive</span>;
  return <span className={`user-badge ${role}`}>{role}</span>;
}

// ---------------------------------------------------------------------------
// Create-user modal
// ---------------------------------------------------------------------------

function CreateUserModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("user");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setErr(null);
    setLoading(true);
    try {
      await adminCreateUser({ email, full_name: name || undefined, password, role });
      onCreated();
      onClose();
    } catch (ex: unknown) {
      setErr(ex instanceof Error ? ex.message : "Failed to create user");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <span>// Create user</span>
          <button className="ghost" onClick={onClose}>✕</button>
        </div>
        <form className="auth-form" onSubmit={submit} noValidate>
          <div className="auth-field">
            <label>Email *</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="user@company.com"
            />
          </div>
          <div className="auth-field">
            <label>Full name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Jane Smith"
            />
          </div>
          <div className="auth-field">
            <label>Password * (min 8 chars)</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="••••••••"
            />
          </div>
          <div className="auth-field">
            <label>Role</label>
            <select value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="user">User</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          {err && <div className="auth-error">! {err}</div>}
          <div className="row" style={{ justifyContent: "flex-end", gap: 8 }}>
            <button type="button" className="ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="primary" disabled={loading}>
              {loading ? "Creating…" : "Create user"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main AdminDashboard
// ---------------------------------------------------------------------------

export function AdminDashboard() {
  const { user: currentUser, logout } = useAuth();
  const navigate = useNavigate();

  const [users, setUsers] = useState<AdminUser[]>([]);
  const [activity, setActivity] = useState<ActivityEntry[]>([]);
  const [tab, setTab] = useState<"users" | "activity">("users");
  const [showCreate, setShowCreate] = useState(false);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [loadingActivity, setLoadingActivity] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const loadUsers = useCallback(async () => {
    setLoadingUsers(true);
    try {
      setUsers(await adminListUsers());
    } catch {
      setActionError("Failed to load users");
    } finally {
      setLoadingUsers(false);
    }
  }, []);

  const loadActivity = useCallback(async () => {
    setLoadingActivity(true);
    try {
      setActivity(await adminActivityLog(200));
    } catch {
      setActionError("Failed to load activity log");
    } finally {
      setLoadingActivity(false);
    }
  }, []);

  useEffect(() => { void loadUsers(); }, [loadUsers]);
  useEffect(() => { if (tab === "activity") void loadActivity(); }, [tab, loadActivity]);

  async function toggleActive(u: AdminUser) {
    setActionError(null);
    try {
      await adminUpdateUser(u.id, { is_active: !u.is_active });
      await loadUsers();
    } catch (ex: unknown) {
      setActionError(ex instanceof Error ? ex.message : "Update failed");
    }
  }

  async function toggleRole(u: AdminUser) {
    setActionError(null);
    const newRole = u.role === "admin" ? "user" : "admin";
    try {
      await adminUpdateUser(u.id, { role: newRole });
      await loadUsers();
    } catch (ex: unknown) {
      setActionError(ex instanceof Error ? ex.message : "Update failed");
    }
  }

  async function deleteUser(u: AdminUser) {
    if (!confirm(`Delete user ${u.email}? This cannot be undone.`)) return;
    setActionError(null);
    try {
      await adminDeleteUser(u.id);
      await loadUsers();
    } catch (ex: unknown) {
      setActionError(ex instanceof Error ? ex.message : "Delete failed");
    }
  }

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="admin-page">
      {/* Top bar */}
      <header className="topbar">
        <div className="brand">
          <span className="brand-name">Asset Pulse</span>
          <span className="brand-tagline" style={{ marginLeft: 10 }}>// Admin</span>
        </div>
        <div className="spacer" />
        <span className="muted" style={{ fontSize: 12 }}>{currentUser?.email}</span>
        <button
          className="ghost"
          style={{ marginLeft: 12 }}
          onClick={() => navigate("/")}
          title="Back to dashboard"
        >
          [ DASHBOARD ]
        </button>
        <button
          className="ghost"
          style={{ marginLeft: 8 }}
          onClick={handleLogout}
        >
          [ SIGN OUT ]
        </button>
      </header>

      <div className="admin-body">
        {/* Tabs */}
        <div className="admin-tabs">
          <button
            className={tab === "users" ? "primary" : "ghost"}
            onClick={() => setTab("users")}
          >
            Users
          </button>
          <button
            className={tab === "activity" ? "primary" : "ghost"}
            onClick={() => setTab("activity")}
          >
            Activity log
          </button>
        </div>

        {actionError && (
          <div className="auth-error" style={{ marginBottom: 12 }}>! {actionError}</div>
        )}

        {/* ------------------------------------------------------------------ */}
        {/* Users tab                                                           */}
        {/* ------------------------------------------------------------------ */}
        {tab === "users" && (
          <div className="admin-section">
            <div className="admin-section-head">
              <span className="admin-section-title">
                {users.length} user{users.length !== 1 ? "s" : ""}
              </span>
              <button
                className="primary"
                style={{ marginLeft: "auto" }}
                onClick={() => setShowCreate(true)}
              >
                + Create user
              </button>
              <button
                className="ghost"
                onClick={loadUsers}
                disabled={loadingUsers}
              >
                Refresh
              </button>
            </div>

            <table className="tbl">
              <thead>
                <tr>
                  <th className="l">Email</th>
                  <th className="l">Name</th>
                  <th className="l">Status / Role</th>
                  <th className="l">Last login</th>
                  <th className="l">Created</th>
                  <th className="l">Actions</th>
                </tr>
              </thead>
              <tbody>
                {loadingUsers ? (
                  <tr>
                    <td colSpan={6} className="muted" style={{ textAlign: "center", padding: 20 }}>
                      Loading…
                    </td>
                  </tr>
                ) : users.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="muted" style={{ textAlign: "center", padding: 20 }}>
                      No users found.
                    </td>
                  </tr>
                ) : (
                  users.map((u) => (
                    <tr key={u.id}>
                      <td className="l">
                        {u.email}
                        {u.id === currentUser?.id && (
                          <span className="muted" style={{ marginLeft: 6, fontSize: 10 }}>(you)</span>
                        )}
                      </td>
                      <td className="l">{u.full_name ?? <span className="faint">—</span>}</td>
                      <td className="l">
                        <Badge role={u.role} active={u.is_active} />
                      </td>
                      <td className="l">{fmt(u.last_login)}</td>
                      <td className="l">{fmt(u.created_at)}</td>
                      <td className="l">
                        <div className="row" style={{ gap: 6 }}>
                          <button
                            style={{ padding: "3px 8px", fontSize: 11 }}
                            onClick={() => toggleActive(u)}
                            disabled={u.id === currentUser?.id}
                            title={u.is_active ? "Deactivate" : "Activate"}
                          >
                            {u.is_active ? "Deactivate" : "Activate"}
                          </button>
                          <button
                            style={{ padding: "3px 8px", fontSize: 11 }}
                            onClick={() => toggleRole(u)}
                            disabled={u.id === currentUser?.id}
                            title={`Change to ${u.role === "admin" ? "user" : "admin"}`}
                          >
                            → {u.role === "admin" ? "user" : "admin"}
                          </button>
                          <button
                            style={{ padding: "3px 8px", fontSize: 11, color: "var(--bad)", borderColor: "var(--bad)" }}
                            onClick={() => deleteUser(u)}
                            disabled={u.id === currentUser?.id}
                            title="Delete user"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* ------------------------------------------------------------------ */}
        {/* Activity log tab                                                    */}
        {/* ------------------------------------------------------------------ */}
        {tab === "activity" && (
          <div className="admin-section">
            <div className="admin-section-head">
              <span className="admin-section-title">Activity log (last 200)</span>
              <button
                className="ghost"
                style={{ marginLeft: "auto" }}
                onClick={loadActivity}
                disabled={loadingActivity}
              >
                Refresh
              </button>
            </div>

            <table className="tbl">
              <thead>
                <tr>
                  <th className="l">Time</th>
                  <th className="l">User</th>
                  <th className="l">Action</th>
                  <th className="l">Resource</th>
                  <th className="l">Details</th>
                  <th className="l">IP</th>
                </tr>
              </thead>
              <tbody>
                {loadingActivity ? (
                  <tr>
                    <td colSpan={6} className="muted" style={{ textAlign: "center", padding: 20 }}>
                      Loading…
                    </td>
                  </tr>
                ) : activity.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="muted" style={{ textAlign: "center", padding: 20 }}>
                      No activity yet.
                    </td>
                  </tr>
                ) : (
                  activity.map((a) => (
                    <tr key={a.id}>
                      <td className="l" style={{ whiteSpace: "nowrap" }}>{fmt(a.created_at)}</td>
                      <td className="l">{a.user_email ?? <span className="faint">—</span>}</td>
                      <td className="l">
                        <span className={`tag ${a.action === "login" ? "accent" : ""}`}>
                          {a.action}
                        </span>
                      </td>
                      <td className="l">
                        {a.resource_type
                          ? `${a.resource_type}${a.resource_id ? ` #${a.resource_id}` : ""}`
                          : <span className="faint">—</span>}
                      </td>
                      <td className="l" style={{ fontSize: 11, color: "var(--text-muted)", maxWidth: 240 }}>
                        {a.details && Object.keys(a.details).length > 0
                          ? JSON.stringify(a.details).slice(0, 120)
                          : <span className="faint">—</span>}
                      </td>
                      <td className="l">{a.ip_address ?? <span className="faint">—</span>}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showCreate && (
        <CreateUserModal
          onClose={() => setShowCreate(false)}
          onCreated={loadUsers}
        />
      )}
    </div>
  );
}
