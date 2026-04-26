# Asset Pulse Application Help

## Purpose

Asset Pulse is an oilfield forecasting and decision-support dashboard for evaluating well, pipeline, gathering-center and facility profitability under uncertainty. The application combines a React frontend with a Python FastAPI calculation backend and PostgreSQL/Neon storage.

Use it to:

- Build a monthly production and cash-flow case.
- Test CAPEX and OPEX overrun sensitivity.
- Estimate NPV, PV-10, payback, economic limit, EUR and netback.
- Compare exponential, hyperbolic and harmonic decline assumptions.
- Run tornado and Monte Carlo uncertainty analysis.
- Stack operational events such as downtime, price drops, OPEX escalation, restart cost and CAPEX overrun.
- Rank wells using a weighted shut-in/restart decision matrix.
- Export assumptions, cash flows and asset registers to CSV for Excel or database handoff.

## Application Layout

### Top Navigation

The top navigation switches between the main work areas:

| View | Purpose |
| --- | --- |
| Scenario | Build and run one asset economic case. |
| Sensitivity | Run tornado sensitivity and Monte Carlo uncertainty. |
| Events | Apply event impacts to a base NPV case. |
| Decision Matrix | Rank assets for keep-online, choke-back, shut-in or restart decisions. |
| Assets | View seeded wells, pipelines, gathering systems and facilities. Includes a Refresh cases button. |
| Scenario Compare | Compare every saved scenario by NPV, breakeven oil, payback and EUR. |
| CSV Exchange | Export/import assumptions and outputs. Approve/save imported rows to the database. |

### Left Command Rail

The command rail shows:

- Current loaded asset.
- Scenario horizon.
- CAPEX and OPEX multipliers.
- API status.
- Database backend currently used by the API.
- Active view.

### Theme Toggle

Use `[ DARK ]` or `[ LIGHT ]` in the top-right corner to switch between light and dark mode. The theme uses React state only and does not store cookies or browser local storage.

## Scenario View

The Scenario view is the main economic model.

### Running a Base Case

1. Open `Scenario`.
2. Select an asset profile from `Load asset profile`, or keep `Custom well`.
3. Review the key assumptions:
   - Horizon in months.
   - First-year decline.
   - Decline model.
   - b-factor.
   - Initial oil and gas rates.
   - Oil price.
   - Fixed OPEX.
   - Development CAPEX.
   - Discount rate.
   - CAPEX and OPEX multipliers.
4. Keep `Apply economic limit truncation` enabled if you want the model to stop production once the well becomes uneconomic.
5. Click `Run scenario`.

### Reset Button

The `Reset` button on the Scenario form restores every input — normal numeric fields, the fiscal regime, and all advanced/regime-specific fields — to the application defaults defined in `DEFAULT_INPUTS` (`frontend/src/components/ScenarioForm.tsx`). It also clears the `Load asset profile` selection so a previously loaded asset cannot silently re-hydrate the form. To work from an asset profile after Reset, pick the asset again from the dropdown.

### Sample Scenario CSV

A starter template with five regime examples (US royalty/tax, NOC internal, PSC, TSC, concession/tax-royalty) is checked in at `examples/asset_pulse_scenario_input_template.csv`. Use it as the column reference when wiring up batch loads or external spreadsheets.

### Key Inputs

| Input | Meaning |
| --- | --- |
| Asset name | Label for the scenario report. |
| Horizon | Number of months to project. |
| First-year decline | Effective production decline during the first year. |
| Decline model | Exponential, hyperbolic or harmonic production decline. |
| b-factor | Arps hyperbolic b-factor; used only for hyperbolic/harmonic decline. |
| Initial oil | Starting oil production rate in BOPD. |
| Initial gas | Starting gas production rate in MCFD. |
| Oil price | Realized oil price in USD/bbl. |
| Fixed OPEX | Monthly fixed lease/facility cost. |
| Development CAPEX | Initial capital at month zero. |
| Discount rate | Annual discount rate for NPV. |
| CAPEX multiplier | Scenario factor for capital overrun or saving. |
| OPEX multiplier | Scenario factor for operating cost escalation or saving. |

### Advanced Inputs

Open `Advanced fiscal, fluid, OPEX and ARO inputs` to edit:

- NGL rate.
- Water cut start and end.
- Gas and NGL prices.
- Royalty.
- Production tax.
- Transport and processing cost.
- Variable oil/gas/water operating costs.
- Sustaining CAPEX.
- Abandonment/ARO cost.
- **Fiscal / Cost Regime** (see below).

