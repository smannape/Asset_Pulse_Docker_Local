# Middle East CAPEX/OPEX and Fiscal-Regime Methodology

## Executive summary

Middle East upstream asset economics should not be modeled as a single US-style lease cash-flow problem. The main modeling difference is the fiscal and contractual wrapper around the same technical cost base: a national oil company internal asset, a production sharing agreement or EPSA, a technical/risk service contract, or a concession/tax-royalty asset.

The technical cost stack remains familiar: drilling, completion, facilities, pipelines, gathering systems, workovers, chemicals, energy, water handling, manpower, maintenance, integrity, logistics, HSE, and abandonment. What changes is whether those costs are deducted, recovered from cost oil, reimbursed as petroleum costs, shared through an operating company, or carried by the national oil company as an internal project cost.

## Regional contract families

| Regime | Typical regional use | CAPEX/OPEX treatment | Revenue/cash-flow logic |
| --- | --- | --- | --- |
| NOC internal economics | Saudi, Kuwait, Qatar and other NOC-operated internal assets | NOC bears CAPEX/OPEX directly. Economics are often evaluated on gross project value, budget discipline, lifting cost, capacity maintenance, and government transfers. | Gross revenue minus operating cost, sustaining capital, development capital and abandonment. Optional internal royalty/tax or transfer logic can be added for government view. |
| PSC/EPSA cost recovery | Oman EPSA, Qatar PSC-type assets, some UAE emirates/other regional PSCs | Contractor bears costs, then recovers eligible exploration, development, operating, and abandonment costs from a capped share of production or revenue. Unrecovered costs carry forward. | Royalty if applicable, cost oil/gas, profit oil/gas split, contractor tax if applicable, government take. |
| Technical or risk service contract | Iraq TSC/DPSC, Kuwait OSC-style concepts, Iran buy-back style contracts | Contractor funds or performs work, recovers eligible petroleum costs, and earns a remuneration fee. It does not own produced hydrocarbons. | Contractor cash flow is cost recovery plus fee, often capped by a percentage of deemed production revenue. Host/NOC retains hydrocarbon revenue net of payments. |
| Concession/tax-royalty | Abu Dhabi-style concession, Saudi-style tax/royalty logic | Operator/partners bear costs and deduct eligible costs for taxable income. Royalty and income tax extract government take. | Gross revenue minus royalty, OPEX, CAPEX/DD&A or period CAPEX, then income tax; contractor keeps after-tax cash flow. |

## PSC/EPSA model

A practical PSC/EPSA calculation sequence is:

1. Gross revenue = oil revenue + gas revenue + NGL revenue.
2. Royalty = gross revenue x royalty rate, if applicable.
3. Net revenue after royalty = gross revenue - royalty.
4. Recoverable cost pool = current recoverable OPEX + recoverable CAPEX allowance + prior unrecovered cost + eligible abandonment contribution + optional uplift.
5. Available cost oil = net revenue after royalty x cost recovery ceiling.
6. Actual cost recovery = min(recoverable cost pool, available cost oil).
7. Unrecovered cost carry-forward = recoverable cost pool - actual cost recovery.
8. Profit oil = net revenue after royalty - actual cost recovery.
9. Contractor profit oil = profit oil x contractor share.
10. Government profit oil = profit oil x government share.
11. Contractor tax = contractor profit oil x contractor tax rate, unless tax is paid by NOC or exempt.
12. Contractor net cash flow = contractor profit oil - contractor tax.
13. Government take = royalty + government profit oil + contractor tax.

