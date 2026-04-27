import { useEffect, useState } from "react";
import { apiDelete, apiGet, type SavedScenario } from "../lib/api";
import { fmtMonths, fmtUSD } from "../lib/format";

// Full audit trail of every saved scenario, with a one-line description of
// the result so a reader can scan history without opening each case.

type RegimeKey = string;

function describeRegime(r: RegimeKey | null | undefined): string {
  switch (r) {
    case "us_royalty_tax":
      return "US royalty/tax";
    case "noc_internal":
      return "NOC internal";
    case "psc_cost_recovery":
      return "PSC / EPSA";
    case "technical_service_contract":
      return "TSC / RSC";
    case "concession_tax_royalty":
      return "Concession (ME)";
    default:
      return r ?? "—";
  }
}

function recommendationFor(sc: SavedScenario): {
  label: string;
  cls: string;
} {
  const r = sc.result;
  if (!r) return { label: "Not run yet", cls: "" };
  const npv = r.npv;
  if (npv == null) return { label: "Result unavailable", cls: "" };
  if (npv > 0 && (r.payback_months ?? Infinity) < 60) {
    return { label: "Proceed", cls: "good" };
  }
  if (npv > 0) return { label: "Marginal — accept w/ caution", cls: "" };
  if (npv < 0) return { label: "Defer / reject", cls: "bad" };
  return { label: "Break-even", cls: "" };
}

function formatStamp(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toISOString().replace("T", " ").slice(0, 16);
  } catch {
    return iso;
  }
}

export function CaseHistory({
  refreshKey,
  onScenarioDeleted,
  onLoadScenario,
}: {
  refreshKey: number;
  onScenarioDeleted?: () => void;
  onLoadScenario?: (sc: SavedScenario) => void;
}) {
  const [items, setItems] = useState<SavedScenario[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setErr(null);
    apiGet<SavedScenario[]>("/api/scenarios?limit=500")
      .then((r) => setItems(r))
      .catch((e) => setErr(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey]);

  const filtered = filter.trim()
    ? items.filter((it) => {
        const q = filter.trim().toLowerCase();
        return [it.name, it.asset_alias, it.source, it.result?.fiscal_regime]
          .filter(Boolean)
          .some((s) => String(s).toLowerCase().includes(q));
      })
    : items;

  const handleDelete = async (id: number) => {
    try {
      await apiDelete(`/api/scenarios/${id}`);
      load();
      if (onScenarioDeleted) onScenarioDeleted();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <div className="case-history">
      <div className="row" style={{ gap: 10, flexWrap: "wrap", marginBottom: 12 }}>
        <button onClick={load} disabled={loading} className="primary">
          {loading ? "Refreshing..." : "Refresh history"}
        </button>
        <input
          type="text"
          placeholder="Filter by name / asset / regime"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          style={{ minWidth: 220 }}
        />
        <span className="muted" style={{ fontSize: 12 }}>
          {filtered.length} of {items.length} historical case
          {items.length === 1 ? "" : "s"} shown
        </span>
      </div>

      {err && (
        <div className="ln" style={{ color: "var(--bad)", fontSize: 12, marginBottom: 8 }}>
          ! {err}
        </div>
      )}

      {filtered.length === 0 && !loading && (
        <div className="muted" style={{ fontSize: 12 }}>
          No saved cases match. Run a scenario or save one from CSV import.
        </div>
      )}

      <div className="case-list">
        {filtered.map((sc) => {
          const r = sc.result;
          const rec = recommendationFor(sc);
          const desc =
            r && r.npv != null
              ? `NPV ${fmtUSD(r.npv)} · BE oil ${
                  r.breakeven_oil_price != null
                    ? `$${r.breakeven_oil_price.toFixed(2)}`
                    : "n/a"
                } · payback ${fmtMonths(r.payback_months)}`
              : "Saved without a result. Open in Scenario and Run to compute.";
          return (
            <div className="case-card" key={sc.id}>
              <div className="case-card-head">
                <div className="case-title">
                  <span className="case-name">{sc.name}</span>
                  <span className="muted case-id"> · #{sc.id}</span>
                </div>
                <div className="case-meta">
                  <span className={`tag ${rec.cls}`}>{rec.label}</span>
                  <span className="tag">{describeRegime(r?.fiscal_regime ?? sc.inputs.fiscal_regime)}</span>
                </div>
              </div>
              <div className="case-sub">
                <span>
                  asset: <b>{sc.asset_alias ?? sc.inputs.asset_name ?? "—"}</b>
                </span>
                <span className="muted">source: {sc.source ?? "—"}</span>
                <span className="muted">last run: {formatStamp(sc.created_at)}</span>
              </div>
              <div className="case-desc">{desc}</div>
              <div className="case-actions">
                {onLoadScenario && (
                  <button
                    onClick={() => onLoadScenario(sc)}
                    title="Hydrate the Scenario form with these inputs"
                  >
                    load into scenario
                  </button>
                )}
                <button
                  className="ghost"
                  onClick={() => void handleDelete(sc.id)}
                  title="Delete this saved case"
                >
                  delete
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
