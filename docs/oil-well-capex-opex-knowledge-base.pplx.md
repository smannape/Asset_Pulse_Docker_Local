# Oil Well CAPEX and OPEX Knowledge Base

## Executive Summary

E&P companies generally treat asset economics as a life-cycle cash-flow problem: capital is spent to acquire, appraise, drill, complete, connect, process, transport, maintain, abandon, and restore assets, while operating cost is modeled as the recurring cost of keeping wells, pipelines, gathering systems, and facilities online. The core dashboard model should separate asset-level CAPEX, fixed OPEX, variable OPEX, production taxes/royalties, transportation and processing fees, sustaining capital, abandonment costs, and fiscal terms before calculating margin, NPV, PV-10-style value, economic limit, and shut-in/restart recommendations.

The most useful implementation pattern is a bottom-up cost taxonomy. Wells should be modeled by drilling, completion, facilities, artificial lift, lease equipment, workover/sustaining capital, and abandonment. Pipelines should be modeled by length, diameter, terrain/region factor, compression/pumping horsepower, storage, metering, maintenance, fuel/power, integrity management, and transportation tariffs. Gathering centers and production facilities should be modeled by inlet capacity, separation/treatment units, compression, processing, utilities, maintenance, labor, chemicals, and decommissioning.

For uncertainty analysis, the model should run sensitivities on oil price, gas price, NGL price, production rate, decline, water cut, fixed OPEX, variable OPEX, CAPEX overrun, startup delay, restart cost, downtime, discount rate, tax/royalty terms, and technical restart risk. A weighted decision matrix should combine economic indicators and operational risk: netback margin, economic limit, NPV delta, restart payback, water-disposal burden, artificial-lift criticality, HBP/lease constraints, midstream commitments, mechanical integrity, and strategic production value.

## Asset Cost Taxonomy

| Asset | CAPEX categories | OPEX categories | Modeling unit |
| --- | --- | --- | --- |
| Wells | Land/acquisition, drilling, completion, tangible equipment, facilities hook-up, artificial lift, workovers/sustaining capital, ARO | Fixed LOE, variable LOE, lifting energy, chemicals, water handling/disposal, well servicing, minor workovers, field labor, taxes | Per well, per BOE, per month |
| Pipelines | Route survey, right-of-way, pipe material, installation, tie-ins, metering, valves, pumps/compressors, SCADA, commissioning | Power/fuel, integrity inspection, corrosion control, pigging, repairs, ROW maintenance, tariffs, compression/pumping O&M | Inch-mile, mile, HP, throughput |
| Gathering systems | Flowlines, manifolds, lease equipment, compression, dehydration, pumps, metering, connection to processing | Compression fuel, chemicals, utilities, maintenance, pigging, trucking, gathering fees | Well count, miles, MMcfd, bbl/d |
| Gathering centers/facilities | Separators, FWKO, heater treaters, tanks, dehydrators, compressors, water treatment, gas processing, power, controls, buildings | Operators, power/fuel, maintenance, chemicals, water treatment, emissions compliance, turnarounds | Capacity, throughput, equipment count |