Cost recovery is the central mechanism. Under Oman EPSA-style contracts, contractors recover exploration and production costs from a portion of petroleum before profit sharing, and disputes can arise over which costs are recoverable, timing, production allocation, audit reversals, and overlifting ([Daily Jus](https://dailyjus.com/world/2024/07/disputes-under-omani-exploration-and-production-sharing-contracts)).

PSC cost recovery generally lets upstream contractors recover capital and operating costs from a specified share of production or revenue called cost recovery oil or gas, frequently subject to ceilings, carry-forward rules, approved work program and budget requirements, and recoverable/non-recoverable cost lists ([Journal of World Energy Law and Business](https://pmc.ncbi.nlm.nih.gov/articles/PMC7798991/)).

The Oxford Institute PSA model expresses the sequence as royalty, available cost oil, actual cost oil, profit oil, profit-oil split, contractor tax, and government take; it also highlights carry-forward and capital-cost uplift mechanics ([Oxford Institute for Energy Studies](https://www.oxfordenergy.org/wpcms/wp-content/uploads/2010/11/WPM25-ProductionSharingAgreementsAnEconomicAnalysis-KBindemann-1999.pdf)).

## Technical service contract model

A technical service contract or risk service contract is not an entitlement model. The contractor is usually paid for service delivery, cost recovery, and a fee. Produced hydrocarbons remain with the host state or NOC.

A practical TSC calculation sequence is:

1. Gross revenue = production x price.
2. Eligible petroleum costs = recoverable OPEX + recoverable CAPEX allowance + prior unrecovered cost.
3. Remuneration fee = produced BOE x fee per BOE, adjusted for production performance if required.
4. Payment cap = gross revenue x payment cap percentage.
5. Contractor payment before tax = min(eligible petroleum costs + remuneration fee, payment cap).
6. Cost recovery paid = min(eligible petroleum costs, contractor payment before tax).
7. Fee paid = contractor payment before tax - cost recovery paid.
8. Contractor tax = fee paid x service fee tax rate, if applicable.
9. Contractor net cash flow = contractor payment before tax - contractor tax.
10. Host/NOC cash flow = gross revenue - contractor payment before tax.
11. Unrecovered cost carry-forward = eligible petroleum costs - cost recovery paid.

Iraq-style technical service contracts reimburse petroleum costs and pay remuneration fees, often subject to period limits such as a share of deemed production value; Kuwait’s operating service contract concept has contractors contribute CAPEX/OPEX, recover only a percentage of costs, receive old/new oil and gas fees, and may include cost-savings sharing ([Kurdistan Regional Government fiscal regime paper](https://8th.cabinet.gov.krd/uploads/documents/Government_Take_and_Petroleum_Fiscal_Regimes__2008_06_30_h14m7s53.doc)).

## Concession/tax-royalty model

A concession/tax-royalty model is closer to a conventional tax model than a PSC. The contractor or concession partners hold an entitlement to lift production and pay fiscal charges through royalties, income tax, and possibly bonuses or participation mechanisms.

A practical concession calculation sequence is:

1. Gross revenue = oil + gas + NGL revenue.
2. Royalty = gross revenue x royalty rate, or a progressive royalty function.
3. Taxable cash margin = gross revenue - royalty - OPEX - sustaining CAPEX - allowable depreciation/capital allowance.
4. Income tax = max(taxable cash margin, 0) x income tax rate.
5. Contractor cash flow = gross revenue - royalty - OPEX - sustaining CAPEX - development CAPEX - abandonment - income tax.
6. Government take = royalty + income tax + bonuses/fees if modeled.

Abu Dhabi concessions are commonly structured around royalty and income tax rather than cost oil and profit oil; reported income tax ranges in oil concessions can be high and are set by concession agreement ([Kayrouz & Associates](https://www.kayrouzandassociates.com/insights/abu-dhabi-oil-concessions-upstream-framework)).

Saudi-style upstream economics include a progressive royalty linked to oil price and an upstream income tax. AGSI describes a current royalty formula of 15% on the first $70/bbl, 45% on the portion between $70/bbl and $100/bbl, and 80% above $100/bbl, with upstream income tax at 50% ([Arab Gulf States Institute](https://agsi.org/analysis/aramco-and-the-saudi-government-budget/)).

## NOC internal economics

NOC internal economics should focus on asset profitability, lifting cost, capacity support, marginal barrel economics, restart economics, and budget impact. It is not always meaningful to model contractor entitlement. Instead, the system should allow a gross project view:

1. Gross revenue = production x realized price.
2. Field operating cost = fixed OPEX + variable lifting/processing/water/energy/logistics costs.
3. Sustaining capital = recurring capital for integrity, workovers, sidetracks, debottlenecking, compression, artificial lift, facilities, and flow assurance.
4. Development capital = drilling, completion, tie-in, facility expansion, pipeline, gathering center and major project cost.
5. Free cash flow = gross revenue - OPEX - sustaining CAPEX - development CAPEX - abandonment.
6. Economic limit = minimum production rate required to cover avoidable OPEX and sustaining capital.

This view is best for internal NOC decisions: keep producing, choke back, defer workover, shut-in, restart, allocate rigs, or prioritize facility debottlenecking.

## Implementation recommendation for Asset Pulse

The regional logic should be merged into the Scenario calculation rather than implemented as a separate top-level tab. The user should select a Fiscal / Cost Regime within the scenario input panel, then the backend should apply the appropriate cash-flow transformation and return both project KPIs and fiscal breakdown.

A separate tab is only needed later if detailed contract administration is added, such as AFE approvals, cost recovery statements, cost audit exceptions, procurement compliance, unrecovered cost ledgers, overlift/underlift tracking, or multi-party entitlement accounting.

## Minimum parameters to expose

| Parameter | Applies to | Default starting value |
| --- | --- | --- |
| fiscal_regime | All | us_royalty_tax |
| cost_recovery_ceiling | PSC/EPSA | 0.60 |
| contractor_profit_share | PSC/EPSA | 0.35 |
| contractor_tax_rate | PSC/EPSA, TSC, concession | 0.0 to 0.50 depending use case |
| capex_recovery_years | PSC/EPSA, concession | 5 |
| capex_uplift_pct | PSC/EPSA | 0.0 |
| service_fee_per_boe | TSC/RSC | 1.15 |
| service_payment_cap_pct | TSC/RSC | 0.50 |
| eligible_cost_recovery_pct | TSC/RSC | 1.00 or contract-specific |
| concession_income_tax_rate | Concession | 0.55 or contract-specific |
| progressive_royalty_enabled | Saudi-style concession | false |

## Decision impact

The same well can rank differently depending on regime:

- Under NOC internal economics, a marginal well may stay online if it supports reservoir management, facility utilization, or strategic capacity.
- Under PSC/EPSA, a high-cost well may still be attractive to the contractor during cost recovery but less attractive after cost recovery when profit split dominates.
- Under TSC/RSC, the contractor may be cash-positive through cost recovery and fees while the host cares about net value after service payments.
- Under concession/tax-royalty, high royalty and tax rates can move economic limit upward and shorten profitable life.

Therefore, Asset Pulse should show both project economics and fiscal-regime-adjusted contractor/host cash flows.
