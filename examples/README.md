# Asset Pulse — Examples

## `asset_pulse_scenario_input_template.csv`

Sample input template for batch scenario data. The columns map to fields on the
`/api/scenario/run` request body and the Scenario tab form. Rows cover the five
fiscal regimes the engine supports today:

| Regime | Sample row |
| --- | --- |
| `us_royalty_tax` | US Permian Base |
| `noc_internal` | NOC Internal Cost Recovery |
| `psc_cost_recovery` | Indonesia PSC |
| `technical_service_contract` | Iraq TSC |
| `concession_tax_royalty` | Saudi Concession |

### Column notes

- Rates are entered as **percentages** in the CSV (e.g. `45` = 45%) so the
  template is human-readable. The CSV Exchange import converts these to the
  fractions (`0.45`) that the API expects automatically.
- `initial_rate_boe_month` is a normalised BOE/month figure; the API exposes
  separate streams (`initial_oil_bopd`, `initial_gas_mcfd`, `initial_ngl_bpd`).
  The importer does **not** split a combined BOE rate, so set the per-stream
  values directly when you want non-zero gas/NGL.
- Regime-specific columns are blank for rows that don't use that regime —
  blanks are ignored, regime defaults stick.
- `scenario_name`, `asset_id_or_name` and `notes` are kept as display
  metadata; they don't go to the API but are shown in the import table.
- `working_interest_pct`, `net_revenue_interest_pct`, `downtime_months` and
  `downtime_start_month` are not currently mapped to API fields and are
  ignored on import.

### Loading into the app

1. Open the app and switch to **CSV Exchange**.
2. Click **Import scenario CSV** and pick this file (or any one-row export
   from **Export scenario inputs**).
3. The **Imported scenarios** table lists every row with scenario name,
   asset, regime, oil price, horizon, decline and CAPEX.
4. Click **Load to Scenario** on the row you want to evaluate. The app
   pushes those values into the Scenario form, clears any stale result,
   and switches to the Scenario tab.
5. Review the form (the **Advanced** drawer holds fiscal/regime fields)
   and click **Run scenario**.

### Resetting after a load

The Scenario tab's **Reset** button restores `DEFAULT_INPUTS` from
`frontend/src/components/ScenarioForm.tsx` and clears the asset-profile
dropdown so a previously loaded asset cannot silently re-hydrate the form.
After Reset, pick the asset again from the dropdown or re-import the CSV
to start from a known case.