### Fiscal / Cost Regime

A single dropdown inside the advanced section controls how the base monthly cash flow is partitioned between contractor and host government. The default `US royalty/tax` keeps existing behaviour (royalty and production tax already netted in revenue). Selecting any other regime swaps the contractor view into NPV, PV-10, payback, and the cash-flow chart. The full per-month breakdown is returned under `result.fiscal` and summarised in the analysis report.

| Regime                          | What it does                                                                                                                                                                                                                                                                                            | Key inputs                                                                                                                                                            |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `us_royalty_tax` (default)      | No-op layer; reports the existing US royalty + production tax netback.                                                                                                                                                                                                                                  | None.                                                                                                                                                                 |
| `noc_internal`                  | Gross project economics with optional government transfer and corporate tax (default 0% / 0%) for NOC internal screening.                                                                                                                                                                              | Gov transfer %, corp tax %.                                                                                                                                           |
| `psc_cost_recovery`             | PSC/EPSA: gross → royalty → available cost oil = (gross−royalty)×ceiling → actual cost oil = min(opex+capex×(1+uplift)+carry, available) → profit oil split (gov / contractor) → contractor tax. Unrecovered costs carry forward.                                                                                  | Royalty %, cost-oil ceiling %, contractor profit share %, contractor tax %, CAPEX uplift %.                                                                           |
| `technical_service_contract`    | TSC/RSC (Iraq-style): contractor reimbursed for eligible petroleum costs subject to a periodic cap (share of gross revenue) plus a flat remuneration $/BOE. Carry-forward for unpaid eligible costs. No hydrocarbon ownership.                                                                          | Payment cap % of revenue, remuneration $/BOE, contractor tax %.                                                                                                       |
| `concession_tax_royalty`        | Middle East concession with royalty (flat or progressive) plus upstream income tax. Optional Saudi-style progressive royalty: 15% on the first $70/bbl, 45% from $70-$100, 80% above $100; income tax 50% (AGSI).                                                                                       | Flat royalty % or progressive toggle, income tax %.                                                                                                                   |

References: Bindemann/Oxford Energy WPM 25 (1999); Daily Jus on Omani EPSA disputes (2024); PMC fiscal-regimes review (PMC7798991); AGSI Aramco analysis.

### Outputs

The KPI strip and analysis report show:

- NPV.
- PV-10.
- Payback.
- Netback/BOE.
- EUR in BOE.
- Economic limit.
- Truncation status.
- Discount rate.
- Decline model.
- First 12 months of projected cash flow.
- Profitability commentary.

The cash-flow projection panel displays monthly free cash flow and cumulative free cash flow.

## Sensitivity View

The Sensitivity view contains two uncertainty tools.

### Tornado Sensitivity

Click `Run tornado sensitivity` to test one-variable-at-a-time NPV swings.

Default drivers include:

- Oil price.
- Initial oil rate.
- Annual decline.
- CAPEX multiplier.
- OPEX multiplier.
- Discount rate.
- Final water cut.

Use this view to identify the biggest value driver before running a broader Monte Carlo simulation.

### Monte Carlo

Click `Run Monte Carlo` to simulate NPV uncertainty.

Default uncertainty distributions:

- Oil price triangular distribution.
- CAPEX multiplier triangular distribution.
- OPEX multiplier triangular distribution.

Outputs:

- P10 NPV.
- P50 NPV.
- P90 NPV.
- Mean NPV.
- Standard deviation.
- Minimum and maximum simulated NPV.
- Downside risk commentary.

Use P10 as the downside case, P50 as the median case and P90 as the upside case.

## Events View

The Events view stacks operational or commercial shocks on top of the current scenario result.

Typical event types:

- CAPEX overrun.
- Downtime.
- Price drop.
- OPEX escalation.
- Restart cost.

Workflow:

1. Run a scenario first.
2. Open `Events`.
3. Add one or more events.
4. Review each event’s NPV impact.
5. Review the final adjusted NPV.

Use this view for “what happens if” analysis after the base case is already understood.

## Decision Matrix View

The Decision Matrix ranks wells or assets for operational decisions.

Default decisions include:

- Keep online.
- Review manually.
- Choke back.
- Shut in.
- Restart.

The scoring model considers:

