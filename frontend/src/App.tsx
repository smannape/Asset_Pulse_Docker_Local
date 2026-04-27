import { useCallback, useEffect, useMemo, useState } from "react";
import { AssetTable } from "./components/AssetTable";
import { CashFlowChart } from "./components/CashFlowChart";
import { CaseHistory } from "./components/CaseHistory";
import { DataExchange } from "./components/DataExchange";
import { DecisionMatrix } from "./components/DecisionMatrix";
import { EventPanel } from "./components/EventPanel";
import { InfoTip } from "./components/InfoTip";
import { KPIStrip } from "./components/KPIStrip";
import { Logo } from "./components/Logo";
import { MonteCarlo } from "./components/MonteCarlo";
import { Panel } from "./components/Panel";
import { PetroleumEconomics } from "./components/PetroleumEconomics";
import { ReportConsole } from "./components/ReportConsole";
import { ScenarioCompare } from "./components/ScenarioCompare";
import { ScenarioForm, DEFAULT_INPUTS } from "./components/ScenarioForm";
import { Tornado } from "./components/Tornado";
import {
  API_BASE,
  apiGet,
  runScenarioApi,
  type Asset,
  type SavedScenario,
  type ScenarioInputs,
  type ScenarioResult,
} from "./lib/api";

type View =
  | "scenario"
  | "sensitivity"
  | "events"
  | "matrix"
  | "assets"
  | "compare"
  | "history"
  | "economics";
type Theme = "light" | "dark";

// Short hover descriptions for top-nav / sidebar tabs. Kept in one place so
// the topbar and rail stay in sync.
const VIEW_DESCRIPTIONS: Record<View, string> = {
  scenario:
    "Build and run a single asset case — inputs, KPIs, cash flow, CSV import.",
  sensitivity:
    "Tornado + Monte Carlo. See which drivers actually move NPV and the P10/P50/P90 spread.",
  events:
    "Stack downtime, price drops, OPEX escalation, CAPEX overruns on a base NPV case.",
  matrix:
    "Weighted decision matrix — keep online, choke, shut-in, restart recommendations.",
  assets:
    "Browse seeded wells, pipelines, gathering systems and facilities.",
  compare:
    "Side-by-side compare of saved scenarios with NPV / breakeven bars and PDF report.",
  history:
    "Full audit trail of every saved case with one-line result summaries.",
  economics:
    "Petroleum-economics primer with flow charts: workflow, CAPEX, OPEX, regional regimes.",
};

