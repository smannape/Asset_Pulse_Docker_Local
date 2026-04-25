import { useState } from "react";
import { apiPost, type ScenarioInputs, type TornadoResponse } from "../lib/api";
import { fmtUSD } from "../lib/format";

export function Tornado({ inputs }: { inputs: ScenarioInputs }) {
  const [data, setData] = useState<TornadoResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const run = async () => {
    setLoading(true);
    setErr(null);
    try {
      const r = await apiPost<TornadoResponse>("/api/uncertainty/tornado", {
        base_inputs: inputs,
      });
      setData(r);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  // Compute scale. We chart deltas vs base in NPV space.
  let maxAbs = 1;
  if (data) {
    for (const r of data.rows) {
      maxAbs = Math.max(maxAbs, Math.abs(r.delta_low), Math.abs(r.delta_high));
    }
  }

  return (
    <div>
      <div className="row" style={{ marginBottom: 8 }}>
        <button className="primary" onClick={run} disabled={loading}>
          {loading ? "Computing..." : "Run tornado sensitivity"}
        </button>
        {data && (
          <span className="muted">
            base NPV = {fmtUSD(data.base_npv)} · {data.rows.length} variables
          </span>
        )}
      </div>
      {err && <div className="ln bad">! {err}</div>}
      {!data && !loading && (
        <div className="muted">Tests ±% swings on key drivers; ranks by NPV swing.</div>
      )}
      {data && (
        <div className="tornado">
          {data.rows.map((r) => {
            const lowPct = Math.min(0, r.delta_low / maxAbs);
            const highPct = Math.max(0, r.delta_high / maxAbs);
            const lowLeft = 50 + (lowPct * 50);
            const lowWidth = Math.abs(lowPct * 50);
            const highWidth = Math.abs(highPct * 50);
            return (
              <Row
                key={r.variable}
                name={r.variable}
                lowLeft={lowLeft}
                lowWidth={lowWidth}
                highWidth={highWidth}
                low={r.delta_low}
                high={r.delta_high}
                swing={r.swing}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

function Row({
  name, lowLeft, lowWidth, highWidth, low, high, swing,
}: {
  name: string; lowLeft: number; lowWidth: number; highWidth: number; low: number; high: number; swing: number;
}) {
  return (
    <>
      <div className="name">{name}</div>
      <div className="bar-track" title={`Δ low ${low.toFixed(0)} / Δ high ${high.toFixed(0)}`}>
        <div className="bar-mid" />
        <div
          className="bar-low"
          style={{ left: `${lowLeft}%`, width: `${lowWidth}%` }}
          title={`Δ ${low.toFixed(0)}`}
        />
        <div
          className="bar-high"
          style={{ left: "50%", width: `${highWidth}%` }}
          title={`Δ ${high.toFixed(0)}`}
        />
      </div>
      <div className="swing mono-num">{fmtUSD(swing)}</div>
    </>
  );
}