- Monthly margin.
- NPV if kept online.
- Avoidable OPEX.
- Restart payback.
- Restart risk.
- HBP or lease-retention risk.
- Water burden.
- Strategic value.

Click `Score matrix` to recompute recommendations after editing assumptions.

Use this view when production curtailment or restart choices require more than a simple monthly margin test.

## Assets View

The Assets view lists seeded sample assets:

- Wells.
- Pipelines.
- Facilities.
- Gathering-center style assets.

Click `load` to push an asset profile into the Scenario form.

### Refresh Cases

The view also exposes a **Refresh cases** button. Use it when CSV imports or
scenario runs in another tab created new cases that are not yet visible. The
app also auto-refreshes the asset list whenever a scenario is run or saved
through CSV Exchange — Refresh cases is the manual fallback if the
auto-refresh missed a change because of a network blip.

In production, replace the seeded sample data with your actual AFE, LOE, production, water, facility and midstream data.

## Scenario Compare View

The Scenario Compare view is a portfolio-level table and chart of every saved
scenario in the database. It loads from `GET /api/scenarios?limit=100` and
shows:

- Scenario name and asset alias (e.g. `asset1`, `asset2`).
- Fiscal regime and source (`api`, `csv_import`, `manual`).
- NPV (positive in green, negative in red), PV-10 and payback.
- **Breakeven oil price** — the bisection-derived USD/bbl that drives NPV to ~zero, holding all other inputs constant. The KPI is computed once when the scenario is saved and cached on `scenario_results.breakeven_oil_price`.
- Netback per BOE and EUR (BOE).

Below the table, two simple SVG-style bars rank the cases by:

1. NPV (signed, with a midline).
2. Breakeven oil price (lower bar = more resilient case).

A **Refresh** button reloads the saved list. A free-text filter narrows the
view by name, asset, regime or source. **Sort** orders by newest, NPV,
breakeven or payback. The `delete` action on each row removes a saved
scenario from the database.

Scenarios appear here automatically when:

- You click **Run scenario** on the Scenario tab — runs persist by default.
- You click **Save approved** or **Save & Run** in CSV Exchange.

## CSV Exchange View

The CSV Exchange view supports Excel-oriented workflows.

### Export Scenario Inputs

Click `Export scenario inputs` to download a one-row CSV containing current scenario assumptions.

Use this when:

- You want to review assumptions in Excel.
- You want to create scenario templates.
- You want to send assumptions to another engineer for review.

### Import Scenario CSV

Use `Import scenario CSV` to upload either:

- a one-row export from `Export scenario inputs`, or
- the multi-row template at `examples/asset_pulse_scenario_input_template.csv`.

After import, every row in the file is shown in an **Imported scenarios** table
with scenario name, asset, regime and key economics. Click `Load to Scenario`
on the row you want to evaluate. The app:

1. Pushes the parsed inputs into the Scenario form (overwriting current values).
2. Clears any stale result so the next `Run scenario` reflects the new case.
3. Switches to the **Scenario** tab automatically so you can review and run.

### Approve & Save Imported Rows

Each parsed row also gets a checkbox. Tick the rows you want to keep, then:

- **Save approved** — persists the inputs to the database without running
  economics. Useful for staging future scenarios.
- **Save & Run** — persists each row, runs `project_scenario` server-side,
  and stores the resulting NPV, payback, breakeven oil price and monthly
  summary on `scenario_results`. The saved IDs are echoed back in the
  feedback line; the rows then appear in the **Scenario Compare** tab and
  in the Assets view (after a refresh).

Behind the scenes the UI POSTs to `/api/scenarios/import` with one payload
containing all selected rows. Each row stores `asset_id_or_name` as
`scenarios.asset_alias`. If that alias matches an existing asset by id or
case-insensitive name, the foreign key `scenarios.asset_id` is also set —
otherwise only the alias is kept and the existing asset table is left
untouched, so naming new cases like `asset1`, `asset2` etc. is safe.

Rules:

- Column names are case- and underscore-insensitive. Both raw API field
  names (e.g. `oil_price`) and template column names (e.g. `oil_price_usd_bbl`)
  are recognised.
- Percentage columns in the template (e.g. `decline_rate_annual_pct = 45`,
  `royalty_rate_pct = 18.75`) are converted to the fractions the API expects
  (`0.45`, `0.1875`).
- `scenario_name`, `asset_id_or_name` and `notes` are kept as display
  metadata; the form's **Asset name** field falls back to `asset_id_or_name`
  when no `asset_name` column is present.