export default function App() {
  const [theme, setTheme] = useState<Theme>("light");
  const [view, setView] = useState<View>("scenario");
  const [inputs, setInputs] = useState<ScenarioInputs>(DEFAULT_INPUTS);
  const [result, setResult] = useState<ScenarioResult | null>(null);
  // Tracks which saved scenario the form is currently bound to, so a Run
  // updates that DB row in-place rather than creating a new sibling.
  const [loadedScenarioId, setLoadedScenarioId] = useState<number | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [scenarios, setScenarios] = useState<SavedScenario[]>([]);
  const [running, setRunning] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [health, setHealth] = useState<{ status: string; database: string } | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [assetsLoading, setAssetsLoading] = useState(false);

  // Push theme to <html data-theme="...">
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  const refreshAssets = useCallback(async () => {
    setAssetsLoading(true);
    try {
      const [a, sc] = await Promise.all([
        apiGet<Asset[]>("/api/assets"),
        apiGet<SavedScenario[]>("/api/scenarios?limit=100").catch(() => [] as SavedScenario[]),
      ]);
      setAssets(a);
      setScenarios(sc);
    } catch {
      // keep prior list — refresh is best-effort
    } finally {
      setAssetsLoading(false);
    }
  }, []);

  // Load assets + health on mount
  useEffect(() => {
    void refreshAssets();
    apiGet<{ status: string; database: string }>("/api/health")
      .then(setHealth)
      .catch(() => setHealth(null));
  }, [refreshAssets]);

  const bumpRefreshKey = useCallback(() => setRefreshKey((k) => k + 1), []);

  const runScenario = useCallback(async () => {
    setRunning(true);
    setErr(null);
    try {
      const r = await runScenarioApi<ScenarioResult>(inputs, {
        scenarioId: loadedScenarioId,
      });
      setResult(r);
      // Stay bound to whichever scenario row the backend persisted to, so a
      // follow-up Run keeps updating in place rather than spawning siblings.
      if (typeof r.scenario_id === "number") {
        setLoadedScenarioId(r.scenario_id);
      }
      // Persist + sibling tabs need to see the updated row.
      bumpRefreshKey();
      void refreshAssets();
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  }, [inputs, loadedScenarioId, bumpRefreshKey, refreshAssets]);

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
      // Picking a base asset detaches the form from any saved scenario row.
      setLoadedScenarioId(null);
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

  const onLoadSavedScenario = useCallback((sc: SavedScenario) => {
    setInputs({ ...DEFAULT_INPUTS, ...sc.inputs });
    setResult(null);
    // Bind the form to this saved scenario so Run updates it in place.
    setLoadedScenarioId(sc.id);
  }, []);

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
    { id: "compare", label: "Scenario Compare", key: "06" },
    { id: "history", label: "Case History", key: "07" },
    { id: "economics", label: "Petroleum Economics", key: "08" },
  ];

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <Logo height={28} />
          <InfoTip
            label={
              <span className="brand-block">
                <span className="brand-name">Asset Pulse</span>
                <span className="brand-tagline">
                  Forecasting &amp; Decision Intelligence
                </span>
              </span>
            }
            description="Oilfield forecasting and decision-support dashboard — production decline, NPV / PV-10 / payback, fiscal regimes, sensitivity, Monte Carlo, decision matrix."
            position="below"
            className="brand-info"
          />
          <span className="v brand-version">v0.1</span>
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
              title={VIEW_DESCRIPTIONS[c.id]}
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
            title={VIEW_DESCRIPTIONS[c.id]}
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
          <br />
          assets: <span className="accent-text">{assets.length}</span> · scenarios:{" "}
          <span className="accent-text">{scenarios.length}</span>
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
              <Panel
                title="Scenario inputs"
                info="Asset, fluid mix, decline, prices, fiscal regime, CAPEX/OPEX. Pick a base asset or saved case to hydrate, then Run."
                meta={<span className="muted">USD · monthly horizon</span>}
              >
                <ScenarioForm
                  inputs={inputs}
                  onChange={setInputs}
                  onSubmit={runScenario}
                  loading={running}
                  assets={assets}
                  scenarios={scenarios}
                  onLoadAsset={onLoadAsset}
                  onLoadScenario={onLoadSavedScenario}
                  onReset={() => {
                    setLoadedScenarioId(null);
                    setResult(null);
                  }}
                />
              </Panel>
              <div>
                <Panel
                  title="Analysis report"
                  info="Terminal-style summary of the run: KPIs, fiscal split, cash flow tape and warnings."
                  meta={result ? <span className="accent-text">{result.asset_name}</span> : null}
                >
                  <ReportConsole result={result} />
                </Panel>
                <Panel
                  title="Cash flow projection"
                  info="Monthly free cash flow over the horizon — bars below zero are CAPEX/loss months."
                >
                  <CashFlowChart result={result} />
                </Panel>
              </div>
            </div>

            <Panel
              title="Upload data — CSV import & save/run"
              info="Bulk import scenarios from a CSV. Preview rows, edit, then Save & Run to persist them as cases."
              meta={
                <span className="muted">
                  Upload → approve rows → Save &amp; Run · saved cases appear in the dropdown above
                </span>
              }
            >
              <DataExchange
                inputs={inputs}
                onImportInputs={(next) => {
                  setInputs(next);
                  setLoadedScenarioId(null);
                }}
                onLoadScenario={(next) => {
                  setInputs(next);
                  setResult(null);
                  setLoadedScenarioId(null);
                }}
                onScenariosSaved={() => {
                  bumpRefreshKey();
                  void refreshAssets();
                }}
                onResultReady={(r, nextInputs) => {
                  // CSV Save & Run finished — push the freshly-computed result
                  // into the visible Scenario panel and bind the form to that
                  // saved row so a follow-up Run updates it in place.
                  setInputs(nextInputs);
                  setResult(r);
                  if (typeof r.scenario_id === "number") {
                    setLoadedScenarioId(r.scenario_id);
                  }
                }}
                result={result}
                assets={assets}
              />
            </Panel>
          </>
        )}

        {view === "sensitivity" && (
          <>
            <Panel
              title={`Tornado sensitivity — ${inputs.asset_name}`}
              info="Each driver is varied ±% one at a time and ranked by NPV swing. Longest bar is the dominant value driver."
              meta={
                <span className="muted">
                  ±% swings on key drivers · ranks by NPV swing
                </span>
              }
            >
              <div
                className="ln"
                style={{
                  marginBottom: 8,
                  fontSize: 12,
                  color: "var(--accent)",
                  fontWeight: 600,
                }}
              >
                Tornado sensitivity for: {inputs.asset_name}
                {result?.scenario_id ? ` · scenario #${result.scenario_id}` : ""}
              </div>
              <Tornado inputs={inputs} />
            </Panel>
            <Panel title="Why run a tornado sensitivity?">
              <div className="muted" style={{ fontSize: 12, lineHeight: 1.65 }}>
                A tornado sensitivity varies <b>one assumption at a time</b> by a
                fixed ±% (oil price, decline, CAPEX, OPEX, water cut, discount
                rate, etc.) while holding everything else constant, and ranks
                each input by the resulting <b>NPV swing</b>. The bar shown for
                each variable is its delta vs the base NPV; the longest bar is
                the dominant value driver.
                <br />
                <br />
                <b>What it achieves:</b>
                <ul style={{ margin: "6px 0 0 18px" }}>
                  <li>
                    Identifies the <b>key economic levers</b> for the selected
                    asset/scenario so capital and OPEX attention go to inputs
                    that actually move NPV.
                  </li>
                  <li>
                    Surfaces <b>risk controls</b> — variables with large
                    downside swings are candidates for hedging, contracting, or
                    tighter operational monitoring.
                  </li>
                  <li>
                    Provides a quick <b>sanity check</b> before committing to
                    Monte Carlo: if a driver doesn't move NPV here, modeling its
                    distribution is rarely worth the effort.
                  </li>
                </ul>
              </div>
            </Panel>
            <Panel
              title={`Monte Carlo uncertainty — ${inputs.asset_name}`}
              info="Triangular distributions across the same drivers with N iterations. Reports P10 / P50 / P90 NPV and full range."
              meta={<span className="muted">Triangular drivers · P10/P50/P90 NPV</span>}
            >
              <MonteCarlo inputs={inputs} />
            </Panel>
          </>
        )}

        {view === "events" && (
          <Panel
            title="Event impact stack"
            info="Layer ad-hoc events on top of the base case. Each event compounds NPV and monthly cash flow."
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
            info="Score each asset across multi-criteria weights to recommend keep-online, choke, shut-in, or restart."
            meta={<span className="muted">Shut-in / restart / keep-online recommender</span>}
          >
            <DecisionMatrix />
          </Panel>
        )}

        {view === "assets" && (
          <Panel
            title="Asset registry"
            info="All seeded base assets — wells, pipelines, gathering, facilities — plus their cost profiles."
            meta={
              <span className="muted">
                {assets.length} asset{assets.length === 1 ? "" : "s"} · {scenarios.length} saved
                scenario{scenarios.length === 1 ? "" : "s"}
              </span>
            }
          >
            <div
              className="row"
              style={{ marginBottom: 10, gap: 10, flexWrap: "wrap" }}
            >
              <button
                className="primary"
                onClick={() => void refreshAssets()}
                disabled={assetsLoading}
                title="Reload assets and any new scenario-derived cases"
              >
                {assetsLoading ? "Refreshing..." : "Refresh assets & cases"}
              </button>
              <span className="muted" style={{ fontSize: 11 }}>
                Cases also refresh automatically after a scenario run or CSV save.
              </span>
            </div>
            <AssetTable
              assets={assets}
              onSelect={(a) => {
                onLoadAsset(a.id);
                setView("scenario");
              }}
            />
          </Panel>
        )}

        {view === "compare" && (
          <Panel
            title="Scenario compare"
            info="Saved cases side-by-side — NPV bars, breakeven bars, plus a generated PDF report."
            meta={<span className="muted">Saved runs · NPV · breakeven · payback</span>}
          >
            <ScenarioCompare
              refreshKey={refreshKey}
              onScenarioDeleted={() => {
                bumpRefreshKey();
                void refreshAssets();
              }}
            />
          </Panel>
        )}

        {view === "history" && (
          <Panel
            title="Case History"
            info="Full audit trail of every saved scenario with one-line result descriptions and recommendations."
            meta={
              <span className="muted">
                Every saved case · click load to hydrate the Scenario form
              </span>
            }
          >
            <CaseHistory
              refreshKey={refreshKey}
              onScenarioDeleted={() => {
                bumpRefreshKey();
                void refreshAssets();
              }}
              onLoadScenario={(sc) => {
                onLoadSavedScenario(sc);
                setView("scenario");
              }}
            />
          </Panel>
        )}

        {view === "economics" && (
          <Panel
            title="Petroleum Economics — flow charts"
            info="Educational primer: scenario workflow, key CAPEX/OPEX inputs, and regional fiscal considerations."
            meta={
              <span className="muted">
                workflow · CAPEX · OPEX · regional considerations
              </span>
            }
          >
            <PetroleumEconomics />
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
