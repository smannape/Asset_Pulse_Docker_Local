import { useEffect, useState } from "react";
import type { Asset, SavedScenario, ScenarioInputs } from "../lib/api";

export const DEFAULT_INPUTS: ScenarioInputs = {
  asset_name: "Custom well",
  months_horizon: 120,
  initial_oil_bopd: 650,
  initial_gas_mcfd: 420,
  initial_ngl_bpd: 35,
  annual_decline: 0.45,
  decline_model: "exponential",
  b_factor: 0.7,
  water_cut_initial: 0.25,
  water_cut_final: 0.85,
  oil_price: 72,
  gas_price: 2.85,
  ngl_price: 24,
  royalty_pct: 0.1875,
  production_tax_pct: 0.045,
  transport_per_boe: 1.5,
  processing_per_boe: 0.5,
  fixed_opex_per_month: 14000,
  oil_var_per_bbl: 4.5,
  gas_var_per_mcf: 0.2,
  water_var_per_bbl: 1.5,
  development_capex: 9_290_000,
  sustaining_capex_per_month: 4500,
  abandonment_cost: 180_000,
  discount_rate_annual: 0.10,
  capex_multiplier: 1.0,
  opex_multiplier: 1.0,
  apply_economic_limit: true,

  // Fiscal / Cost Regime defaults — us_royalty_tax keeps existing behaviour.
  fiscal_regime: "us_royalty_tax",
  noc_government_share_pct: 0.0,
  noc_corp_tax_pct: 0.0,
  psc_royalty_pct: 0.10,
  psc_cost_oil_limit_pct: 0.60,
  psc_contractor_profit_share_pct: 0.40,
  psc_contractor_tax_pct: 0.30,
  psc_capex_uplift_pct: 0.0,
  tsc_payment_cap_pct: 0.50,
  tsc_remuneration_per_boe: 1.50,
  tsc_contractor_tax_pct: 0.35,
  concession_royalty_pct: 0.20,
  concession_income_tax_pct: 0.50,
  concession_royalty_progressive: false,
};

