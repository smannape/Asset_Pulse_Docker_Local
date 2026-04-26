import { useEffect, useMemo, useState } from "react";
import { apiDelete, apiGet, type SavedScenario } from "../lib/api";
import { fmtMonths, fmtNum, fmtUSD } from "../lib/format";

type SortKey = "id" | "npv" | "breakeven" | "payback";

export function ScenarioCompare({
  refreshKey,
  onScenarioDeleted,
}: {
  refreshKey: number;
  onScenarioDeleted?: () => void;
}) {
  const [items, setItems] = useState<SavedScenario[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("id");
  const [filter, setFilter] = useState<string>("");

  const load = () => {
    setLoading(true);
    setErr(null);
    apiGet<SavedScenario[]>("/api/scenarios?limit=100")
      .then((r) => setItems(r))
      .catch((e) => setErr(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey]);

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    const list = q
      ? items.filter((it) =>
          [it.name, it.asset_alias, it.source, it.result?.fiscal_regime]
            .filter(Boolean)
            .some((s) => String(s).toLowerCase().includes(q)),
        )
      : items;
    const sorted = [...list];
    sorted.sort((a, b) => {
      switch (sortKey) {
        case "npv":
          return (b.result?.npv ?? -Infinity) - (a.result?.npv ?? -Infinity);
        case "breakeven":
          return (a.result?.breakeven_oil_price ?? Infinity) - (b.result?.breakeven_oil_price ?? Infinity);
        case "payback":
          return (a.result?.payback_months ?? Infinity) - (b.result?.payback_months ?? Infinity);
        case "id":
        default:
          return b.id - a.id;
      }
    });
    return sorted;
  }, [items, filter, sortKey]);

  const npvMaxAbs = useMemo(() => {
    let m = 1;
    for (const it of filtered) {
      const v = it.result?.npv;
      if (v != null) m = Math.max(m, Math.abs(v));
    }
    return m;
  }, [filtered]);

  const breakevenMax = useMemo(() => {
    let m = 1;
    for (const it of filtered) {
      const v = it.result?.breakeven_oil_price;
      if (v != null) m = Math.max(m, v);
    }
    return m;
  }, [filtered]);

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
    <div>
      <div className="panel">
        <header>
          <h2>Saved scenarios</h2>
          <span className="meta muted">
            {items.length} total · {filtered.length} shown
          </span>
        </header>
        <div className="body">
          <div
            className="row"
            style={{ gap: 10, flexWrap: "wrap", marginBottom: 10 }}
          >
            <button onClick={load} disabled={loading} className="primary">
              {loading ? "Refreshing..." : "Refresh"}
            </button>
            <input
              type="text"
              placeholder="Filter by name / asset / regime"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              style={{ minWidth: 220 }}
            />
            <label className="muted" style={{ fontSize: 12 }}>
              Sort:&nbsp;
              <select value={sortKey} onChange={(e) => setSortKey(e.target.value as SortKey)}>
                <option value="id">Newest first</option>
                <option value="npv">NPV (high → low)</option>
                <option value="breakeven">Breakeven oil (low → high)</option>
                <option value="payback">Payback (fast → slow)</option>
              </select>
            </label>
          </div>

          {err && (
            <div className="ln" style={{ color: "var(--bad)", fontSize: 12 }}>
              ! {err}
            </div>
          )}

          {filtered.length === 0 && !loading && (
            <div className="muted" style={{ fontSize: 12 }}>
              No saved scenarios yet. Use Scenario → Run, or Save &amp; Run from CSV Exchange.
            </div>
          )}

          {filtered.length > 0 && (
            <div style={{ overflowX: "auto" }}>
              <table className="csv-import-table compare-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Scenario</th>
                    <th>Asset</th>
                    <th>Regime</th>
                    <th>Source</th>
                    <th className="right">NPV</th>
                    <th className="right">PV-10</th>
                    <th className="right">Payback</th>
                    <th className="right">Breakeven oil</th>
                    <th className="right">Netback / BOE</th>
                    <th className="right">EUR (BOE)</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((it) => {
                    const r = it.result;
                    const npvCls = r && r.npv != null ? (r.npv > 0 ? "good" : r.npv < 0 ? "bad" : "") : "";
                    return (
                      <tr key={it.id}>
                        <td className="muted">{it.id}</td>
                        <td>{it.name}</td>
                        <td>{it.asset_alias ?? "—"}</td>
                        <td className="mono-num">{r?.fiscal_regime ?? it.inputs.fiscal_regime ?? "—"}</td>
                        <td className="muted mono-num">{it.source ?? "—"}</td>
                        <td className={`right mono-num ${npvCls}`}>{fmtUSD(r?.npv)}</td>
                        <td className="right mono-num">{fmtUSD(r?.pv10)}</td>
                        <td className="right mono-num">{fmtMonths(r?.payback_months ?? null)}</td>
                        <td className="right mono-num">
                          {r?.breakeven_oil_price != null ? `$${r.breakeven_oil_price.toFixed(2)}` : "—"}
                        </td>
                        <td className="right mono-num">
                          {r?.netback_per_boe != null ? `$${r.netback_per_boe.toFixed(2)}` : "—"}
                        </td>
                        <td className="right mono-num">{fmtNum(r?.total_boe)}</td>
                        <td>
                          <button
                            className="ghost"
                            onClick={() => void handleDelete(it.id)}
                            title="Remove this scenario"
                          >
                            delete
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {filtered.length > 0 && (
        <>
          <div className="panel" style={{ marginTop: 12 }}>
            <header>
              <h2>NPV comparison</h2>
              <span className="meta muted">USD · positive = green, negative = red</span>
            </header>
            <div className="body">
              <CompareBars
                rows={filtered.map((it) => ({
                  label: it.name,
                  sub: it.asset_alias ?? "",
                  value: it.result?.npv ?? null,
                  display: fmtUSD(it.result?.npv),
                }))}
                maxAbs={npvMaxAbs}
                signed
              />
            </div>
          </div>

          <div className="panel" style={{ marginTop: 12 }}>
            <header>
              <h2>Breakeven oil price</h2>
              <span className="meta muted">USD/bbl · lower bars = more resilient case</span>
            </header>
            <div className="body">
              <CompareBars
                rows={filtered.map((it) => ({
                  label: it.name,
                  sub: it.asset_alias ?? "",
                  value: it.result?.breakeven_oil_price ?? null,
                  display:
                    it.result?.breakeven_oil_price != null
                      ? `$${it.result.breakeven_oil_price.toFixed(2)}`
                      : "n/a",
                }))}
                maxAbs={breakevenMax}
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
}

type BarRow = { label: string; sub: string; value: number | null; display: string };

function CompareBars({
  rows,
  maxAbs,
  signed = false,
}: {
  rows: BarRow[];
  maxAbs: number;
  signed?: boolean;
}) {
  return (
    <div className="compare-bars">
      {rows.map((r, i) => {
        const v = r.value ?? 0;
        const pct = Math.min(100, Math.abs(v) / maxAbs * 100);
        let left = 0;
        let width = pct;
        let cls = "compare-bar";
        if (signed) {
          left = v < 0 ? 50 - pct / 2 : 50;
          width = pct / 2;
          cls += v >= 0 ? " pos" : " neg";
        }
        return (
          <div className="compare-row" key={`${i}-${r.label}`}>
            <div className="compare-label" title={`${r.label} · ${r.sub}`}>
              <span className="compare-name">{r.label}</span>
              {r.sub ? <span className="muted compare-sub"> · {r.sub}</span> : null}
            </div>
            <div className={signed ? "compare-track signed" : "compare-track"}>
              {signed ? <div className="compare-mid" /> : null}
              {r.value != null ? (
                <div
                  className={cls}
                  style={{ left: `${left}%`, width: `${width}%` }}
                  title={r.display}
                />
              ) : null}
            </div>
            <div className="compare-value mono-num">{r.display}</div>
          </div>
        );
      })}
    </div>
  );
}
