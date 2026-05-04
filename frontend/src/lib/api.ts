// API client with JWT auth injection.
// VITE_API_BASE_URL defaults to "" (relative /api) so Nginx proxy works seamlessly.

const RAW_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) || "";
export const API_BASE = RAW_BASE.replace(/\/$/, "");

const TOKEN_KEY = "ap_token";
export const getStoredToken = (): string | null => localStorage.getItem(TOKEN_KEY);
export const setStoredToken = (t: string): void => { localStorage.setItem(TOKEN_KEY, t); };
export const clearStoredToken = (): void => { localStorage.removeItem(TOKEN_KEY); };

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const token = getStoredToken();
  const h: Record<string, string> = { "Content-Type": "application/json", ...extra };
  if (token) h["Authorization"] = `Bearer ${token}`;
  return h;
}

// On 401, clear token so the app redirects to login on next navigation.
function handle401(status: number): void {
  if (status === 401) clearStoredToken();
}

export async function apiGet<T = unknown>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { headers: authHeaders() });
  handle401(res.status);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

export async function apiPost<T = unknown>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(body),
  });
  handle401(res.status);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`POST ${path} failed: ${res.status} ${text}`);
  }
  return res.json();
}

export async function apiPut<T = unknown>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers: authHeaders(),
    body: JSON.stringify(body),
  });
  handle401(res.status);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`PUT ${path} failed: ${res.status} ${text}`);
  }
  return res.json();
}

export async function apiDelete<T = unknown>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  handle401(res.status);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`DELETE ${path} failed: ${res.status} ${text}`);
  }
  return res.json();
}

export async function apiPostBlob(path: string, body: unknown): Promise<Blob> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(body),
  });
  handle401(res.status);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`POST ${path} failed: ${res.status} ${text}`);
  }
  return res.blob();
}

export async function runScenarioApi<T = unknown>(
  body: unknown,
  opts?: { scenarioId?: number | null },
): Promise<T> {
  const params = new URLSearchParams();
  if (opts?.scenarioId != null) params.set("scenario_id", String(opts.scenarioId));
  const qs = params.toString();
  return apiPost<T>(`/api/scenario/run${qs ? `?${qs}` : ""}`, body);
}

// ---------------------------------------------------------------------------
// Auth API
// ---------------------------------------------------------------------------

export interface AuthUserOut {
  id: number;
  email: string;
  full_name?: string | null;
  role: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: AuthUserOut;
}

export async function authLogin(email: string, password: string): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail ?? `Login failed: ${res.status}`);
  }
  return res.json();
}

