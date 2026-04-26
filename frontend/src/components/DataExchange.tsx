import { useState } from "react";
import type { Asset, ScenarioInputs, ScenarioResult } from "../lib/api";
import { downloadText, parseCsv, toCsv } from "../lib/csv";
import { mapCsvRowToInputs, type ParsedScenarioRow } from "../lib/scenarioCsv";

type ImportError = { fileName: string; message: string };

export function DataExchange({
  inputs,
  onImportInputs,
  onLoadScenario,
  result,
  assets,
}: {
  inputs: ScenarioInputs;
  onImportInputs: (inputs: ScenarioInputs) => void;
  onLoadScenario?: (inputs: ScenarioInputs) => void;
  result: ScenarioResult | null;
  assets: Asset[];
}) {
  const [rows, setRows] = useState<ParsedScenarioRow[]>([]);
  const [fileName, setFileName] = useState<string>("");
  const [error, setError] = useState<ImportError | null>(null);
  const [loadedIndex, setLoadedIndex] = useState<number | null>(null);

  const exportInputs = () => {
    downloadText("asset-pulse-scenario-inputs.csv", toCsv([inputs]));
  };

  const exportCashFlow = () => {
    if (!result) return;
    const rowsOut = result.monthly.months.map((month, i) => ({
      asset_name: result.asset_name,
      month,
      net_revenue: result.monthly.net_revenue[i],
      opex: result.monthly.opex[i],
      sustaining_capex: result.monthly.sustaining_capex[i],
      dev_capex: result.monthly.dev_capex[i],
      abandonment: result.monthly.abandonment[i],
      free_cash_flow: result.monthly.free_cash_flow[i],
      oil_bbl: result.monthly.oil_bbl[i],
      gas_mcf: result.monthly.gas_mcf[i],
      water_bbl: result.monthly.water_bbl[i],
    }));
    downloadText("asset-pulse-cash-flow-export.csv", toCsv(rowsOut));
  };

  const exportAssets = () => {
    const rowsOut = assets.map((asset) => ({
      id: asset.id,
      name: asset.name,
      asset_type: asset.asset_type,
      region: asset.region ?? "",
      initial_oil_bopd: asset.cost_profile?.decline_inputs?.initial_oil_bopd ?? "",
      annual_decline: asset.cost_profile?.decline_inputs?.annual_decline ?? "",
      fixed_opex_per_month: asset.cost_profile?.opex_inputs?.fixed_opex_per_month ?? "",
      capex_inputs_json: asset.cost_profile?.capex_inputs ? JSON.stringify(asset.cost_profile.capex_inputs) : "",
      metadata_json: asset.metadata ? JSON.stringify(asset.metadata) : "",
    }));
    downloadText("asset-pulse-asset-register.csv", toCsv(rowsOut));
  };

  const importCsvFile = async (file: File | null) => {
    if (!file) return;
    setError(null);
    setLoadedIndex(null);
    try {
      const text = await file.text();
      const raw = parseCsv(text);
      if (raw.length === 0) {
        setRows([]);
        setFileName(file.name);
        setError({ fileName: file.name, message: "No data rows found. Ensure a header row plus at least one row." });
        return;
      }
      const parsed = raw.map((r) => mapCsvRowToInputs(r, inputs));
      setRows(parsed);
      setFileName(file.name);
    } catch (e) {
      setRows([]);
      setError({ fileName: file.name, message: e instanceof Error ? e.message : String(e) });
    }
  };

  const loadRow = (idx: number) => {
    const row = rows[idx];
    if (!row) return;
    setLoadedIndex(idx);
    if (onLoadScenario) {
      onLoadScenario(row.inputs);
    } else {
      onImportInputs(row.inputs);
    }
  };

  return (
    <div>
      <div className="console" style={{ minHeight: 120 }}>
        <span className="ln pre">Asset Pulse // data exchange</span>
        <span className="ln">
          Export current scenario assumptions, export the latest cash flow, or import a scenario CSV.
        </span>
        <span className="ln dim">
          Imports support the multi-row template at examples/asset_pulse_scenario_input_template.csv as well as
          one-row exports from this app. Pick a row and click Load to Scenario to push it into the Scenario tab.
        </span>
      </div>

      <div className="exchange-grid">
        <button className="primary" onClick={exportInputs}>Export scenario inputs</button>
        <button onClick={exportCashFlow} disabled={!result}>Export cash flow</button>
        <button onClick={exportAssets} disabled={assets.length === 0}>Export asset register</button>
        <label className="file-import">
          Import scenario CSV
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={(e) => {
              void importCsvFile(e.target.files?.[0] ?? null);
              e.currentTarget.value = "";
            }}
          />
        </label>
      </div>

      {error && (
        <div className="panel" style={{ borderColor: "var(--bad)", marginTop: 12 }}>
          <div className="body" style={{ color: "var(--bad)", fontSize: 12 }}>
            ! Could not import {error.fileName || "file"}: {error.message}
          </div>
        </div>
      )}

      {rows.length > 0 && (
        <div className="panel" style={{ marginTop: 12 }}>
          <header>
            <h2>Imported scenarios</h2>
            <span className="meta muted">
              {rows.length} row{rows.length === 1 ? "" : "s"} from {fileName}
            </span>
          </header>
          <div className="body" style={{ padding: 0 }}>
            <div style={{ overflowX: "auto" }}>
              <table className="csv-import-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Scenario</th>
                    <th>Asset</th>
                    <th>Regime</th>
                    <th className="right">Oil $/bbl</th>
                    <th className="right">Horizon</th>
                    <th className="right">Decline</th>
                    <th className="right">CAPEX</th>
                    <th>Notes</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, idx) => (
                    <tr key={idx} className={loadedIndex === idx ? "loaded" : ""}>
                      <td className="muted">{idx + 1}</td>
                      <td>{row.scenario_name || "—"}</td>
                      <td>{row.asset_id_or_name || row.inputs.asset_name}</td>
                      <td className="mono-num">{row.inputs.fiscal_regime}</td>
                      <td className="right mono-num">{row.inputs.oil_price.toFixed(2)}</td>
                      <td className="right mono-num">{row.inputs.months_horizon}</td>
                      <td className="right mono-num">{(row.inputs.annual_decline * 100).toFixed(1)}%</td>
                      <td className="right mono-num">
                        {row.inputs.development_capex.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                      </td>
                      <td className="muted" style={{ maxWidth: 240 }}>{row.notes}</td>
                      <td>
                        <button
                          className={loadedIndex === idx ? "ghost" : "primary"}
                          onClick={() => loadRow(idx)}
                          title="Push this row into the Scenario tab"
                        >
                          {loadedIndex === idx ? "Loaded ✓" : "Load to Scenario"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {rows.some((r) => r.warnings.length > 0) && (
              <div style={{ padding: 10, borderTop: "1px solid var(--border)" }}>
                <div className="muted" style={{ fontSize: 11, marginBottom: 4 }}>
                  // Validation notes
                </div>
                <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12 }}>
                  {rows.flatMap((r, idx) =>
                    r.warnings.map((w, j) => (
                      <li key={`${idx}-${j}`} className="muted">
                        Row {idx + 1} ({r.scenario_name || r.asset_id_or_name || r.inputs.asset_name}): {w}
                      </li>
                    )),
                  )}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
