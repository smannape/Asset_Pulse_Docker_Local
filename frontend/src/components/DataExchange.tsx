import { useMemo, useState } from "react";
import {
  apiPost,
  type Asset,
  type ScenarioImportResponse,
  type ScenarioImportRow,
  type ScenarioInputs,
  type ScenarioResult,
} from "../lib/api";
import { downloadText, parseCsv, toCsv } from "../lib/csv";
import { mapCsvRowToInputs, type ParsedScenarioRow } from "../lib/scenarioCsv";

type ImportError = { fileName: string; message: string };

export function DataExchange({
  inputs,
  onImportInputs,
  onLoadScenario,
  onScenariosSaved,
  onResultReady,
  result,
  assets,
}: {
  inputs: ScenarioInputs;
  onImportInputs: (inputs: ScenarioInputs) => void;
  onLoadScenario?: (inputs: ScenarioInputs) => void;
  onScenariosSaved?: () => void;
  onResultReady?: (result: ScenarioResult, inputs: ScenarioInputs) => void;
  result: ScenarioResult | null;
  assets: Asset[];
}) {
  const [rows, setRows] = useState<ParsedScenarioRow[]>([]);
  const [fileName, setFileName] = useState<string>("");
  const [error, setError] = useState<ImportError | null>(null);
  const [loadedIndex, setLoadedIndex] = useState<number | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [saving, setSaving] = useState(false);
  const [importing, setImporting] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const [saveErr, setSaveErr] = useState<string | null>(null);

  const allSelected = rows.length > 0 && selected.size === rows.length;
  const selectedCount = selected.size;

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
    setSelected(new Set());
    setSaveMsg(null);
    setSaveErr(null);
    setImporting(true);
    try {
      const text = await file.text();
      const raw = parseCsv(text);
      if (raw.length === 0) {
        setRows([]);
        setFileName(file.name);
        setError({
          fileName: file.name,
          message: "No data rows found. Ensure a header row plus at least one row.",
        });
        return;
      }
      const parsed: ParsedScenarioRow[] = [];
      raw.forEach((r, idx) => {
        try {
          parsed.push(mapCsvRowToInputs(r, inputs));
        } catch (rowErr) {
          parsed.push({
            scenario_name: r["scenario_name"] ?? `row-${idx + 1}`,
            asset_id_or_name: r["asset_id_or_name"] ?? "",
            notes: r["notes"] ?? "",
            inputs: { ...inputs },
            warnings: [
              `Could not parse row: ${rowErr instanceof Error ? rowErr.message : String(rowErr)}`,
            ],
          });
        }
      });
      setRows(parsed);
      setFileName(file.name);
      // Default-select all parsed rows so the user can hit Save & Run immediately.
      setSelected(new Set(parsed.map((_, i) => i)));
    } catch (e) {
      setRows([]);
      setError({
        fileName: file.name,
        message: e instanceof Error ? e.message : String(e),
      });
    } finally {
      setImporting(false);
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

  const toggleRow = (idx: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const toggleAll = () => {
    setSelected(allSelected ? new Set() : new Set(rows.map((_, i) => i)));
  };

  const saveSelected = async (run: boolean) => {
    if (selectedCount === 0) return;
    setSaving(true);
    setSaveMsg(null);
    setSaveErr(null);
    try {
      const orderedIdx = Array.from(selected).sort((a, b) => a - b);
      const orderedRows = orderedIdx.map((idx) => rows[idx]);
      const payload: { rows: ScenarioImportRow[]; run: boolean; source: string } = {
        rows: orderedRows.map((r) => ({
          scenario_name: r.scenario_name || undefined,
          asset_id_or_name: r.asset_id_or_name || undefined,
          notes: r.notes || undefined,
          inputs: r.inputs,
        })),
        run,
        source: "csv_import",
      };
      const resp = await apiPost<ScenarioImportResponse>("/api/scenarios/import", payload);
      const errCount = resp.errors.length;
      const okCount = resp.saved.length;
      const idDetails = resp.saved
        .map((s) => `#${s.scenario_id}${s.ran ? " ✓" : ""}`)
        .join(", ");
      setSaveMsg(
        `${okCount} of ${orderedRows.length} scenario${okCount === 1 ? "" : "s"} ${run ? "saved & run" : "saved"} ` +
          `(${idDetails || "none"})` +
          (errCount > 0 ? ` · ${errCount} error${errCount === 1 ? "" : "s"}` : ""),
      );
      if (errCount > 0) {
        setSaveErr(
          resp.errors.map((e) => `Row ${e.row}: ${e.error}`).join("; "),
        );
      }
      if (onScenariosSaved) onScenariosSaved();

      // After Save & Run, surface the FIRST run's full result into the visible
      // Scenario panel so the user immediately sees economics for what they
      // just imported. We re-run via /api/scenarios/{id}/run because /import
      // only returns summary KPIs, not the monthly cash flow needed to render
      // the report panel + chart.
      if (run && resp.saved.length > 0 && onResultReady) {
        const first = resp.saved[0];
        const firstRow = orderedRows[0];
        try {
          const fullResult = await apiPost<ScenarioResult>(
            `/api/scenarios/${first.scenario_id}/run`,
            firstRow.inputs,
          );
          onResultReady(fullResult, firstRow.inputs);
        } catch (rerunErr) {
          // Don't fail the whole save just because the visible-panel refresh
          // couldn't fetch — the rows are already persisted and visible in
          // Scenario Compare.
          setSaveErr(
            (prev) =>
              `${prev ? prev + "; " : ""}` +
              `could not refresh result panel: ${
                rerunErr instanceof Error ? rerunErr.message : String(rerunErr)
              }`,
          );
        }
      }
    } catch (e) {
      setSaveErr(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const importSummary = useMemo(() => {
    if (rows.length === 0) return null;
    return `${rows.length} row${rows.length === 1 ? "" : "s"} from ${fileName}`;
  }, [rows, fileName]);

  return (
    <div>
      <div className="console" style={{ minHeight: 120 }}>
        <span className="ln pre">Asset Pulse // data exchange</span>
        <span className="ln">
          Export current scenario assumptions, export the latest cash flow, or import a scenario CSV.
        </span>
        <span className="ln dim">
          Imports support the multi-row template at examples/asset_pulse_scenario_input_template.csv as well as
          one-row exports from this app. Tick the rows you want to keep, then click Save &amp; Run to push them
          into the database — they will appear in the Scenario Compare and Asset tabs.
        </span>
      </div>

      <div className="exchange-grid">
        <button className="primary" onClick={exportInputs}>Export scenario inputs</button>
        <button onClick={exportCashFlow} disabled={!result}>Export cash flow</button>
        <button onClick={exportAssets} disabled={assets.length === 0}>Export asset register</button>
        <label className="file-import">
          {importing ? "Importing..." : "Import scenario CSV"}
          <input
            type="file"
            accept=".csv,text/csv"
            disabled={importing}
            onChange={(e) => {
              const file = e.target.files?.[0] ?? null;
              // Reset the input value synchronously so re-selecting the same
              // file still fires onChange. The import itself runs in a
              // microtask and never blocks render.
              e.currentTarget.value = "";
              void importCsvFile(file);
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
            <span className="meta muted">{importSummary}</span>
          </header>
          <div className="body" style={{ padding: 0 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 12,
                padding: 10,
                borderBottom: "1px solid var(--border-soft)",
                flexWrap: "wrap",
              }}
            >
              <span className="muted" style={{ fontSize: 12 }}>
                {selectedCount} of {rows.length} selected
              </span>
              <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
                <button onClick={toggleAll} title="Toggle all rows">
                  {allSelected ? "Deselect all" : "Select all"}
                </button>
                <button
                  onClick={() => void saveSelected(false)}
                  disabled={selectedCount === 0 || saving}
                  title="Save selected rows to the database without running economics"
                >
                  Save approved
                </button>
                <button
                  className="primary"
                  onClick={() => void saveSelected(true)}
                  disabled={selectedCount === 0 || saving}
                  title="Save selected rows and run economics — results land in Scenario Compare"
                >
                  {saving ? "Saving..." : "Save & Run"}
                </button>
              </div>
            </div>
            {saveMsg && (
              <div
                className="ln"
                style={{ padding: "8px 10px", color: "var(--good)", fontSize: 12 }}
              >
                {saveMsg}
              </div>
            )}
            {saveErr && (
              <div
                className="ln"
                style={{ padding: "8px 10px", color: "var(--bad)", fontSize: 12 }}
              >
                ! {saveErr}
              </div>
            )}
            <div style={{ overflowX: "auto" }}>
              <table className="csv-import-table">
                <thead>
                  <tr>
                    <th style={{ width: 36 }}>
                      <input
                        type="checkbox"
                        checked={allSelected}
                        onChange={toggleAll}
                        aria-label="Toggle all"
                      />
                    </th>
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
                      <td>
                        <input
                          type="checkbox"
                          checked={selected.has(idx)}
                          onChange={() => toggleRow(idx)}
                          aria-label={`Select row ${idx + 1}`}
                        />
                      </td>
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
