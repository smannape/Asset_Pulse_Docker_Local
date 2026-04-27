# Help Me — Calculation Guide for CAPEX, OPEX & Fiscal Inputs

This guide explains how to populate every advanced CAPEX, OPEX and fiscal field
on the Asset Pulse Scenario form (and in the multi-row CSV template at
`examples/asset_pulse_scenario_input_template.csv`). Each section gives you the
**meaning, how to estimate it, a working formula or example, QA checks, and
operator-specific notes** for the three archetypes Asset Pulse is most often
used for:

- **NOC** — National Oil Company running an internal screening view (e.g.
  Saudi Aramco, ADNOC, Petrobras, Pemex, Sonatrach).
- **IOC** — International Oil Company under a host-government contract such as
  a PSC, TSC or concession (e.g. ExxonMobil, Shell, TotalEnergies, BP).
- **US Independent** — onshore US working-interest operator under
  lease-royalty + severance-tax economics (e.g. shale operator in the Permian,
  Eagle Ford, Bakken).

> **Disclaimer**: Asset Pulse is a decision-support tool. The numbers below
> are typical reference ranges drawn from the public sources cited inline.
> They are not legal, tax or accounting advice. Always validate fiscal terms,
> royalty schedules and tax rates against the actual contract or local
> regulator.

---

## 1. Operating cost inputs

### 1.1 `fixed_opex_usd_month`

**Meaning.** The lease/facility/operator fixed cost that you incur every month
even if the well chokes back to zero — pumper/operator labour, surface
equipment rental, SCADA/comms, road and lease maintenance, regulatory
reporting. This is the classic "fixed lifting cost" component of LOE.

**How to estimate.**

1. Pull last 12 months of LOE/AFE actuals from the accounting system.
2. Strip out anything that scales with production (chemicals, electricity,
   water disposal, hauling) — those go into the variable buckets below.
3. Divide the remaining fixed annualised total by 12.

**Formula.**

```
fixed_opex_usd_month  =  (annual fixed lease + facility + labour cost) / 12
```

