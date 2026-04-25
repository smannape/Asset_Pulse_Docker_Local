import { useEffect, useState } from "react";
import { apiPost, type DecisionAsset, type DecisionResultRow } from "../lib/api";
import { fmtNum, fmtUSD } from "../lib/format";

const SAMPLE: DecisionAsset[] = [
  {
    name: "Eagle Ford Pad-3 Well A",
    monthly_margin: 95_000,
    npv_keep_online: 4_800_000,
    avoidable_opex: 14_500,
    restart_payback_months: 6,
    restart_risk: 0.2,
    hbp_risk: 0.3,
    water_burden: 0.25,
    strategic_value: 0.85,
  },
  {
    name: "Eagle Ford Pad-3 Well B",
    monthly_margin: -8_500,
    npv_keep_online: -180_000,
    avoidable_opex: 18_000,
    restart_payback_months: 22,
    restart_risk: 0.55,
    hbp_risk: 0.65,
    water_burden: 0.78,
    strategic_value: 0.40,
  },
  {
    name: "Permian Stripper Well-12",
    monthly_margin: -12_400,
    npv_keep_online: -420_000,
    avoidable_opex: 11_500,
    restart_payback_months: 38,
    restart_risk: 0.75,
    hbp_risk: 0.10,
    water_burden: 0.92,
    strategic_value: 0.20,
  },
];

export function DecisionMatrix() {
  const [rows, setRows] = useState<DecisionAsset[]>(SAMPLE);
  const [results, setResults] = useState<DecisionResultRow[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const update = (i: number, k: keyof DecisionAsset, v: string) => {
    setRows((arr) =>
      arr.map((r, j) => {
        if (j !== i) return r;
        if (k === "name") return { ...r, name: v };
        return { ...r, [k]: Number(v) };
      })
    );
  };

  const run = async () => {
    setLoading(true);
    setErr(null);
    try {
      const r = await apiPost<{ results: DecisionResultRow[] }>(
        "/api/decision-matrix/score",
        { assets: rows }
      );
      setResults(r.results);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void run();
    // Seeded decision rows should score once on first render for the demo dashboard.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const maxScore = results ? Math.max(...results.map((r) => r.weighted_score), 0.01) : 1;

  return (
    <div>
      <div className="muted" style={{ marginBottom: 8 }}>
        Edit per-asset metrics, then score. Higher score = stronger keep-online position; high
        shut-in pressure flags candidates.
      </div>
      <div className="scrollbox" style={{ marginBottom: 10 }}>
        <table className="tbl">
          <thead>
            <tr>
              <th className="l">Asset</th>
              <th>Monthly margin</th>
              <th>NPV keep online</th>
              <th>Avoidable OPEX</th>
              <th>Restart payback (mo)</th>
              <th>Restart risk 0-1</th>
              <th>HBP risk 0-1</th>
              <th>Water burden 0-1</th>
              <th>Strategic 0-1</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                <td className="l">
                  <input value={r.name} onChange={(e) => update(i, "name", e.target.value)} />
                </td>
                {(
                  [
                    "monthly_margin",
                    "npv_keep_online",
                    "avoidable_opex",
                    "restart_payback_months",
                    "restart_risk",
                    "hbp_risk",
                    "water_burden",
                    "strategic_value",
                  ] as (keyof DecisionAsset)[]
                ).map((k) => (
                  <td key={k}>
                    <input
                      type="number"
                      step="0.01"
                      value={r[k] as number}
                      onChange={(e) => update(i, k, e.target.value)}
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="row" style={{ marginBottom: 10 }}>
        <button className="primary" onClick={run} disabled={loading}>
          {loading ? "Scoring..." : "Score matrix"}
        </button>
        <button
          className="ghost"
          onClick={() =>
            setRows([
              ...rows,
              {
                name: `New asset ${rows.length + 1}`,
                monthly_margin: 0, npv_keep_online: 0, avoidable_opex: 0,
                restart_payback_months: 12, restart_risk: 0.5, hbp_risk: 0.5,
                water_burden: 0.5, strategic_value: 0.5,
              },
            ])
          }
        >
          + add asset
        </button>
      </div>

      {err && <div className="ln bad">! {err}</div>}

      {results && (
        <div>
          <div className="muted" style={{ marginBottom: 6 }}>Ranked results:</div>
          {results.map((r) => {
            const recCls =
              r.recommendation.startsWith("Keep") ? "good" :
              r.recommendation.startsWith("Shut") ? "bad" :
              r.recommendation.startsWith("Restart") ? "accent" : "warn";
            return (
              <div key={r.asset_id} className="dm-row">
                <div className="name">{r.name}</div>
                <div className="score-bar">
                  <div className="score-fill" style={{ width: `${(r.weighted_score / maxScore) * 100}%` }} />
                </div>
                <div className="mono-num right">{fmtNum(r.weighted_score, 3)}</div>
                <div className="rec">
                  <span className={`tag ${recCls === "accent" ? "accent" : recCls}`}>{r.recommendation}</span>
                </div>
                <div style={{ gridColumn: "1 / -1", paddingLeft: 12, fontSize: 11, color: "var(--text-muted)" }}>
                  shut-in pressure: <span className="mono-num">{fmtNum(r.shut_in_pressure, 3)}</span> · keep-online
                  pressure: <span className="mono-num">{fmtNum(r.keep_online_pressure, 3)}</span> · top driver:
                  {topContribution(r)}
                </div>
              </div>
            );
          })}
          <div className="muted" style={{ marginTop: 6, fontSize: 11 }}>
            * NPV/margin values shown above (e.g. {fmtUSD(rows[0]?.npv_keep_online)}) are normalised against the
            asset population before weighting.
          </div>
        </div>
      )}
    </div>
  );
}

function topContribution(r: DecisionResultRow) {
  const top = [...r.breakdown].sort((a, b) => b.contribution - a.contribution)[0];
  if (!top) return null;
  return ` ${top.label} (${(top.contribution).toFixed(3)})`;
}
