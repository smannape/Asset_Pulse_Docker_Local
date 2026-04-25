import type { ScenarioResult } from "../lib/api";
import { fmtMonths, fmtNum, fmtUSD } from "../lib/format";

export function KPIStrip({ result }: { result: ScenarioResult | null }) {
  const k = result?.kpis;
  const npvClass =
    k && k.npv > 0 ? "good" : k && k.npv < 0 ? "bad" : "accent";
  const el = k?.economic_limit?.economic_limit_boe_per_month;
  return (
    <div className="kpis">
      <Cell label="NPV" value={k ? fmtUSD(k.npv) : "—"} cls={npvClass} />
      <Cell label="PV-10" value={k ? fmtUSD(k.pv10) : "—"} cls="accent" />
      <Cell label="Payback" value={k ? fmtMonths(k.payback_months) : "—"} />
      <Cell label="Netback / BOE" value={k ? `$${fmtNum(k.netback_per_boe, 2)}` : "—"} />
      <Cell label="EUR (BOE)" value={k ? fmtNum(k.total_boe) : "—"} />
      <Cell label="Econ Limit" value={el != null ? `${fmtNum(el)} BOE/mo` : "n/a"} />
      <Cell
        label="Truncated"
        value={k?.truncated_at_month != null ? `Mo ${k.truncated_at_month}` : "no"}
        cls={k?.truncated_at_month != null ? "bad" : ""}
      />
      <Cell label="Discount" value={k ? `${(k.discount_rate_annual * 100).toFixed(1)}%` : "—"} />
    </div>
  );
}

function Cell({ label, value, cls = "" }: { label: string; value: string; cls?: string }) {
  return (
    <div className="kpi">
      <div className="label">{label}</div>
      <div className={`value mono-num ${cls}`}>{value}</div>
    </div>
  );
}