- `apply_economic_limit` and `concession_royalty_progressive` accept
  `true`/`false`/`yes`/`no`/`1`/`0`.
- Blank fiscal/regime cells are ignored — the regime defaults stay in place.
- Invalid numeric or boolean cells are listed under **Validation notes**
  beneath the imported table; the rest of the row still loads.
- Columns the app does not recognise (e.g. `working_interest_pct`,
  `downtime_months`) are ignored without error.

### Export Cash Flow

After running a scenario, click `Export cash flow` to download monthly results.

The export includes:

- Month.
- Net revenue.
- OPEX.
- Sustaining CAPEX.
- Development CAPEX.
- Abandonment.
- Free cash flow.
- Oil, gas and water volumes.

### Export Asset Register

Click `Export asset register` to export all currently loaded assets and compact JSON assumptions.

## Recommended Workflow

1. Load an asset or build a custom well case.
2. Run Scenario and inspect KPIs. The result is automatically saved.
3. Switch the decline model and compare exponential vs hyperbolic economics.
4. Run Tornado to identify dominant drivers.
5. Run Monte Carlo to quantify distribution risk.
6. Add Events to test operational shocks.
7. Use Decision Matrix for keep-online, choke-back, shut-in or restart calls.
8. Export scenario and cash flow CSVs for documentation.

### Portfolio Workflow (CSV Import → Compare)

1. Build a multi-row CSV from `examples/asset_pulse_scenario_input_template.csv`.
   Use distinct asset aliases such as `asset1`, `asset2`, ... in the
   `asset_id_or_name` column.
2. Open **CSV Exchange**, click `Import scenario CSV`.
3. Review the parsed rows, untick anything you do not want stored, then click
   **Save & Run**.
4. Open **Scenario Compare** to inspect NPV, breakeven oil price and payback
   side-by-side; sort or filter to spot the best case.
5. Open **Assets** and click **Refresh cases** if the new scenarios are not
   already visible.
9. Persist or seed production data in Neon once validated.

## Interpretation Notes

- NPV is sensitive to price, production decline, water handling cost and fixed OPEX.
- Economic limit truncation is useful for marginal wells, but lease obligations, HBP status, restart risk and strategic value must still be considered.
- Monte Carlo ranges are only as good as the distribution assumptions.
- Hyperbolic decline preserves more tail production than exponential decline for the same first-year decline assumption.
- The tool is a decision-support model, not a substitute for final reserves, accounting, tax or regulatory review.

## Troubleshooting

| Issue | Likely Cause | Fix |
| --- | --- | --- |
| API unreachable | FastAPI backend is not running or CORS is wrong. | Check backend host, `/api/health`, and `CORS_ORIGINS`. |
| Database shows SQLite fallback | `DATABASE_URL` is missing on backend host. | Set Neon pooled `DATABASE_URL` and restart backend. |
| Netlify page loads but calculations fail | Frontend cannot reach FastAPI. | Set `VITE_API_BASE_URL` or configure Netlify proxy redirect. |
| Scenario import shows no rows | File has only a header line, or commas inside cells are unquoted. | Verify at least one data row and quote any cell containing a comma. |
| Loaded row values look wrong by 100× | Columns named `*_pct` were already entered as fractions instead of percentages. | The template treats `*_pct` columns as percentages — enter `45` for 45%, not `0.45`. |
| Imported numbers ignored | Cell contains text or units the parser can't strip (e.g. `45 percent`). | Use plain numbers; `$`, `,`, `_`, spaces, and a trailing `%` are stripped automatically. |
| Monte Carlo is slow | Iterations are high or backend host is cold-starting. | Start with 500–1000 iterations; increase after deployment is stable. |
| Results look too optimistic | Decline, water cut, OPEX or abandonment assumptions may be too low. | Test downside cases in Tornado and Monte Carlo. |

## Production Readiness Checklist

- Replace seeded sample data with operator-specific data.
- Connect backend to Neon using pooled `DATABASE_URL`.
- Set Netlify `VITE_API_BASE_URL` to the deployed FastAPI URL.
- Set backend `CORS_ORIGINS` to the Netlify domain.
- Add authentication before exposing internal economics publicly.
- Add role-based data access for multi-user production use.
- Validate fiscal terms and tax logic for the operating region.
- Back up Neon data before bulk imports.