**Typical ranges** (per the [EIA upstream cost study](https://www.eia.gov/analysis/studies/drilling/pdf/upstream.pdf)
and [Lumel LOE breakdown](https://lumel.com/blog/oil-and-gas/budgeting-loe-lease-operating-expense/)):

| Asset class                       | Fixed OPEX USD/month |
|-----------------------------------|----------------------|
| US shale single horizontal well   | 8,000 – 25,000       |
| Conventional onshore stripper     | 1,500 – 6,000        |
| Mature giant ME field (per well)  | 4,000 – 15,000       |
| Offshore platform (per well slot) | 50,000 – 300,000     |

**QA checks.**
- Re-derive on a $/BOE basis and compare with the [EIA performance profile lifting-cost band](https://www.eia.gov/finance/performanceprofiles/oil_gas.php).
- Make sure you have **not** double-counted variable opex.
- Pumper labour should appear here, not in `variable_opex_usd_boe`.

**Operator notes.**
- **NOC**: Use internal LOE ledger; many giant fields run very low fixed
  per-well costs because headcount and surface infrastructure are pooled
  across the field. State subsidies on diesel/power should be reflected at
  the *delivered* (post-subsidy) price the operator actually pays.
- **IOC**: Use the contractor-bookable share of operating cost, as defined in
  the cost-recovery procedures of the PSC/TSC. Some contracts cap technical
  assistance fees, IT/G&A allocations and parent-company charge-backs.
- **US Independent**: Equals the fixed component of LOE per well. If the
  lease has multiple wells, allocate the lease-level fixed cost across active
  wells using a defensible method (equal split, BOE-weighted, or working
  interest weighted).

### 1.2 `variable_opex_usd_boe`

**Meaning.** All operating cost that scales with production volume —
chemicals, electricity for artificial lift, compression fuel, hauling,
chemical inhibitors, downhole intervention. Charged on every BOE produced.

**How to estimate.**

1. Sum last 12 months of variable LOE line items.
2. Divide by total BOE produced over the same period.

**Formula.**

```
variable_opex_usd_boe  =  annual variable LOE / annual produced BOE
```

**Typical ranges** (cross-checking [Lumel's LOE article](https://lumel.com/blog/oil-and-gas/budgeting-loe-lease-operating-expense/)
against [EIA finance performance profiles](https://www.eia.gov/finance/performanceprofiles/oil_gas.php)):

| Asset class                          | Variable OPEX USD/BOE |
|--------------------------------------|------------------------|
| US shale, low water cut              | 2.5 – 6                |
| US shale, mature high water cut      | 6 – 15                 |
| ME giant onshore, very low water cut | 1 – 3                  |
| Heavy oil / thermal recovery         | 8 – 25                 |

**QA checks.**
- Don't include water-handling cost here — it has its own field.
- Avoid double-counting electricity if your power is netted out of revenue.

**Operator notes.**
- **NOC**: Use realised internal $/BOE; remember that subsidised utilities
  understate cost relative to international benchmarks.
- **IOC**: Make sure variable costs are *recoverable* under the cost-recovery
  rules. Some PSCs disallow specific items (entertainment, parent G&A above a
  cap, financing cost).
- **US Independent**: Pump electricity, gas-lift fuel and methanol injection
  are the typical drivers. Many independents compute this directly from their
  LOS (Lease Operating Statement).

### 1.3 `water_handling_usd_bbl`

**Meaning.** The marginal cost of dealing with one barrel of produced water —
gathering, lift, treatment, hauling, salt-water disposal (SWD) injection
fees. Quoted per **barrel of water**, not per BOE.

**How to estimate.**

```
water_handling_usd_bbl =  (annual water OPEX + SWD / disposal fees) / annual water bbl
```

Reference the water cost discussion in
[the Lumel LOE article](https://lumel.com/blog/oil-and-gas/budgeting-loe-lease-operating-expense/)
and the EIA's note that water handling is a major variable LOE driver in
mature wells ([EIA upstream costs](https://www.eia.gov/analysis/studies/drilling/pdf/upstream.pdf)).

**Typical ranges.**

| System                           | USD/bbl water |
|----------------------------------|---------------|
| Pipeline-connected SWD, dry area | 0.25 – 0.75   |
| Trucked SWD                      | 1.50 – 4.00   |
| Offshore overboard treatment     | 0.10 – 0.30   |
| Steam/thermal cycle reuse        | 0.50 – 2.50   |

**QA checks.**
- Pair with `water_cut_pct` — if water cut grows in the projection, the
  *implied* monthly water cost grows with it. Check that the resulting
  $/BOE water spend in late-life months is still credible.
- Don't include water *injection* CAPEX here — that goes into `capex_total_usd`.

**Operator notes.**
- **NOC**: Brownfield giant fields often have purpose-built water injection
  and disposal grids; per-barrel cost can be very low (< $0.30) but trends up
  as water cut climbs above 85%.
- **IOC**: Confirm whether produced water handling is a recoverable cost or
  treated as the contractor's risk inside the operating fee.
- **US Independent**: Often the single largest variable cost in mature
  Permian wells. Trucking adds $1–$3/bbl over pipeline; line losses are
  another 2–5%.

### 1.4 `water_cut_pct`

**Meaning.** Water as a **percentage of total liquid production** at the end
of the projection horizon (or starting water cut, depending on which UI
field you are filling). Asset Pulse linearly interpolates between start and
end water cut over the horizon.

**How to estimate.** Read the most recent month's well test or production
allocation; project forward using analog wells in the same reservoir.

**Formula.**

```
water_cut_pct  =  100 * water_bbl / (water_bbl + oil_bbl)
```

**Typical ranges.**

- New shale well, year 1: 5 – 30%
- US shale, mature: 60 – 90%
- ME giant onshore mature: 30 – 60% (peripheral water injection)
- North Sea late-life: 80 – 95%

**QA checks.**
- Enter as a **percent** in CSV (e.g. `45` for 45%); the importer converts to
  a fraction internally.
- End-of-life water cut > 95% is rare — sanity check before locking in.

**Operator notes.**
- **NOC**: For peripheral or pattern waterflood, end water cut is often a
  reservoir-engineering output, not a free input.
- **IOC**: A higher water cut in a PSC reduces produced oil and therefore
  shrinks both the cost-recovery base (cost oil) and the contractor's profit
  oil; it materially hurts contractor NPV.
- **US Independent**: Strongly affects netback because every incremental
  water barrel costs `water_handling_usd_bbl` on top of pump electricity.

---

## 2. Scenario multipliers

### 2.1 `capex_multiplier`

**Meaning.** A **ratio** applied to *all* CAPEX (development + sustaining).
`1.0` means use base CAPEX as entered. `1.25` means assume a 25% capital
overrun. `0.9` means a 10% saving versus the base AFE.

**How to set.**

- Use `1.0` for the deterministic base case.
- Use historical AFE-vs-actual variance to centre Monte Carlo distributions.
  Many basins show a P90 overrun of 15–35% on offshore and 5–15% on
  development drilling.

**Formula.**

```
adjusted_capex  =  base_capex * capex_multiplier
```

**Operator notes.**
- **NOC**: Frequently used for fiscal stress tests against
  state-budget-driven price decks.
- **IOC**: The CAPEX multiplier interacts with `capex_uplift_pct` under
  PSCs — overrun hits cash flow but uplift only applies to the *base*
  recoverable CAPEX as defined by the contract.
- **US Independent**: Tornado/Monte Carlo this between 0.9 and 1.3 to capture
  service-cost inflation and rig availability risk.

### 2.2 `opex_multiplier`

**Meaning.** Same idea as the CAPEX multiplier, applied to all OPEX (fixed +
variable + water handling). `1.0` is base. `1.1` is 10% inflation.

**How to set.** Use service-cost inflation indices (BLS for US, IEA for
international); 1.05–1.15 is typical for stress cases.

**Operator notes.**
- **NOC**: Often used to model future labour cost increases under local
  content rules.
- **IOC**: An `opex_multiplier > 1.0` on a TSC chips into the recoverable
  cap directly because TSCs reimburse cost up to a cap.
- **US Independent**: Critical lever — LOE inflation has historically been
  the second-biggest driver of breakeven oil price after the price deck
  itself.

### 2.3 `downtime_months` and `downtime_start_month`

**Meaning.** A contiguous block of months with zero production (e.g.
turnaround, pipeline outage, weather shut-in). `downtime_start_month` is
1-indexed.

**How to set.**

- For unscheduled risk events, use Monte Carlo with a Poisson-style
  occurrence and 1–3 month duration.
- For a planned turnaround, set `downtime_months` and `downtime_start_month`
  directly and re-run the scenario.

**Formula behaviour.** During the downtime block:
- Oil, gas, water volumes go to 0.
- Variable OPEX and water handling drop to 0.
- Fixed OPEX continues (the asset is still being kept hot).
- Royalty, severance and PSC profit oil also drop with revenue.

**QA checks.**
- `downtime_start_month + downtime_months ≤ horizon_months` — otherwise
  most of the downtime falls beyond the projection.
- Set both to `0` to disable.

**Operator notes.**
- **NOC**: Use to model major maintenance turnarounds in long-life giant
  fields.
- **IOC**: PSC cost recovery is limited to the cost-oil **ceiling × revenue**
  — when revenue drops to zero in a downtime month, no costs are recoverable
  that month. Costs carry forward.
- **US Independent**: Use to test winter freeze-offs (Bakken/Anadarko) or
  permit-driven shut-ins.

---

## 3. PSC fiscal inputs (`psc_cost_recovery` regime)

A production sharing contract (PSC) splits production between host
government and contractor through royalty → cost recovery → profit oil →
contractor tax. The mechanics below match the Asset Pulse PSC engine and the
descriptions in
[the PetroSkills introduction to PSCs](https://www.petroskills.com/en/blog/entry/apr21-sub-introduction-to-production-sharing-contracts),
the [Bindemann (1999) Oxford Energy paper](https://www.oxfordenergy.org/wpcms/wp-content/uploads/2010/11/WPM25-ProductionSharingAgreementsAnEconomicAnalysis-KBindemann-1999.pdf),
and the [Oklahoma Law Review summary of PSC structures](https://digitalcommons.law.ou.edu/cgi/viewcontent.cgi?article=1408&context=onej).

### 3.1 `psc_royalty_rate_pct`

**Meaning.** A royalty taken off the top of gross petroleum revenue **before**
cost recovery. Some modern PSCs have no royalty (set to `0`).

**Typical ranges.** 0% – 15% (common: 10%). Bindemann (1999) notes royalty
is often 8–15% where present.

**Formula.**

```
royalty_$  =  gross_revenue * psc_royalty_rate_pct / 100
post_royalty_revenue  =  gross_revenue - royalty_$
```

**QA checks.** Enter percent (10 for 10%), not fraction.

**Operator notes.**
- **NOC**: Often run with royalty = 0 internally, since royalty is just a
  bookkeeping transfer between state and state-owned operator.
- **IOC**: Royalty reduces both the cost-recovery base **and** the profit
  oil base — it is the single most punitive PSC term for a low-margin field.

### 3.2 `psc_cost_recovery_ceiling_pct`

**Meaning.** The **maximum percentage** of (post-royalty) revenue the
contractor can use to recover petroleum costs in any given period.
Unrecovered costs carry forward. Typical: 50%–80% (e.g. Indonesia historic 80%
cost-oil ceiling).

**Formula.**

```
available_cost_oil       =  post_royalty_revenue * psc_cost_recovery_ceiling_pct / 100
recoverable_pool         =  carry_forward + opex + capex * (1 + capex_uplift_pct/100)
recovered_$              =  min(recoverable_pool, available_cost_oil)
new_carry_forward        =  recoverable_pool - recovered_$
```

**QA checks.** A high ceiling (>80%) speeds up cost recovery but can run
afoul of profit-oil minima in some contracts. Make sure your ceiling is
consistent with the contract.

### 3.3 `psc_contractor_profit_oil_share_pct`

**Meaning.** The contractor's **share of profit oil** after cost recovery.
Profit oil = post-royalty revenue minus recovered cost. Typical: 20%–50%,
often on a sliding scale by R-factor or cumulative production.

**Formula.**

```
profit_oil               =  post_royalty_revenue - recovered_$
contractor_profit_oil    =  profit_oil * psc_contractor_profit_oil_share_pct / 100
gov_profit_oil           =  profit_oil - contractor_profit_oil
```

**QA checks.** Asset Pulse uses a single flat contractor share — if the
contract has an R-factor scale, pick a representative average for the period
or run multiple scenarios for the lower/upper plateau.

### 3.4 `contractor_tax_rate_pct`

**Meaning.** The income tax the contractor pays on its taxable petroleum
income (recovered cost + contractor profit oil, depending on the regime). In
many PSCs cost recovery is *not* taxable and only profit oil is — Asset Pulse
applies tax on contractor profit oil + remuneration (TSC) only.

**Typical ranges.** 25% – 55%. Many ME PSCs land around 30–50%.

**Formula.**

```
contractor_after_tax  =  recovered_$ + contractor_profit_oil * (1 - contractor_tax_rate_pct/100)
```

**Operator notes.** This field is reused by the TSC engine to tax
remuneration income.

### 3.5 `capex_uplift_pct`

**Meaning.** Many PSCs allow contractors to recover **more than nominal
CAPEX** (e.g. 110%, 120%) as compensation for time-value-of-money on capital
locked into cost recovery. `0` = no uplift.

**Typical ranges.** 0% – 25%.

**Formula** — already shown in §3.2 (`capex * (1 + capex_uplift_pct/100)`).

**QA checks.** Don't double-count: if you already grossed up base CAPEX
manually, leave uplift at 0%.

---

## 4. TSC fiscal inputs (`technical_service_contract` regime)

Technical service contracts (Iraq-style) reimburse the contractor for
recoverable cost up to a **cap** plus a flat **remuneration fee per BOE**.
The contractor never owns hydrocarbons. Source:
[2B1st Consulting on TSCs](https://2b1stconsulting.com/technical-service-contracts/)
and the [Cornell service contracts review paper](https://clinlawell.dyson.cornell.edu/service_contracts_review_paper.pdf).

### 4.1 `tsc_fee_usd_boe`

**Meaning.** The flat per-BOE remuneration the contractor earns, often
$1–$3/BOE for Iraq-class TSCs.

**Formula.**

```
remuneration_$  =  produced_BOE * tsc_fee_usd_boe
```

**QA checks.** Iraq tender bids in 2009/2010 ranged roughly $1.15 – $5.50/BOE;
above $5/BOE is unusual today.

### 4.2 `tsc_cost_recovery_cap_usd_month`

**Meaning.** A **monthly cap** on petroleum cost reimbursement to the
contractor (in absolute USD/month, not as % of revenue). Eligible costs
above the cap roll forward to future months.

**Formula.**

```
recoverable_pool       =  carry_forward + opex + capex * (1 + capex_uplift_pct/100)
recovered_$            =  min(recoverable_pool, tsc_cost_recovery_cap_usd_month)
new_carry_forward      =  recoverable_pool - recovered_$
contractor_cash_$      =  (recovered_$ + remuneration_$) * (1 - contractor_tax_rate_pct/100)
```

**QA checks.** Set the cap to a realistic absolute number — e.g. $3.5M/month
on a 180 kBOPD field is a tight 0.6 $/BOE recovery limit.

**Operator notes.**
- **IOC**: A TSC behaves more like a fee-for-service contract than a PSC.
  The contractor's economics are driven almost entirely by the fee and the
  cap — production upside accrues to the host.
- **NOC**: TSC is the typical **inverse** view: the host keeps essentially
  all profit oil and pays a defined fee.

---

## 5. Concession fiscal inputs (`concession_tax_royalty` regime)

Concession (or tax-and-royalty) regimes assign hydrocarbons to the licensee
who pays royalty on gross revenue and corporate income tax on taxable
profit. Source:
[ScienceDirect on tax-royalty regimes](https://www.sciencedirect.com/science/article/abs/pii/S0360544207000771),
the [petroleum fiscal regime overview](https://en.wikipedia.org/wiki/Petroleum_fiscal_regime),
and the [Meehan LinkedIn primer on concession regimes](https://www.linkedin.com/pulse/international-petroleum-fiscal-regimes-concessions-schemes-meehan).

### 5.1 `concession_royalty_rate_pct`

**Meaning.** Royalty taken off gross revenue. Asset Pulse also supports a
Saudi-style **progressive** royalty: 15% on the first $70/bbl, 45% from
$70–$100, 80% above $100. Toggle that with `concession_royalty_progressive`
in the form / CSV; otherwise the flat rate is used.

**Typical ranges.** 5% – 20% for flat schedules.

**Formula (flat).**

```
royalty_$  =  gross_revenue * concession_royalty_rate_pct / 100
```

### 5.2 `concession_income_tax_rate_pct`

**Meaning.** Upstream corporate income tax on taxable profit (revenue –
royalty – opex – allowances). Asset Pulse applies it to the post-royalty
operating profit. Saudi AGSI-style upstream tax = 50%.

**Formula.**

```
taxable_income      =  gross_revenue - royalty_$ - opex - depreciation/CAPEX_amortisation
income_tax_$        =  max(taxable_income, 0) * concession_income_tax_rate_pct / 100
contractor_cash_$   =  taxable_income - income_tax_$
```

**QA checks.** Confirm tax rate is the **upstream** rate, which is often
higher than the general corporate rate (50% AGSI vs 20% general in KSA).

---

## 6. NOC vs IOC vs US Independent — what to actually input

| Topic | NOC (internal) | IOC (PSC / TSC / concession) | US Independent (royalty / tax) |
|-------|----------------|------------------------------|-------------------------------|
| Fiscal regime | `noc_internal` | `psc_cost_recovery` / `technical_service_contract` / `concession_tax_royalty` | `us_royalty_tax` |
| Pricing | Internal transfer or government-set | Market basis (Brent, ICE), with marketing fee | WTI - basis differential |
| Royalty / govt take | Often modeled as 0 internally; gov capture via transfer pricing or dividends | Contract royalty + cost recovery + profit oil split | 12.5% – 25% lease royalty |
| Tax | Optional corporate tax (`gov_transfer` field) | `contractor_tax_rate_pct` | Severance + ad valorem ([DW Energy on severance](https://www.dwenergygroup.com/understanding-severance-tax/), [Investopedia: severance tax](https://www.investopedia.com/terms/s/severance-tax.asp)). TX: oil 4.6%, gas 7.5% |
| OPEX | Subsidised utilities, low fixed/BOE in giant fields | Use *recoverable* OPEX subset | Full LOE per LOS |
| CAPEX uplift | Not typical | 0% – 25% | Not applicable |
| Carry-forward of unrecovered cost | Not used | Yes — built into PSC/TSC engines | Not applicable |
| Working interest / NRI | 100% / 100% (state) | Per JOA | WI < 100%, NRI = WI × (1 - royalty - ORRI) |
| Strategic levers | Production continuity, local content, job creation | Cost recovery speed, profit oil share, R-factor | Drilling cadence, hedging, severance optimisation, depletion deductions ([Instead on royalty taxation](https://www.instead.com/resources/blog/how-are-oil-and-gas-royalties-taxed)) |

> **US tax note.** Severance/production taxes are imposed by individual
> states and vary widely. Income-tax effects (depletion, IDC) are
> jurisdiction-specific — Asset Pulse does **not** do US tax planning. For an
> overview see
> [Investopedia on severance tax](https://www.investopedia.com/terms/s/severance-tax.asp);
> for state-by-state rates see
> [DW Energy's severance tax overview](https://www.dwenergygroup.com/understanding-severance-tax/).

---

## 7. Worked examples

### 7.1 US Independent — Permian shale horizontal

```
fiscal_regime                       = us_royalty_tax
oil_price_usd_bbl                   = 72
initial_rate_boe_month              = 21,000
decline_rate_annual_pct             = 45         # entered as percent
months                              = 120
working_interest_pct                = 100
net_revenue_interest_pct            = 81.25      # 100 - 18.75 royalty
royalty_rate_pct                    = 18.75
severance_tax_rate_pct              = 4.5        # TX oil severance
discount_rate_pct                   = 10
capex_total_usd                     = 9,290,000
fixed_opex_usd_month                = 14,000
variable_opex_usd_boe               = 4.50
water_handling_usd_bbl              = 1.50
water_cut_pct                       = 25         # end-of-horizon
capex_multiplier                    = 1.0
opex_multiplier                     = 1.0
```

Sanity: total LOE/BOE in year 1 ≈ fixed_opex_usd_month / monthly_BOE +
variable_opex_usd_boe + water_cost_per_BOE ≈ $0.7 + $4.5 + ($1.5 × 0.33 bbl
water/BOE) ≈ **$5.7/BOE**, in line with Permian peers per
[EIA performance profiles](https://www.eia.gov/finance/performanceprofiles/oil_gas.php).

### 7.2 IOC PSC — Indonesia-style cost recovery

```
fiscal_regime                       = psc_cost_recovery
oil_price_usd_bbl                   = 80
initial_rate_boe_month              = 32,000
decline_rate_annual_pct             = 18
months                              = 150
discount_rate_pct                   = 10
capex_total_usd                     = 42,000,000
fixed_opex_usd_month                = 75,000
variable_opex_usd_boe               = 5.0
water_handling_usd_bbl              = 2.0
water_cut_pct                       = 30
psc_royalty_rate_pct                = 10
psc_cost_recovery_ceiling_pct       = 80
psc_contractor_profit_oil_share_pct = 40
contractor_tax_rate_pct             = 30
capex_uplift_pct                    = 0
capex_multiplier                    = 1.05    # 5% AFE risk
```

Mechanics for month 1 (rough): gross revenue $76.8M (32 kBOPD × 30 × $80) →
royalty $7.68M → post-royalty $69.1M → cost-oil ceiling 80% = $55.3M
available → recover ~$0.85M opex + $42M capex = $42.85M, leaving $26.3M as
profit oil → contractor 40% = $10.5M → tax 30% on profit oil (~$7.4M
after-tax). Contractor also retains the $42.85M of recovered cost. See the
mechanics in the
[PetroSkills PSC primer](https://www.petroskills.com/en/blog/entry/apr21-sub-introduction-to-production-sharing-contracts).

### 7.3 NOC — Saudi-style internal screening

```
fiscal_regime                       = noc_internal
oil_price_usd_bbl                   = 75            # internal flat deck
initial_rate_boe_month              = 45,000
decline_rate_annual_pct             = 12
months                              = 180
discount_rate_pct                   = 8             # state cost of capital
capex_total_usd                     = 55,000,000
fixed_opex_usd_month                = 90,000
variable_opex_usd_boe               = 3.20
water_handling_usd_bbl              = 0.60          # pipelined SWD
water_cut_pct                       = 12
gov_transfer_pct                    = 0             # NOC keeps gross
contractor_tax_rate_pct             = 0
```

Use this view for **internal capital allocation, well-prioritisation, and
abandonment timing**. Strategic value of long-life production, local content
and government employment is *not* in NPV — capture it qualitatively in the
Decision Matrix view (see `docs/application-help.pplx.md`).

---

## 8. CSV input QA checklist

Before clicking **Save & Run** in the Scenario tab's Upload data sub-panel:

- [ ] All `*_pct` columns entered as **percent** (e.g. `45` for 45%). The
  importer converts to fractions automatically.
- [ ] `fiscal_regime` is one of `us_royalty_tax`, `noc_internal`,
  `psc_cost_recovery`, `technical_service_contract`, `concession_tax_royalty`.
- [ ] PSC rows have `psc_royalty_rate_pct`,
  `psc_cost_recovery_ceiling_pct`, `psc_contractor_profit_oil_share_pct`,
  `contractor_tax_rate_pct` populated.
- [ ] TSC rows have `tsc_fee_usd_boe`, `tsc_cost_recovery_cap_usd_month`
  and `contractor_tax_rate_pct`.
- [ ] Concession rows have `concession_royalty_rate_pct` and
  `concession_income_tax_rate_pct`.
- [ ] `downtime_start_month + downtime_months ≤ months`.
- [ ] `capex_multiplier` and `opex_multiplier` set to `1.0` for the base
  case unless explicitly modelling overrun.
- [ ] `water_cut_pct` is plausible at horizon end (rarely > 95%).
- [ ] No commodity-tax double counting (US severance is folded into
  `us_royalty_tax` — don't also re-deduct it in the OPEX line).

---

## 9. Where to look next

- App overview and CSV workflow: [`docs/application-help.pplx.md`](application-help.pplx.md).
- Field-by-field methodology with Middle East context:
  [`docs/middle-east-capex-opex-fiscal-methodology.pplx.md`](middle-east-capex-opex-fiscal-methodology.pplx.md).
- Onshore well CAPEX/OPEX taxonomy:
  [`docs/oil-well-capex-opex-knowledge-base.pplx.md`](oil-well-capex-opex-knowledge-base.pplx.md).
- Multi-regime CSV template: `examples/asset_pulse_scenario_input_template.csv`.
