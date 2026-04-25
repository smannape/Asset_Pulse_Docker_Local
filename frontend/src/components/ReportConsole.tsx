import type { ScenarioResult } from "../lib/api";
import { fmtMonths, fmtNum, fmtUSD } from "../lib/format";

type LineKind = "" | "h" | "pre" | "dim" | "warn" | "bad" | "good";
type Line = { kind: LineKind; text: string };

function buildLines(result: ScenarioResult): Line[] {
  const k = result.kpis;
  const m = result.monthly;
  const lines: Line[] = [];
  const ts = new Date().toISOString().replace("T", " ").slice(0, 19);

  lines.push({ kind: "pre", text: `Asset Pulse // analysis report  ${ts}` });
  lines.push({ kind: "h", text: `Asset: ${result.asset_name}` });
  lines.push({ kind: "", text: `> npv             = ${fmtUSD(k.npv)}` });
  lines.push({ kind: "", text: `> pv-10           = ${fmtUSD(k.pv10)}` });
  lines.push({
    kind: "",
    text: `> payback         = ${fmtMonths(k.payback_months)}`,
  });
  lines.push({ kind: "", text: `> netback/boe     = $${fmtNum(k.netback_per_boe, 2)}` });
  lines.push({ kind: "", text: `> total boe       = ${fmtNum(k.total_boe)}` });
  lines.push({
    kind: "",
    text: `> decline model   = ${k.decline_model ?? "exponential"}${
      k.decline_model === "hyperbolic" || k.decline_model === "harmonic"
        ? ` (b=${fmtNum(k.b_factor, 2)})`
        : ""
    }`,
  });
  lines.push({
    kind: "",
    text: `> economic limit  = ${
      k.economic_limit.economic_limit_boe_per_month != null
        ? `${fmtNum(k.economic_limit.economic_limit_boe_per_month)} BOE/mo`
        : "n/a"
    } (net price/BOE = $${fmtNum(k.economic_limit.net_price_per_boe, 2)})`,
  });
  if (k.truncated_at_month != null) {
    lines.push({
      kind: "warn",
      text: `! decline truncated at month ${k.truncated_at_month} — economic limit reached.`,
    });
  }

  // Fiscal regime summary
  if (result.fiscal && result.fiscal.summary) {
    const f = result.fiscal.summary;
    const regime = f.regime ?? k.fiscal_regime ?? "us_royalty_tax";
    lines.push({ kind: "h", text: `Fiscal regime: ${regime}` });
    if (regime === "us_royalty_tax") {
      lines.push({
        kind: "dim",
        text: "  Base US royalty + production tax already netted in revenue.",
      });
    } else if (regime === "noc_internal") {
      lines.push({ kind: "", text: `> gross revenue   = ${fmtUSD(f.gross_revenue_total ?? 0)}` });
      lines.push({ kind: "", text: `> gov transfer    = ${fmtPct(f.government_share_pct)} | corp tax = ${fmtPct(f.corp_tax_pct)}` });
      lines.push({ kind: "", text: `> gov take total  = ${fmtUSD(f.government_total ?? 0)}` });
      lines.push({ kind: "", text: `> contractor cf   = ${fmtUSD(f.contractor_total_cf ?? 0)}` });
    } else if (regime === "psc_cost_recovery") {
      lines.push({
        kind: "",
        text: `> royalty / cost-oil ceiling / profit share / tax = ${fmtPct(f.royalty_pct)} / ${fmtPct(f.cost_oil_limit_pct)} / ${fmtPct(f.contractor_profit_share_pct)} / ${fmtPct(f.contractor_tax_pct)}`,
      });
      if ((f.capex_uplift_pct ?? 0) > 0) {
        lines.push({ kind: "dim", text: `  capex uplift     = ${fmtPct(f.capex_uplift_pct)}` });
      }
      lines.push({ kind: "", text: `> royalty total   = ${fmtUSD(f.royalty_total ?? 0)}` });
      lines.push({ kind: "", text: `> cost oil total  = ${fmtUSD(f.cost_oil_total ?? 0)}` });
      lines.push({ kind: "", text: `> profit oil      = ${fmtUSD(f.profit_oil_total ?? 0)} (gov ${fmtUSD(f.government_profit_oil_total ?? 0)} | contractor ${fmtUSD(f.contractor_profit_oil_total ?? 0)})` });
      lines.push({ kind: "", text: `> contractor tax  = ${fmtUSD(f.contractor_tax_total ?? 0)}` });
      lines.push({ kind: "", text: `> carry-fwd end   = ${fmtUSD(f.carry_forward_end ?? 0)}` });
      lines.push({ kind: "", text: `> gov take total  = ${fmtUSD(f.government_total ?? 0)}` });
      lines.push({ kind: "", text: `> contractor cf   = ${fmtUSD(f.contractor_total_cf ?? 0)}` });
    } else if (regime === "technical_service_contract") {
      lines.push({
        kind: "",
        text: `> payment cap / fee/BOE / tax = ${fmtPct(f.payment_cap_pct)} / $${fmtNum(f.remuneration_per_boe ?? 0, 2)} / ${fmtPct(f.contractor_tax_pct)}`,
      });
      lines.push({ kind: "", text: `> reimbursement   = ${fmtUSD(f.reimbursement_total ?? 0)}` });
      lines.push({ kind: "", text: `> remuneration    = ${fmtUSD(f.remuneration_total ?? 0)}` });
      lines.push({ kind: "", text: `> contractor tax  = ${fmtUSD(f.contractor_tax_total ?? 0)}` });
      lines.push({ kind: "", text: `> carry-fwd end   = ${fmtUSD(f.carry_forward_end ?? 0)}` });
      lines.push({ kind: "", text: `> gov take total  = ${fmtUSD(f.government_total ?? 0)}` });
      lines.push({ kind: "", text: `> contractor cf   = ${fmtUSD(f.contractor_total_cf ?? 0)}` });
    } else if (regime === "concession_tax_royalty") {
      lines.push({
        kind: "",
        text: `> royalty (${f.royalty_progressive ? "progressive" : "flat"}) eff. rate = ${fmtPct(f.effective_royalty_rate)} | income tax = ${fmtPct(f.income_tax_pct)}`,
      });
      lines.push({ kind: "", text: `> royalty total   = ${fmtUSD(f.royalty_total ?? 0)}` });
      lines.push({ kind: "", text: `> income tax      = ${fmtUSD(f.income_tax_total ?? 0)}` });
      lines.push({ kind: "", text: `> gov take total  = ${fmtUSD(f.government_total ?? 0)}` });
      lines.push({ kind: "", text: `> contractor cf   = ${fmtUSD(f.contractor_total_cf ?? 0)}` });
    }
    if (f.note) {
      lines.push({ kind: "dim", text: `  ${f.note}` });
    }
  }

  lines.push({ kind: "h", text: "First 12-month projection" });
  lines.push({
    kind: "dim",
    text: "  mo |    net rev  |     opex    |   sustain   |    fcf",
  });
  for (let i = 0; i < Math.min(12, m.months.length); i++) {
    const row = `  ${String(m.months[i]).padStart(2)} | ${pad(m.net_revenue[i])} | ${pad(
      m.opex[i]
    )} | ${pad(m.sustaining_capex[i])} | ${pad(m.free_cash_flow[i])}`;
    lines.push({ kind: m.free_cash_flow[i] < 0 ? "bad" : "", text: row });
  }
  lines.push({ kind: "dim", text: `  ... ${m.months.length - 12} more months` });

  // Cumulative cash flow & profitability commentary
  const cum = m.free_cash_flow.reduce((a, b) => a + b, 0);
  lines.push({ kind: "h", text: "Profitability commentary" });
  lines.push({
    kind: cum >= 0 ? "good" : "bad",
    text:
      cum >= 0
        ? `+ undiscounted cumulative free cash flow = ${fmtUSD(cum)}`
        : `- undiscounted cumulative free cash flow = ${fmtUSD(cum)} (project would not recover capital)`,
  });
  lines.push({
    kind: k.npv >= 0 ? "good" : "bad",
    text:
      k.npv >= 0
        ? `+ NPV positive at ${(k.discount_rate_annual * 100).toFixed(0)}% — project clears hurdle.`
        : `- NPV negative at ${(k.discount_rate_annual * 100).toFixed(0)}% — would destroy value at current inputs.`,
  });
  lines.push({
    kind: "dim",
    text:
      "  Run sensitivities to find which input has the largest swing on NPV. Use Decision Matrix for shut-in / restart calls.",
  });
  lines.push({ kind: "pre", text: "EOF — ready for next command." });
  return lines;
}

function pad(n: number): string {
  const s = `$${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
  return s.padStart(11);
}

function fmtPct(v: number | undefined | null): string {
  if (v == null || Number.isNaN(v)) return "n/a";
  return `${(v * 100).toFixed(1)}%`;
}

export function ReportConsole({ result }: { result: ScenarioResult | null }) {
  if (!result) {
    return (
      <div className="console">
        <span className="ln pre">Asset Pulse // ready</span>
        <span className="ln dim">
          Select an asset profile or fill in scenario inputs, then press “Run scenario”.
        </span>
        <span className="ln dim">Outputs: NPV, PV-10, payback, economic limit, netback, sensitivities.</span>
        <span className="ln">
          asset-pulse&gt; <span className="cursor">_</span>
        </span>
      </div>
    );
  }

  const lines = buildLines(result);
  return (
    <div className="console">
      {lines.map((l, i) => (
        <span key={i} className={`ln ${l.kind}`}>
          {l.text}
        </span>
      ))}
      <span className="ln">
        asset-pulse&gt; <span className="cursor">_</span>
      </span>
    </div>
  );
}
