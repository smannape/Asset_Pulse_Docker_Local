import { useCallback, useEffect, useMemo, useState } from "react";
import { AssetTable } from "./components/AssetTable";
import { CashFlowChart } from "./components/CashFlowChart";
import { DataExchange } from "./components/DataExchange";
import { DecisionMatrix } from "./components/DecisionMatrix";
import { EventPanel } from "./components/EventPanel";
import { KPIStrip } from "./components/KPIStrip";
import { Logo } from "./components/Logo";
import { MonteCarlo } from "./components/MonteCarlo";
import { Panel } from "./components/Panel";
import { ReportConsole } from "./components/ReportConsole";
import { ScenarioForm, DEFAULT_INPUTS } from "./components/ScenarioForm";
import { Tornado } from "./components/Tornado";
import {
  API_BASE,
  apiGet,
  apiPost,
  type Asset,
  type ScenarioInputs,
  type ScenarioResult,
} from "./lib/api";

type View = "scenario" | "sensitivity" | "events" | "matrix" | "assets" | "exchange";
type Theme = "light" | "dark";

export default function App() {
  const [theme, setTheme] = useState<Theme>("light");
  const [view, setView] = useState<View>("scenario");
  const [inputs, setInputs] = useState<ScenarioInputs>(DEFAULT_INPUTS);
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [running, setRunning] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [health, setHealth] = useState<{ status: string; database: string } | null>(null);

  // Push theme to <html data-theme="...">
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  // Load assets + health on mount
  useEffect(() => {
    apiGet<Asset[]>("/api/assets").then(setAssets).catch(() => setAssets([]));
    apiGet<{ status: string; database: string }>("/api/health")
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  const runScenario = useCallback(async () => {
    setRunning(true);
    setErr(null);
    try {
      const r = await apiPost<ScenarioResult>("/api/scenario/run", inputs);
      setResult(r);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  }, [inputs]);

  // When user picks an asset profile, hydrate inputs from cost profile.
  // Use functional setInputs so the callback identity doesn't change with every
  // input edit — otherwise the ScenarioForm's load-asset effect would re-fire
  // and silently overwrite changes (including a Reset).
  const onLoadAsset = useCallback(
    (id: number | null) => {
      if (id === null) return;
      const a = assets.find((x) => x.id === id);
      if (!a) return;
      const cp = a.cost_profile;
      if (!cp) return;
      setInputs((prev) => {
        const next: ScenarioInputs = {
          ...prev,
          asset_name: a.name,
          ...(cp.decline_inputs ?? {}),
          ...(cp.opex_inputs ?? {}),
        } as ScenarioInputs;
        if (a.asset_type === "well" && cp.capex_inputs) {
          const sum = Object.entries(cp.capex_inputs).reduce((acc, [k, v]) => {
            if (k === "contingency_pct" || k === "capitalized_aro") return acc;
            return acc + (typeof v === "number" ? v : 0);
          }, 0);
          const cont = (cp.capex_inputs.contingency_pct ?? 0) * sum;
          next.development_capex = sum + cont + (cp.capex_inputs.capitalized_aro ?? 0);
        }
        return next;
      });
    },
    [assets]
  );

  const baseMonthlyCf = useMemo(() => {
    if (!result) return null;
    const fcf = result.monthly.free_cash_flow.slice(1); // exclude t=0 capex
    if (fcf.length === 0) return 0;
    const positive = fcf.filter((v) => v > 0);
    if (positive.length === 0) return fcf.reduce((a, b) => a + b, 0) / fcf.length;
    return positive.reduce((a, b) => a + b, 0) / positive.length;
  }, [result]);

  const cmds: Array<{ id: View; label: string; key: string }> = [
    { id: "scenario", label: "Scenario", key: "01" },
    { id: "sensitivity", label: "Sensitivity", key: "02" },
    { id: "events", label: "Events", key: "03" },
    { id: "matrix", label: "Decision Matrix", key: "04" },
    { id: "assets", label: "Assets", key: "05" },
    { id: "exchange", label: "CSV Exchange", key: "06" },
  ];

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <Logo height={26} />
          <span className="brand-name sr-only">Asset Pulse</span>
          <span className="v">v0.1 · forecasting decision terminal</span>
        </div>
        <div className="spacer" />
        <nav className="nav">
          {cmds.map((c) => (
            <a
              key={c.id}
              href="#"
              className={view === c.id ? "active" : ""}
              onClick={(e) => {
                e.preventDefault();
                setView(c.id);
              }}
            >
              {c.label}
            </a>
          ))}
        </nav>
        <button
          className="ghost"
          onClick={() => setTheme(theme === "light" ? "dark" : "light")}
          title="Toggle theme"
        >
          {theme === "light" ? "[ DARK ]" : "[ LIGHT ]"}
        </button>
      </header>

      <aside className="rail">
        <h4>// Commands</h4>
        {cmds.map((c) => (
          <div
            key={c.id}
            className={`cmd ${view === c.id ? "active" : ""}`}
            onClick={() => setView(c.id)}
          >
            <span>{c.label}</span>
            <span className="key">{c.key}</span>
          </div>
        ))}
        <h4>// Loaded</h4>
        <div className="muted" style={{ fontSize: 11 }}>
          Asset: <span className="accent-text">{inputs.asset_name}</span>
          <br />
          Horizon: {inputs.months_horizon} mo
          <br />
          CAPEX mult.: {inputs.capex_multiplier} · OPEX mult.: {inputs.opex_multiplier}
        </div>
        <h4>// Status</h4>
        <div style={{ fontSize: 11 }} className="muted">
          api: <span className="accent-text">{API_BASE || "/api (relative)"}</span>
          <br />
          db: <span className="accent-text">{health?.database ?? "unknown"}</span>
        </div>
      </aside>

      <main className="main">
        {err && (
          <div className="panel" style={{ borderColor: "var(--bad)" }}>
            <div className="body" style={{ color: "var(--bad)" }}>
              ! {err}
            </div>
          </div>
        )}

        {view === "scenario" && (
          <>
            <KPIStrip result={result} />
            <div className="two-col">
              <Panel title="Scenario inputs" meta={<span className="muted">USD · monthly horizon</span>}>
                <ScenarioForm
                  inputs={inputs}
                  onChange={setInputs}
                  onSubmit={runScenario}
                  loading={running}
                  assets={assets}
                  onLoadAsset={onLoadAsset}
                />
              </Panel>
              <div>
                <Panel
                  title="Analysis report"
                  meta={result ? <span className="accent-text">{result.asset_name}</span> : null}
                >
                  <ReportConsole result={result} />
                </Panel>
                <Panel title="Cash flow projection">
                  <CashFlowChart result={result} />
                </Panel>
              </div>
            </div>
          </>
        )}

        {view === "sensitivity" && (
          <>
            <Panel
              title="Tornado sensitivity"
              meta={<span className="muted">±% swings on key drivers · ranks by NPV swing</span>}
            >
              <Tornado inputs={inputs} />
            </Panel>
            <Panel title="Notes">
              <div className="muted" style={{ fontSize: 12, lineHeight: 1.6 }}>
                Each row varies one input by the configured ±%; bars show the NPV delta vs base. Largest swing
                is the dominant driver. Run Monte Carlo below for P10/P50/P90 economics under price, CAPEX and
                OPEX uncertainty.
              </div>
            </Panel>
            <Panel
              title="Monte Carlo uncertainty"
              meta={<span className="muted">Triangular drivers · P10/P50/P90 NPV</span>}
            >
              <MonteCarlo inputs={inputs} />
            </Panel>
          </>
        )}

        {view === "events" && (
          <Panel
            title="Event impact stack"
            meta={<span className="muted">CAPEX overruns · downtime · price drops · escalation</span>}
          >
            <EventPanel
              baseNpv={result?.kpis.npv ?? null}
              baseMonthlyCf={baseMonthlyCf}
            />
          </Panel>
        )}

        {view === "matrix" && (
          <Panel
            title="Weighted decision matrix"
            meta={<span className="muted">Shut-in / restart / keep-online recommender</span>}
          >
            <DecisionMatrix />
          </Panel>
        )}

        {view === "assets" && (
          <Panel title="Asset registry" meta={<span className="muted">{assets.length} loaded</span>}>
            <AssetTable
              assets={assets}
              onSelect={(a) => {
                onLoadAsset(a.id);
                setView("scenario");
              }}
            />
          </Panel>
        )}

        {view === "exchange" && (
          <Panel
            title="CSV exchange"
            meta={<span className="muted">Excel handoff · scenario/cash-flow exports</span>}
          >
            <DataExchange
              inputs={inputs}
              onImportInputs={setInputs}
              onLoadScenario={(next) => {
                setInputs(next);
                setResult(null);
                setView("scenario");
              }}
              result={result}
              assets={assets}
            />
          </Panel>
        )}
      </main>

      <footer className="status">
        <span className={`row ${health?.status === "ok" ? "ok" : "warn"}`}>
          <span className="dot" />
          {health ? `api ${health.status}` : "api unreachable"}
        </span>
        <span className="muted">db: {health?.database ?? "—"}</span>
        <span className="muted">theme: {theme}</span>
        <span className="muted">view: {view}</span>
        <span className="muted" style={{ marginLeft: "auto" }}>
          Asset Pulse // formulas in python · storage on neon · ui on netlify
        </span>
      </footer>
    </div>
  );
}
