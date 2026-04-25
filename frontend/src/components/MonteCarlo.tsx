import { useState } from "react";
import { apiPost, type MonteCarloResponse, type ScenarioInputs } from "../lib/api";
import { fmtUSD } from "../lib/format";

type MonteInputs = {
  iterations: number;
  seed: number;
  oilLow: number;
  oilMode: number;
  oilHigh: number;
  capexLow: number;
  capexMode: number;
  capexHigh: number;
  opexLow: number;
  opexMode: number;
  opexHigh: number;
};

function defaultMonte(inputs: ScenarioInputs): MonteInputs {
  return {
    iterations: 1000,
    seed: 42,
    oilLow: Math.max(1, inputs.oil_price * 0.75),
    oilMode: inputs.oil_price,
    oilHigh: inputs.oil_price * 1.30,
    capexLow: Math.max(0.2, inputs.capex_multiplier * 0.95),
    capexMode: inputs.capex_multiplier,
    capexHigh: inputs.capex_multiplier * 1.30,
    opexLow: Math.max(0.2, inputs.opex_multiplier * 0.95),
    opexMode: inputs.opex_multiplier,
    opexHigh: inputs.opex_multiplier * 1.25,
  };
}

export function MonteCarlo({ inputs }: { inputs: ScenarioInputs }) {
  const [cfg, setCfg] = useState<MonteInputs>(() => defaultMonte(inputs));
  const [data, setData] = useState<MonteCarloResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const set = <K extends keyof MonteInputs>(k: K, v: MonteInputs[K]) => {
    setCfg({ ...cfg, [k]: v });
  };

  const numField = (k: keyof MonteInputs, label: string, step = 0.01) => (
    <label key={k}>
      {label}
      <input
        type="number"
        step={step}
        value={cfg[k]}
        onChange={(e) => set(k, (e.target.value === "" ? 0 : Number(e.target.value)) as never)}
      />
    </label>
  );

  const run = async () => {
    setLoading(true);
    setErr(null);
    try {
      const r = await apiPost<MonteCarloResponse>("/api/uncertainty/montecarlo", {
        base_inputs: inputs,
        iterations: cfg.iterations,
        seed: cfg.seed,
        distributions: {
          oil_price: { type: "triangular", low: cfg.oilLow, mode: cfg.oilMode, high: cfg.oilHigh },
          capex_multiplier: { type: "triangular", low: cfg.capexLow, mode: cfg.capexMode, high: cfg.capexHigh },
          opex_multiplier: { type: "triangular", low: cfg.opexLow, mode: cfg.opexMode, high: cfg.opexHigh },
        },
      });
      setData(r);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setCfg(defaultMonte(inputs));
    setData(null);
  };

  const span = data ? Math.max(1, data.max - data.min) : 1;
  const pos = (v: number) => (data ? ((v - data.min) / span) * 100 : 0);

  return (
    <div>
      <div className="row" style={{ marginBottom: 8 }}>
        <button className="primary" onClick={run} disabled={loading}>
          {loading ? "Simulating..." : "Run Monte Carlo"}
        </button>
        <button className="ghost" onClick={reset} disabled={loading}>Reset distribution</button>
        {data && <span className="muted">{data.iterations} trials · seed {cfg.seed}</span>}
      </div>

      {err && <div className="ln bad">! {err}</div>}

      <details className="advanced-fields" open={!data}>
        <summary>Distribution setup</summary>
        <div className="form-grid">
          {numField("iterations", "Iterations", 100)}
          {numField("seed", "Seed", 1)}
          {numField("oilLow", "Oil low $/bbl", 0.5)}
          {numField("oilMode", "Oil mode $/bbl", 0.5)}
          {numField("oilHigh", "Oil high $/bbl", 0.5)}
          {numField("capexLow", "CAPEX mult low", 0.01)}
          {numField("capexMode", "CAPEX mult mode", 0.01)}
          {numField("capexHigh", "CAPEX mult high", 0.01)}
          {numField("opexLow", "OPEX mult low", 0.01)}
          {numField("opexMode", "OPEX mult mode", 0.01)}
          {numField("opexHigh", "OPEX mult high", 0.01)}
        </div>
      </details>

      {!data && !loading && (
        <div className="muted" style={{ marginTop: 8 }}>
          Simulates NPV uncertainty using triangular distributions for oil price, CAPEX multiplier and OPEX multiplier.
        </div>
      )}

      {data && (
        <>
          <div className="mc-kpis">
            <div><span>P10</span><strong>{fmtUSD(data.p10)}</strong></div>
            <div><span>P50</span><strong>{fmtUSD(data.p50)}</strong></div>
            <div><span>P90</span><strong>{fmtUSD(data.p90)}</strong></div>
            <div><span>Mean</span><strong>{fmtUSD(data.mean)}</strong></div>
            <div><span>σ</span><strong>{fmtUSD(data.stdev)}</strong></div>
          </div>
          <div className="mc-track" title={`min ${fmtUSD(data.min)} / max ${fmtUSD(data.max)}`}>
            <span className="mc-range" />
            <span className="mc-marker p10" style={{ left: `${pos(data.p10)}%` }} title={`P10 ${fmtUSD(data.p10)}`} />
            <span className="mc-marker p50" style={{ left: `${pos(data.p50)}%` }} title={`P50 ${fmtUSD(data.p50)}`} />
            <span className="mc-marker p90" style={{ left: `${pos(data.p90)}%` }} title={`P90 ${fmtUSD(data.p90)}`} />
          </div>
          <div className="row" style={{ justifyContent: "space-between", marginTop: 4 }}>
            <span className="muted">min {fmtUSD(data.min)}</span>
            <span className="muted">max {fmtUSD(data.max)}</span>
          </div>
          <div className="console" style={{ minHeight: 120, marginTop: 10 }}>
            <span className="ln pre">Asset Pulse // monte carlo summary</span>
            <span className="ln">{`> downside case P10 = ${fmtUSD(data.p10)}`}</span>
            <span className="ln">{`> median case   P50 = ${fmtUSD(data.p50)}`}</span>
            <span className="ln">{`> upside case   P90 = ${fmtUSD(data.p90)}`}</span>
            <span className={data.p10 < 0 ? "ln bad" : "ln good"}>
              {data.p10 < 0
                ? "! P10 is negative — downside cases can destroy value."
                : "+ P10 remains positive — downside economics are resilient under selected ranges."}
            </span>
          </div>
        </>
      )}
    </div>
  );
}
