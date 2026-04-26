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
  template is human-readable. The Scenario tab and API expect fractions
  (e.g. `0.45`), so divide by 100 when wiring this up to the API.
- `initial_rate_boe_month` is a normalized BOE/month figure; the API exposes
  separate streams (`initial_oil_bopd`, `initial_gas_mcfd`, `initial_ngl_bpd`).
  Convert before posting (1 mcf ≈ 1/6 BOE).
- Regime-specific columns are blank for rows that don't use that regime.
- `notes` is freeform.

### Loading into the app

The Scenario tab has a **Reset** button that restores the base defaults
(`DEFAULT_INPUTS` in `frontend/src/components/ScenarioForm.tsx`). Reset clears
any previously loaded asset profile so values stick — pick a profile again
from the "Load asset profile" dropdown to re-hydrate.

For batch CSV import, see the **CSV Exchange** tab.