EIA’s upstream cost study separates onshore costs into land acquisition, capitalized drilling/completion/facilities costs, lease operating expenses, and gathering-processing-transport costs, which maps directly to the dashboard’s asset hierarchy ([EIA upstream cost study](https://www.eia.gov/analysis/studies/drilling/pdf/upstream.pdf)). EIA reports that onshore drilling commonly represents 30-40% of total well costs, completions 55-70%, and facilities about 7-8%, with typical studied onshore well capital costs ranging from $4.9 million to $8.3 million in 2014 cost terms ([EIA upstream cost study](https://www.eia.gov/analysis/studies/drilling/pdf/upstream.pdf)).

## CAPEX Calculation Framework

### General CAPEX Formula

```text
Total CAPEX =
  acquisition_capex
+ exploration_or_appraisal_capex
+ drilling_capex
+ completion_capex
+ surface_facilities_capex
+ gathering_pipeline_capex
+ processing_facility_capex
+ artificial_lift_capex
+ sustaining_capex
+ capitalized_aro
+ contingency
+ owner_costs
```

For a producing asset, the dashboard should distinguish initial development capital from sustaining or maintenance capital. Initial CAPEX affects investment decision metrics; sustaining capital affects ongoing cash flow and restart decisions. Under IFRS-style reporting, development expenditure is capitalized when it is necessary to access proved reserves or provide extraction, treatment, gathering, and storage facilities, while routine repairs after commercial production are expensed unless they meet asset-recognition criteria ([PwC oil and gas financial reporting guide](https://www.pwc.com/id/en/energy-utilities-mining/assets/financial-reporting-in-the-oil-and-gas-industry.pdf)).

### Well CAPEX

```text
well_capex =
  drilling_capex
+ completion_capex
+ tangible_equipment_capex
+ pad_site_and_road_capex
+ lease_equipment_capex
+ artificial_lift_capex
+ flowline_hookup_capex
+ scada_metering_capex
+ contingency
+ capitalized_aro
```

EIA’s onshore well model identifies drilling costs such as rig hire, bits, logging, cement, mud, drilling fluids, fuel, casing, and liners, while completion costs include tubing, Christmas trees, packers, perforating, frack equipment, proppant, chemicals, water, flowback, and disposal ([EIA upstream cost study](https://www.eia.gov/analysis/studies/drilling/pdf/upstream.pdf)). In offshore deepwater, EIA notes that rig-related drilling and completion costs can account for 90-95% of total well costs and that offshore well costs can range broadly from $60 million to $240 million depending on basin, depth, rig days, and complexity ([EIA upstream cost study](https://www.eia.gov/analysis/studies/drilling/pdf/upstream.pdf)).

### Pipeline and Gathering CAPEX

```text
pipeline_capex =
  length_miles
* diameter_inches
* base_cost_per_inch_mile
* regional_factor
+ compressor_hp * cost_per_hp * compression_region_factor
+ metering_and_scada
+ tie_in_costs
+ contingency
```

INGAA’s midstream infrastructure assumptions use a pipeline cost method based on $/inch-mile, with an average pipeline cost of $155,000 per inch-mile and gathering line costs that vary by diameter, such as $28,827/inch-mile for 6-inch gathering line and $145,701/inch-mile for 16-inch gathering line in 2015 dollars ([INGAA midstream infrastructure study](https://ingaa.org/wp-content/uploads/2016/04/27962.pdf)). INGAA also models compression and pumping at $3,000 per horsepower before regional factors, making horsepower a clean input for pipeline and gathering-center CAPEX ([INGAA midstream infrastructure study](https://ingaa.org/wp-content/uploads/2016/04/27962.pdf)).

### Facility CAPEX

```text
facility_capex =
  processing_capacity_mmcfd * gas_processing_cost_per_mmcfd
+ oil_handling_capacity_bopd * oil_facility_unit_cost
+ water_handling_capacity_bwpd * water_facility_unit_cost
+ compression_hp * cost_per_hp
+ storage_capacity_bbl * storage_cost_per_bbl
+ power_generation_or_grid_connection
+ controls_scada
+ installation_commissioning
+ contingency
```

INGAA estimates gas processing at about $525,000 per MMcfd excluding compression, NGL fractionation at $6,600 per BOE of NGL processed, crude oil storage tanks at $15 per barrel, and lease equipment at $103,000 per gas well and $250,000 per oil well in 2015 dollars ([INGAA midstream infrastructure study](https://ingaa.org/wp-content/uploads/2016/04/27962.pdf)). These public unit-cost assumptions are suitable for default seed values, but the dashboard should allow operators to override them with company AFE, procurement, and historical actual-cost data.

### ARO and Decommissioning CAPEX

```text
aro_present_value =
  future_abandonment_cost
/ (1 + credit_adjusted_risk_free_rate) ^ years_to_abandonment

aro_accretion_expense_t =
  opening_aro_liability_t
* credit_adjusted_risk_free_rate
```

COPAS defines asset retirement obligation as the unavoidable cost of retiring long-lived oilfield assets, including dismantlement and removal of production equipment and facilities and restoration or reclamation of the surface and subsurface ([COPAS ARO accounting](https://copas.org/asset-retirement-obligation-accounting-in-the-oil-and-gas-industry/)). COPAS notes that successful-efforts companies include retirement cost as part of the cost of wells, equipment, and facilities and amortize it over proved developed reserves, while full-cost companies include retirement cost in the countrywide cost center and amortize it over total proved reserves ([COPAS ARO accounting](https://copas.org/asset-retirement-obligation-accounting-in-the-oil-and-gas-industry/)).

## OPEX Calculation Framework

### General OPEX Formula

```text
total_opex_t =
  fixed_opex_t
+ variable_oil_opex_per_bbl * oil_bbl_t
+ variable_gas_opex_per_mcf * gas_mcf_t
+ variable_water_opex_per_bbl * water_bbl_t
+ chemicals_opex_t
+ energy_opex_t
+ maintenance_opex_t
+ workover_opex_t
+ gathering_processing_transport_t
+ production_taxes_t
+ environmental_compliance_t
+ allocated_g_and_a_t
```

EIA defines lifting costs, also called production costs, as the cost to operate and maintain wells and related equipment and facilities per BOE after hydrocarbons have been found, acquired, and developed for production ([EIA performance profiles](https://www.eia.gov/finance/performanceprofiles/oil_gas.php)). EIA defines direct lifting costs as total production spending minus production taxes and, in foreign regions, royalties, divided by production in BOE, while total lifting costs are direct lifting costs plus production taxes ([EIA performance profiles](https://www.eia.gov/finance/performanceprofiles/oil_gas.php)).

### Fixed and Variable OPEX

```text
opex_t =
  fixed_cost_per_month
+ oil_variable_cost_per_bbl * oil_bbl_t
+ gas_variable_cost_per_mcf * gas_mcf_t
+ water_variable_cost_per_bbl * water_bbl_t
```

Cawley, Gillespie & Associates recommends separating operating costs into fixed costs that are independent of production volumes and variable costs associated with production volumes, with fixed examples such as field salaries, compressor rentals, and facility maintenance, and variable examples such as chemicals, pump/compressor electricity, and trucking ([CGA operating expense guidance](https://www.cgaus.com/oil-gas-operating-expenses-preparing-compliant-forecasts/)). CGA recommends using at least the prior 12 months of recent cost data to determine current costs, because a single month can be distorted by seasonal variations or accounting anomalies such as annual ad valorem taxes ([CGA operating expense guidance](https://www.cgaus.com/oil-gas-operating-expenses-preparing-compliant-forecasts/)).

### Netback and Margin

```text
gross_revenue_t =
  oil_bbl_t * realized_oil_price
+ gas_mcf_t * realized_gas_price
+ ngl_bbl_t * realized_ngl_price

net_revenue_t =
  gross_revenue_t
- royalties_t
- production_taxes_t
- transportation_tariffs_t
- processing_fees_t

operating_cash_flow_t =
  net_revenue_t
- controllable_opex_t
- allocated_fixed_opex_t
- sustaining_capex_t

netback_per_boe_t =
  operating_cash_flow_before_sustaining_capex_t
/ boe_t
```

Onshore operating cost models should include lease operating expenses plus gathering, processing, and transport fees. EIA reports studied onshore LOE of $2.00/BOE to $14.50/BOE, water disposal of $1.00/bbl to $8.00/bbl of water, oil/condensate gathering of $0.25/bbl to $1.50/bbl by pipeline or $2.00/bbl to $3.50/bbl by trucking, and G&A of $1.00/BOE to $4.00/BOE ([EIA upstream cost study](https://www.eia.gov/analysis/studies/drilling/pdf/upstream.pdf)).

## Accounting and Reserve-Economics Treatment

### Successful Efforts vs Full Cost

Exploration and evaluation costs may be capitalized or expensed depending on accounting policy and whether the activity has demonstrated commercial viability, while development costs are capitalized when they create access to proved reserves or facilities for extraction, treatment, gathering, and storage ([PwC oil and gas financial reporting guide](https://www.pwc.com/id/en/energy-utilities-mining/assets/financial-reporting-in-the-oil-and-gas-industry.pdf)). Under U.S. full-cost rules, Deloitte summarizes SEC guidance that costs to be amortized include all capitalized costs less accumulated amortization, estimated future expenditures to develop proved reserves, and estimated dismantlement and abandonment costs net of salvage values ([Deloitte DART Topic 12](https://dart.deloitte.com/USDART/home/accounting/sec/sec-staff-bulletins/staff-accounting-bulletins/topic-12-oil-gas-producing-activities)).

### DD&A

```text
uop_dd_and_a_t =
  depletable_cost_base
* production_boe_t
/ remaining_proved_reserves_boe

depletable_cost_base =
  net_capitalized_costs
+ future_development_costs
+ future_abandonment_costs_net_salvage
- excluded_unproved_or_major_project_costs
```

Deloitte’s summary of SEC full-cost guidance states that DD&A is generally computed on a physical units basis using oil and gas converted to a common unit by relative energy content, unless economic circumstances make a gross-revenue method more appropriate ([Deloitte DART Topic 12](https://dart.deloitte.com/USDART/home/accounting/sec/sec-staff-bulletins/staff-accounting-bulletins/topic-12-oil-gas-producing-activities)). PwC describes production assets as being amortized through DD&A on a units-of-production basis over proved or proved-plus-probable reserves, depending on policy and consistency ([PwC oil and gas financial reporting guide](https://www.pwc.com/id/en/energy-utilities-mining/assets/financial-reporting-in-the-oil-and-gas-industry.pdf)).

### PV-10 and Standardized Measure Logic

```text
pv10_pre_tax =
  sum_t[
    (future_revenue_t
     - future_production_cost_t
     - future_development_cost_t
     - future_abandonment_cost_t)
    / (1 + 10%) ^ t
  ]

standardized_measure =
  sum_t[
    (future_revenue_t
     - future_production_cost_t
     - future_development_cost_t
     - future_abandonment_cost_t
     - future_income_tax_t)
    / (1 + 10%) ^ t
  ]
```

Stout explains that PV-10 is the present value of estimated future oil and gas revenues reduced by direct expenses and discounted at 10%, while the standardized measure also deducts future income taxes before applying the 10% discount rate ([Stout SEC reserve reporting](https://www.stout.com/en/insights/article/understanding-sec-oil-and-gas-reserve-reporting)). Stout notes that the SEC standardized framework uses the 12-month historical average of first-day-of-month prices, deducts estimated production costs, development costs, abandonment costs, and income taxes, and should not be interpreted as fair market value ([Stout SEC reserve reporting](https://www.stout.com/en/insights/article/understanding-sec-oil-and-gas-reserve-reporting)).

## Profitability and Economic Limit

### Economic Limit Rate

```text
net_price_per_boe =
  realized_price_per_boe
- royalty_per_boe
- production_tax_per_boe
- variable_cost_per_boe
- transport_processing_per_boe

economic_limit_rate_boe_per_month =
  fixed_cost_per_month
/ net_price_per_boe
```

If production falls below the economic limit rate, the asset cannot cover fixed operating cost under the modeled price and cost assumptions. For multi-phase wells, compute the limit on an equivalent BOE basis or solve with oil, gas, and water streams separately because water handling can dominate marginal economics in high-water-cut wells.

### Project NPV

```text
free_cash_flow_t =
  revenue_t
- royalties_t
- production_taxes_t
- opex_t
- sustaining_capex_t
- development_capex_t
- abandonment_cash_cost_t
- income_tax_t

npv =
  sum_t[free_cash_flow_t / (1 + discount_rate)^t]
```

The dashboard should calculate NPV at asset, well, scenario, and portfolio levels. It should also display breakeven oil price, breakeven OPEX, breakeven CAPEX overrun, and breakeven restart cost using root-finding against NPV = 0 or operating cash flow = 0.

## Uncertainty and Sensitivity Modeling

### Deterministic Sensitivities

| Variable | Typical sensitivity range | Impact metric |
| --- | --- | --- |
| Oil/gas/NGL price | -30% to +30% | NPV, margin, economic limit |
| Production rate | -30% to +30% | Cash flow, reserves, payback |
| Decline rate | -20% to +20% | Reserves, future cash flow |
| CAPEX overrun | 0% to +30% | NPV, IRR, capital efficiency |
| OPEX escalation | 0% to +30% | Economic limit, shut-in threshold |
| Water cut | 0% to +30% absolute/relative | Disposal cost, lifting margin |
| Downtime/startup delay | 1-24 months | NPV erosion, payback delay |
| Restart cost | P10/P50/P90 | Restart recommendation |

Upstream project economics commonly test price, production, OPEX, and CAPEX because changes in these inputs directly affect NPV and profitability index; one public upstream economics example varied oil price, oil production, OPEX, and CAPEX by +/-5% and +/-10% to evaluate NPV and profitability index sensitivity ([Himalayan Journal of Economics and Business Management](https://www.himjournals.com/hjebm/936/1022/articleID=1380/)). The model should also test breakeven price, breakeven CAPEX overrun, and breakeven recoverable reserves because those are intuitive thresholds for decision makers.

### Probabilistic Scenarios

```text
scenario_npv_distribution =
  monte_carlo(
    oil_price ~ triangular(low, base, high),
    production_rate ~ lognormal(mu, sigma),
    capex_multiplier ~ triangular(p10, p50, p90),
    opex_multiplier ~ triangular(p10, p50, p90),
    water_cut ~ beta(alpha, beta),
    restart_success_factor ~ discrete(probabilities)
  )
```

For each scenario, store assumptions, computed cash flows, NPV, economic limit, and recommended action. The Neon database should store scenario inputs compactly as JSONB where possible while keeping key numeric outputs in typed columns for filtering and dashboard aggregation.

## Shut-In and Restart Decision Logic

### Candidate Selection

```text
monthly_operating_margin =
  net_revenue_month
- fixed_opex_month
- variable_opex_month
- transport_processing_month
- required_sustaining_capex_month

restart_payback_months =
  restart_cost
/ max(monthly_operating_margin_after_restart, small_positive_value)

shut_in_savings =
  avoidable_fixed_opex
+ avoidable_variable_opex
+ avoided_water_disposal
- shut_in_cost
- lease_or_midstream_penalties
- restart_cost_probability_weighted
- expected_production_loss_value
```

SPE’s JPT warns that selecting wells simply from the lease operating statement is insufficient, although high-water-cut wells can be attractive shut-in candidates because shut-in avoids water-disposal cost ([SPE JPT](https://jpt.spe.org/twa/shutting-wells-why-its-nuanced-process)). SPE’s JPT also notes that held-by-production constraints, subsurface challenges, crossflow, paraffin/asphaltene/emulsion buildup, and marginal wells failing to return to production can make shut-ins operationally risky ([SPE JPT](https://jpt.spe.org/twa/shutting-wells-why-its-nuanced-process)).

### Restart Risk

AOGR lists fiscal restart drivers such as hedging, offset activity, HBP obligations, lease obligations, midstream obligations, capital-provider restrictions, royalty provisions, and stripper-well tax classification, alongside technical drivers such as production restoration uncertainty, parent-child effects, ESP restart risk, crossflow, liquid loading, artificial-lift failures, corrosion, scale, sanding, surface-facility degradation, and tubular/seal failures ([AOGR restart strategy article](https://www.aogr.com/magazine/cover-story/fiscal-technical-issues-define-operator-strategies-in-restarting-shut-in-wells)). AOGR also notes that many operators database remedial and plugging costs to obtain quick NPV or cash-flow estimates for legacy gas wells, where remedial work is often negative NPV ([AOGR restart strategy article](https://www.aogr.com/magazine/cover-story/fiscal-technical-issues-define-operator-strategies-in-restarting-shut-in-wells)).

## Weighted Decision Matrix

### Recommended Criteria

| Criterion | Direction | Suggested weight | Data source |
| --- | --- | ---: | --- |
| Current monthly margin | Higher is better | 20% | Production, price, LOE |
| NPV if kept online | Higher is better | 15% | Forecast model |
| Avoidable OPEX if shut in | Higher favors shut-in | 10% | LOE, water, energy |
| Restart payback | Lower is better | 10% | Restart cost, forecast margin |
| Restart technical risk | Lower is better | 15% | Artificial lift, well age, well type |
| HBP/lease/midstream constraint | Lower risk is better | 10% | Commercial/legal inputs |
| Water-disposal burden | Higher favors shut-in | 10% | Water cut, disposal cost |
| Strategic production value | Higher favors keep online | 10% | Portfolio priority |

### Scoring Formula

```text
normalized_score_i =
  normalize(metric_i, direction_i, min_i, max_i)

weighted_score =
  sum_i(weight_i * normalized_score_i)

recommended_action =
  if monthly_margin < 0 and restart_risk low and hbp_risk low:
      "Shut in / monitor restart trigger"
  elif monthly_margin < 0 and restart_risk high:
      "Choke back / minimize cost / avoid full shut-in"
  elif monthly_margin > 0 and npv_positive:
      "Keep online"
  elif restart_payback acceptable and price_trigger_met:
      "Restart"
  else:
      "Review manually"
```

The matrix should never be a black-box decision. It should show which criteria drove the recommendation, because well shut-in/restart decisions can be dominated by constraints that do not appear in pure NPV models, such as HBP, midstream commitments, ESP restart risk, parent-child risk, or water-disposal bottlenecks.

## Database Design Seed

| Table | Purpose |
| --- | --- |
| assets | Wells, pipelines, gathering centers, facilities |
| asset_cost_profiles | Default CAPEX/OPEX assumptions by asset |
| production_forecasts | Monthly oil, gas, water, NGL forecast |
| price_decks | Oil, gas, NGL prices and differentials |
| scenarios | Scenario metadata and uncertainty inputs |
| scenario_results | KPIs, NPV, economic limit, recommendation |
| cash_flows | Time-series cash-flow lines by asset and scenario |
| decision_matrix | Criteria weights and scores |
| events | Shut-in, restart, workover, failure, CAPEX overrun events |

For Neon’s free tier, the prototype should store only scenario metadata, summary KPIs, and compact monthly cash-flow arrays for selected scenarios. Neon’s current free plan provides 0.5 GB storage per project, 5 GB/month public transfer, and scale-to-zero after 5 minutes, so detailed Monte Carlo paths should be aggregated before storage unless the user upgrades ([Neon plans](https://neon.tech/docs/introduction/plans)).

## Netlify and Backend Deployment Implications

Netlify is a strong fit for the React frontend and JavaScript/Go serverless functions, but Netlify Functions do not natively support Python runtime functions; Netlify’s Python support is for configurable Python versions during builds, not a Python API runtime ([Netlify Python build support](https://www.netlify.com/blog/announcing-configurable-python-versions-in-netlify-builds/), [Netlify functions configuration](https://docs.netlify.com/build/functions/optional-configuration/)). Therefore, the recommended production architecture is React on Netlify, Python/FastAPI calculations on a separate API host, and Neon PostgreSQL as the shared database.

For Neon connectivity, serverless or bursty APIs should use the pooled Neon connection string, while migrations should use a direct connection because pooled connections can cause migration issues ([Neon Knex connection guide](https://neon.tech/docs/guides/knex)). Python applications can connect to Neon using a `DATABASE_URL` environment variable with `sslmode=require`, which fits the FastAPI service configuration ([Neon Python guide](https://neon.tech/docs/guides/python)).

## Dashboard Calculation Modules

| Module | Function |
| --- | --- |
| `cost_models.py` | Well, pipeline, facility CAPEX and OPEX formulas |
| `economics.py` | Revenue, royalties, taxes, free cash flow, NPV, PV-10, payback |
| `uncertainty.py` | Tornado sensitivities, Monte Carlo, P10/P50/P90 |
| `decision_matrix.py` | Weighted scoring and shut-in/restart recommendations |
| `database.py` | PostgreSQL connection and persistence |
| `schemas.py` | Pydantic request/response models |

## Implementation Defaults

| Parameter | Default seed value | Override required? |
| --- | ---: | --- |
| Discount rate | 10% | Yes |
| Royalty burden | 12.5-20% | Yes |
| Production tax | 0-10% | Yes |
| Onshore LOE | $2-14.50/BOE | Yes |
| Water disposal | $1-8/bbl water | Yes |
| Pipeline CAPEX | $/inch-mile | Yes |
| Compression CAPEX | $3,000/HP | Yes |
| Gas processing | $525,000/MMcfd | Yes |
| ARO discounting | PV of abandonment cost | Yes |

## Knowledge Graph Entities

```text
Asset -> has_capex_category -> Drilling
Asset -> has_capex_category -> Completion
Asset -> has_capex_category -> Facilities
Asset -> has_opex_category -> Fixed LOE
Asset -> has_opex_category -> Variable LOE
Well -> may_have -> Artificial Lift
Well -> may_have -> ARO
Pipeline -> calculated_by -> Inch-Mile CAPEX
Facility -> calculated_by -> Capacity-Based CAPEX
Scenario -> changes -> CAPEX Multiplier
Scenario -> changes -> OPEX Multiplier
Scenario -> outputs -> NPV
Scenario -> outputs -> Economic Limit
Scenario -> outputs -> Decision Matrix Score
Decision -> considers -> HBP Constraint
Decision -> considers -> Restart Risk
Decision -> recommends -> Keep Online / Shut In / Restart / Review
```

## Key Takeaways

The dashboard should use public formulas and default benchmarks only as seed assumptions. The highest-value workflow is to let engineers input company-specific AFE, LOE, production, water, power, workover, and midstream data, then compare base-case economics against uncertainty events. The decision engine should combine pure economics with technical and commercial constraints, because a well with negative current margin may still be kept online due to lease, midstream, restart-risk, or strategic reasons.