export async function authLogout(token: string): Promise<void> {
  await fetch(`${API_BASE}/api/auth/logout`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<{ message: string }> {
  return apiPost("/api/auth/change-password", {
    current_password: currentPassword,
    new_password: newPassword,
  });
}

// ---------------------------------------------------------------------------
// Admin API
// ---------------------------------------------------------------------------

export interface AdminUser {
  id: number;
  email: string;
  full_name?: string | null;
  role: string;
  is_active: boolean;
  created_at: string | null;
  last_login: string | null;
}

export interface ActivityEntry {
  id: number;
  user_email?: string | null;
  action: string;
  resource_type?: string | null;
  resource_id?: number | null;
  details?: Record<string, unknown> | null;
  ip_address?: string | null;
  created_at: string | null;
}

export const adminListUsers = (): Promise<AdminUser[]> =>
  apiGet("/api/admin/users");

export const adminCreateUser = (payload: {
  email: string;
  password: string;
  full_name?: string;
  role?: string;
}): Promise<{ id: number; email: string; role: string }> =>
  apiPost("/api/admin/users", payload);

export const adminUpdateUser = (
  id: number,
  payload: Partial<{ full_name: string; role: string; is_active: boolean; password: string }>,
): Promise<{ message: string }> => apiPut(`/api/admin/users/${id}`, payload);

export const adminDeleteUser = (id: number): Promise<{ deleted: number }> =>
  apiDelete(`/api/admin/users/${id}`);

export const adminActivityLog = (limit = 200): Promise<ActivityEntry[]> =>
  apiGet(`/api/admin/activity?limit=${limit}`);

// ---------------------------------------------------------------------------
// Domain types (unchanged from original)
// ---------------------------------------------------------------------------

export type ScenarioInputs = {
  asset_name: string;
  months_horizon: number;
  initial_oil_bopd: number;
  initial_gas_mcfd: number;
  initial_ngl_bpd: number;
  annual_decline: number;
  decline_model: "exponential" | "hyperbolic" | "harmonic";
  b_factor: number;
  water_cut_initial: number;
  water_cut_final: number;
  oil_price: number;
  gas_price: number;
  ngl_price: number;
  royalty_pct: number;
  production_tax_pct: number;
  transport_per_boe: number;
  processing_per_boe: number;
  fixed_opex_per_month: number;
  oil_var_per_bbl: number;
  gas_var_per_mcf: number;
  water_var_per_bbl: number;
  development_capex: number;
  sustaining_capex_per_month: number;
  abandonment_cost: number;
  discount_rate_annual: number;
  capex_multiplier: number;
  opex_multiplier: number;
  apply_economic_limit: boolean;
  fiscal_regime?: FiscalRegime;
  noc_government_share_pct?: number;
  noc_corp_tax_pct?: number;
  psc_royalty_pct?: number;
  psc_cost_oil_limit_pct?: number;
  psc_contractor_profit_share_pct?: number;
  psc_contractor_tax_pct?: number;
  psc_capex_uplift_pct?: number;
  tsc_payment_cap_pct?: number;
  tsc_remuneration_per_boe?: number;
  tsc_contractor_tax_pct?: number;
  concession_royalty_pct?: number;
  concession_income_tax_pct?: number;
  concession_royalty_progressive?: boolean;
  concession_royalty_tiers?: Array<{ upper: number | null; rate: number }> | null;
};

export type FiscalRegime =
  | "us_royalty_tax"
  | "noc_internal"
  | "psc_cost_recovery"
  | "technical_service_contract"
  | "concession_tax_royalty";

export type FiscalSummary = {
  regime: FiscalRegime | string;
  contractor_total_cf?: number;
  government_total?: number;
  royalty_pct?: number;
  cost_oil_limit_pct?: number;
  contractor_profit_share_pct?: number;
  contractor_tax_pct?: number;
  capex_uplift_pct?: number;
  royalty_total?: number;
  cost_oil_total?: number;
  profit_oil_total?: number;
  government_profit_oil_total?: number;
  contractor_profit_oil_total?: number;
  contractor_tax_total?: number;
  carry_forward_end?: number;
  payment_cap_pct?: number;
  remuneration_per_boe?: number;
  reimbursement_total?: number;
  remuneration_total?: number;
  royalty_progressive?: boolean;
  effective_royalty_rate?: number;
  flat_royalty_pct?: number;
  income_tax_pct?: number;
  income_tax_total?: number;
  tiers_used?: Array<{ upper: number | null; rate: number }> | null;
  gross_revenue_total?: number;
  government_share_pct?: number;
  corp_tax_pct?: number;
  note?: string;
};

export type FiscalBlock = {
  regime: string;
  contractor_cf: number[];
  monthly: Record<string, number[]>;
  summary: FiscalSummary;
};

export type ScenarioResult = {
  asset_name: string;
  scenario_id?: number;
  breakeven_oil_price?: number | null;
  kpis: {
    npv: number;
    pv10: number;
    payback_months: number | null;
    economic_limit: {
      net_price_per_boe: number;
      economic_limit_boe_per_month: number | null;
      note: string;
    };
    total_boe: number;
    netback_per_boe: number;
    truncated_at_month: number | null;
    discount_rate_annual: number;
    decline_model: string;
    b_factor: number;
    fiscal_regime?: FiscalRegime;
  };
  fiscal?: FiscalBlock;
  monthly: {
    months: number[];
    net_revenue: number[];
    opex: number[];
    sustaining_capex: number[];
    dev_capex: number[];
    abandonment: number[];
    free_cash_flow: number[];
    oil_bbl: number[];
    gas_mcf: number[];
    water_bbl: number[];
  };
};

export type Asset = {
  id: number;
  name: string;
  asset_type: string;
  region: string | null;
  metadata: Record<string, unknown> | null;
  cost_profile: {
    capex_inputs: Record<string, number> | null;
    opex_inputs: Record<string, number> | null;
    decline_inputs: Record<string, number> | null;
  } | null;
};

export type TornadoRow = {
  variable: string;
  low_value: number;
  base_value: number;
  high_value: number;
  low_npv: number;
  base_npv: number;
  high_npv: number;
  swing: number;
  delta_low: number;
  delta_high: number;
};

export type TornadoResponse = { base_npv: number; rows: TornadoRow[] };

export type MonteCarloResponse = {
  iterations: number;
  mean: number;
  stdev: number;
  p10: number;
  p50: number;
  p90: number;
  min: number;
  max: number;
};

export type DecisionAsset = {
  asset_id?: string;
  name: string;
  monthly_margin: number;
  npv_keep_online: number;
  avoidable_opex: number;
  restart_payback_months: number;
  restart_risk: number;
  hbp_risk: number;
  water_burden: number;
  strategic_value: number;
};

export type DecisionResultRow = {
  asset_id: string;
  name: string;
  weighted_score: number;
  shut_in_pressure: number;
  keep_online_pressure: number;
  recommendation: string;
  breakdown: Array<{
    key: string;
    label: string;
    value: number;
    normalized: number;
    weight: number;
    contribution: number;
    direction: string;
  }>;
};

export type EventInput = {
  type: string;
  magnitude: number;
  duration_months: number;
  notes?: string;
};

export type SavedScenarioResult = {
  npv: number | null;
  pv10: number | null;
  payback_months: number | null;
  netback_per_boe: number | null;
  economic_limit_boe_per_month: number | null;
  breakeven_oil_price: number | null;
  total_boe: number | null;
  fiscal_regime: string | null;
};

export type SavedScenario = {
  id: number;
  name: string;
  asset_id: number | null;
  asset_alias: string | null;
  source: string | null;
  created_at: string | null;
  inputs: ScenarioInputs;
  result: SavedScenarioResult | null;
};

export type ScenarioImportRow = {
  scenario_name?: string;
  asset_id_or_name?: string;
  notes?: string;
  inputs: ScenarioInputs;
};

export type ScenarioImportSavedEntry = {
  scenario_id: number;
  name: string;
  asset_alias: string | null;
  asset_id: number | null;
  npv?: number | null;
  breakeven_oil_price?: number | null;
  ran: boolean;
};

export type ScenarioImportResponse = {
  saved: ScenarioImportSavedEntry[];
  errors: Array<{ row: number; error: string }>;
};