export function ScenarioForm({
  inputs,
  onChange,
  onSubmit,
  loading,
  assets,
  scenarios = [],
  onLoadAsset,
  onLoadScenario,
  onReset,
}: {
  inputs: ScenarioInputs;
  onChange: (v: ScenarioInputs) => void;
  onSubmit: () => void;
  loading: boolean;
  assets: Asset[];
  scenarios?: SavedScenario[];
  onLoadAsset: (id: number | null) => void;
  onLoadScenario?: (s: SavedScenario) => void;
  onReset?: () => void;
}) {
  const [selected, setSelected] = useState<string>("");

  useEffect(() => {
    if (selected === "" || selected === "custom") return;
    if (selected.startsWith("scenario:")) {
      const id = Number(selected.slice("scenario:".length));
      const sc = scenarios.find((x) => x.id === id);
      if (sc && onLoadScenario) onLoadScenario(sc);
      return;
    }
    onLoadAsset(Number(selected));
  }, [selected, onLoadAsset, onLoadScenario, scenarios]);

  const set = <K extends keyof ScenarioInputs>(k: K, v: ScenarioInputs[K]) =>
    onChange({ ...inputs, [k]: v });

  const handleReset = () => {
    setSelected("");
    onChange({ ...DEFAULT_INPUTS });
    if (onReset) onReset();
  };

  const numField = (k: keyof ScenarioInputs, label: string, step = 0.01) => {
    const raw = inputs[k];
    const numVal = typeof raw === "number" ? raw : 0;
    return (
      <label key={k}>
        {label}
        <input
          type="number"
          step={step}
          value={numVal}
          onChange={(e) =>
            set(k, (e.target.value === "" ? 0 : Number(e.target.value)) as ScenarioInputs[typeof k])
          }
        />
      </label>
    );
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
    >
      <label className="full" style={{ marginBottom: 6, display: "block" }}>
        <span className="muted" style={{ fontSize: 11 }}>
          Load asset profile{" "}
          <span style={{ opacity: 0.7 }}>
            (base assets + saved scenarios/cases — pick to hydrate inputs)
          </span>
        </span>
        <select value={selected} onChange={(e) => setSelected(e.target.value)}>
          <option value="">— select —</option>
          <option value="custom">Custom (use current values)</option>
          {assets.length > 0 && (
            <optgroup label="Base assets">
              {assets.map((a) => (
                <option key={`asset-${a.id}`} value={String(a.id)}>
                  {a.name} [{a.asset_type}]
                </option>
              ))}
            </optgroup>
          )}
          {scenarios.length > 0 && (
            <optgroup label="Saved scenarios / cases">
              {scenarios.map((sc) => {
                const alias = sc.asset_alias ?? sc.inputs.asset_name;
                return (
                  <option key={`scenario-${sc.id}`} value={`scenario:${sc.id}`}>
                    {sc.name} — {alias} [scenario #{sc.id}]
                  </option>
                );
              })}
            </optgroup>
          )}
        </select>
      </label>

      <div className="form-actions form-actions-top">
        <button
          type="button"
          className="ghost"
          onClick={handleReset}
          title="Restore base scenario defaults (clears any loaded asset profile)"
        >
          Reset
        </button>
        <button type="submit" className="primary" disabled={loading}>
          {loading ? "Running..." : "Run scenario"}
        </button>
      </div>

      <div className="form-grid compact-grid">
        <label className="full">
          Asset name
          <input value={inputs.asset_name} onChange={(e) => set("asset_name", e.target.value)} />
        </label>
        {numField("months_horizon", "Horizon (mo)", 1)}
        {numField("annual_decline", "1st-year decline", 0.01)}
        <label>
          Decline model
          <select
            value={inputs.decline_model}
            onChange={(e) => set("decline_model", e.target.value as ScenarioInputs["decline_model"])}
          >
            <option value="exponential">Exponential</option>
            <option value="hyperbolic">Hyperbolic</option>
            <option value="harmonic">Harmonic</option>
          </select>
        </label>
        {numField("b_factor", "b-factor", 0.05)}
        {numField("initial_oil_bopd", "Initial oil (bopd)", 1)}
        {numField("initial_gas_mcfd", "Initial gas (mcfd)", 1)}
        {numField("oil_price", "Oil $/bbl", 0.5)}
        {numField("fixed_opex_per_month", "Fixed OPEX $/mo", 100)}
        {numField("development_capex", "Dev CAPEX $", 1000)}
        {numField("discount_rate_annual", "Discount rate", 0.005)}
        {numField("capex_multiplier", "CAPEX mult.", 0.01)}
        {numField("opex_multiplier", "OPEX mult.", 0.01)}
        <label className="full row" style={{ marginTop: 4 }}>
          <input
            type="checkbox"
            checked={inputs.apply_economic_limit}
            onChange={(e) => set("apply_economic_limit", e.target.checked)}
            style={{ width: "auto" }}
          />
          <span>Apply economic limit truncation</span>
        </label>
      </div>

      <details className="advanced-fields">
        <summary>Advanced fiscal, fluid, OPEX and ARO inputs</summary>
        <div className="form-grid">
          {numField("initial_ngl_bpd", "Initial NGL (bpd)", 1)}
          {numField("water_cut_initial", "Water cut start", 0.01)}
          {numField("water_cut_final", "Water cut end", 0.01)}
          {numField("gas_price", "Gas $/mcf", 0.05)}
          {numField("ngl_price", "NGL $/bbl", 0.5)}
          {numField("royalty_pct", "Royalty %", 0.005)}
          {numField("production_tax_pct", "Prod tax %", 0.005)}
          {numField("transport_per_boe", "Transport $/BOE", 0.05)}
          {numField("processing_per_boe", "Processing $/BOE", 0.05)}
          {numField("oil_var_per_bbl", "Oil var $/bbl", 0.05)}
          {numField("gas_var_per_mcf", "Gas var $/mcf", 0.01)}
          {numField("water_var_per_bbl", "Water var $/bbl", 0.05)}
          {numField("sustaining_capex_per_month", "Sustain $/mo", 100)}
          {numField("abandonment_cost", "ARO cost $", 1000)}
        </div>

        <div className="fiscal-section" style={{ marginTop: 12 }}>
          <div className="muted" style={{ fontSize: 11, letterSpacing: "0.05em", textTransform: "uppercase", marginBottom: 6 }}>
            Fiscal / Cost Regime
          </div>
          <div className="form-grid">
            <label className="full">
              Regime
              <select
                value={inputs.fiscal_regime ?? "us_royalty_tax"}
                onChange={(e) => set("fiscal_regime", e.target.value as ScenarioInputs["fiscal_regime"])}
              >
                <option value="us_royalty_tax">US royalty/tax (default)</option>
                <option value="noc_internal">NOC internal economics</option>
                <option value="psc_cost_recovery">PSC / EPSA cost recovery</option>
                <option value="technical_service_contract">TSC / RSC technical service</option>
                <option value="concession_tax_royalty">Concession tax/royalty (ME)</option>
              </select>
            </label>

            {inputs.fiscal_regime === "noc_internal" && (
              <>
                {numField("noc_government_share_pct", "Gov transfer %", 0.01)}
                {numField("noc_corp_tax_pct", "Corp tax %", 0.01)}
              </>
            )}

            {inputs.fiscal_regime === "psc_cost_recovery" && (
              <>
                {numField("psc_royalty_pct", "PSC royalty %", 0.005)}
                {numField("psc_cost_oil_limit_pct", "Cost oil ceiling %", 0.05)}
                {numField("psc_contractor_profit_share_pct", "Contractor profit share %", 0.05)}
                {numField("psc_contractor_tax_pct", "Contractor tax %", 0.05)}
                {numField("psc_capex_uplift_pct", "CAPEX uplift %", 0.05)}
              </>
            )}

            {inputs.fiscal_regime === "technical_service_contract" && (
              <>
                {numField("tsc_payment_cap_pct", "Payment cap % of revenue", 0.05)}
                {numField("tsc_remuneration_per_boe", "Remuneration $/BOE", 0.05)}
                {numField("tsc_contractor_tax_pct", "Contractor tax %", 0.05)}
              </>
            )}

            {inputs.fiscal_regime === "concession_tax_royalty" && (
              <>
                <label className="full row">
                  <input
                    type="checkbox"
                    checked={!!inputs.concession_royalty_progressive}
                    onChange={(e) => set("concession_royalty_progressive", e.target.checked)}
                    style={{ width: "auto" }}
                  />
                  <span>Use Saudi-style progressive royalty (15% / 45% / 80% at $70 / $100)</span>
                </label>
                {!inputs.concession_royalty_progressive &&
                  numField("concession_royalty_pct", "Flat royalty %", 0.005)}
                {numField("concession_income_tax_pct", "Income tax %", 0.05)}
              </>
            )}
          </div>
        </div>
      </details>
    </form>
  );
}
