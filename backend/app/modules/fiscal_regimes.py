"""
Regional fiscal-regime calculations applied on top of the base scenario engine.

Regimes implemented:

* ``us_royalty_tax``         — existing default. Royalty + production tax already
                                 net out of the base scenario; this regime is a no-op
                                 layer that simply reports the contractor (=operator)
                                 cash flow as the base FCF.
* ``noc_internal``            — gross project economics with optional government
                                 transfer/tax (defaults to zero). Used by national oil
                                 companies for internal screening.
* ``psc_cost_recovery``       — Production Sharing Contract / EPSA. Gross production →
                                 royalty → available cost oil ceiling → actual cost
                                 recovery (recoverable costs + carry-forward) → profit
                                 oil split (government / contractor) → contractor tax.
                                 Optional uplift on CAPEX. References:
                                   - Bindemann, Oxford Energy WPM 25 (1999)
                                     https://www.oxfordenergy.org/wpcms/wp-content/uploads/2010/11/WPM25-ProductionSharingAgreementsAnEconomicAnalysis-KBindemann-1999.pdf
                                   - Daily Jus on Omani EPSA disputes (2024)
                                     https://dailyjus.com/world/2024/07/disputes-under-omani-exploration-and-production-sharing-contracts
                                   - PMC fiscal regimes review (PMC7798991)
                                     https://pmc.ncbi.nlm.nih.gov/articles/PMC7798991/
* ``technical_service_contract`` — TSC / RSC (Iraq-style). Contractor recovers
                                 eligible petroleum costs subject to a periodic
                                 payment cap (share of deemed production revenue) and
                                 receives a remuneration fee per BOE. No hydrocarbon
                                 ownership.
* ``concession_tax_royalty``  — Middle East concession with royalty (flat or Saudi-style
                                 progressive tiers) and upstream income tax. Saudi
                                 default tiers: 15% on first $70/bbl, 45% from
                                 $70-$100, 80% above $100; income tax 50%. Reference:
                                   - AGSI Aramco fiscal terms
                                     https://agsi.org/analysis/aramco-and-the-saudi-government-budget/

Each regime returns a per-month breakdown plus an aggregated ``summary`` dict that
the scenario engine surfaces under ``result["fiscal"]``. The contractor net cash
flow stream (``contractor_cf``) replaces the base ``free_cash_flow`` so downstream
NPV / PV-10 / payback all reflect the regime.
"""

from __future__ import annotations

from typing import Any, Iterable


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

SUPPORTED_REGIMES = (
    "us_royalty_tax",
    "noc_internal",
    "psc_cost_recovery",
    "technical_service_contract",
    "concession_tax_royalty",
)


def apply_fiscal_regime(
    *,
    regime: str,
    monthly: dict[str, list[float]],
    inputs: dict[str, Any],
) -> dict[str, Any]:
    """Apply a fiscal regime on top of pre-computed base monthly arrays.

    ``monthly`` must already contain ``net_revenue``, ``opex``, ``sustaining_capex``,
    ``dev_capex``, ``abandonment``, ``free_cash_flow`` and the production arrays
    (``oil_bbl``, ``gas_mcf``).

    Returns a dict with at least ``contractor_cf`` (length == months) and a
    ``summary`` block. ``contractor_cf`` should replace ``monthly.free_cash_flow``
    in the scenario response so all downstream KPIs use the regime view.
    """
    regime_norm = (regime or "us_royalty_tax").lower()
    if regime_norm not in SUPPORTED_REGIMES:
        raise ValueError(f"Unsupported fiscal regime: {regime!r}")

    if regime_norm == "us_royalty_tax":
        return _us_passthrough(monthly)
    if regime_norm == "noc_internal":
        return _noc_internal(monthly, inputs)
    if regime_norm == "psc_cost_recovery":
        return _psc(monthly, inputs)
    if regime_norm == "technical_service_contract":
        return _tsc(monthly, inputs)
    if regime_norm == "concession_tax_royalty":
        return _concession(monthly, inputs)
    raise AssertionError("unreachable")  # pragma: no cover


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _gross_revenue_series(
    monthly: dict[str, list[float]], inputs: dict[str, Any]
) -> list[float]:
    """Reconstruct gross (pre-royalty/tax) revenue per month.

    The base ``net_revenue`` already deducts royalty, production tax, transport
    and processing. For most fiscal regimes we want the *gross* number to apply
    statutory royalty / cost recovery against. We rebuild it from prices and
    volumes which we know exactly.
    """
    oil_price = float(inputs.get("oil_price", 0.0))
    gas_price = float(inputs.get("gas_price", 0.0))
    ngl_price = float(inputs.get("ngl_price", 0.0))
    initial_ngl_bpd = float(inputs.get("initial_ngl_bpd", 0.0))
    initial_oil_bopd = float(inputs.get("initial_oil_bopd", 0.0)) or 1e-9

    oil_arr = monthly.get("oil_bbl", [])
    gas_arr = monthly.get("gas_mcf", [])

    out: list[float] = []
    for oil, gas in zip(oil_arr, gas_arr):
        # NGL volume scales with the same decline ratio as oil
        ngl_ratio = (oil / (initial_oil_bopd * 30.4375)) if initial_oil_bopd > 0 else 0.0
        ngl_bbl = initial_ngl_bpd * 30.4375 * ngl_ratio
        gross = oil * oil_price + gas * gas_price + ngl_bbl * ngl_price
        out.append(gross)
    return out


def _capex_series(monthly: dict[str, list[float]]) -> list[float]:
    """Total capital outflow per month (development + sustaining + abandonment)."""
    dev = monthly.get("dev_capex", [])
    sus = monthly.get("sustaining_capex", [])
    aban = monthly.get("abandonment", [])
    n = max(len(dev), len(sus), len(aban))
    out = []
    for i in range(n):
        d = dev[i] if i < len(dev) else 0.0
        s = sus[i] if i < len(sus) else 0.0
        a = aban[i] if i < len(aban) else 0.0
        out.append(d + s + a)
    return out


def _zeros(n: int) -> list[float]:
    return [0.0] * n


def _round_list(xs: Iterable[float], nd: int = 2) -> list[float]:
    return [round(float(x), nd) for x in xs]


# ---------------------------------------------------------------------------
# Regimes
# ---------------------------------------------------------------------------

def _us_passthrough(monthly: dict[str, list[float]]) -> dict[str, Any]:
    """No-op regime — surfaces the existing US royalty/tax cash flow unchanged."""
    fcf = list(monthly.get("free_cash_flow", []))
    return {
        "regime": "us_royalty_tax",
        "contractor_cf": fcf,
        "monthly": {
            "contractor_cf": _round_list(fcf),
        },
        "summary": {
            "regime": "us_royalty_tax",
            "contractor_total_cf": round(sum(fcf), 2),
            "government_total": 0.0,  # already netted via royalty + production tax in base
            "note": "Base US royalty/tax netback applied at the revenue stage.",
        },
    }


def _noc_internal(
    monthly: dict[str, list[float]], inputs: dict[str, Any]
) -> dict[str, Any]:
    """Gross project economics with optional government transfer.

    Recomputes pre-royalty revenue and ignores production tax; an optional flat
    transfer (``noc_government_share_pct``) and corporate tax
    (``noc_corp_tax_pct``) can be applied. Defaults are zero so this gives a
    pure technical-economics view.
    """
    n = len(monthly.get("free_cash_flow", []))
    gross = _gross_revenue_series(monthly, inputs)
    opex = monthly.get("opex", _zeros(n))
    capex = _capex_series(monthly)

    gov_share = float(inputs.get("noc_government_share_pct", 0.0))
    corp_tax = float(inputs.get("noc_corp_tax_pct", 0.0))

    contractor_cf: list[float] = []
    gov_take: list[float] = []
    for i in range(n):
        operating = gross[i] - opex[i]
        transfer = max(0.0, operating) * gov_share
        taxable = operating - transfer
        tax = max(0.0, taxable) * corp_tax
        contractor = operating - transfer - tax - capex[i]
        contractor_cf.append(contractor)
        gov_take.append(transfer + tax)

    return {
        "regime": "noc_internal",
        "contractor_cf": contractor_cf,
        "monthly": {
            "gross_revenue": _round_list(gross),
            "government_take": _round_list(gov_take),
            "contractor_cf": _round_list(contractor_cf),
        },
        "summary": {
            "regime": "noc_internal",
            "gross_revenue_total": round(sum(gross), 2),
            "government_total": round(sum(gov_take), 2),
            "contractor_total_cf": round(sum(contractor_cf), 2),
            "government_share_pct": gov_share,
            "corp_tax_pct": corp_tax,
            "note": "Gross project economics. Government share/tax default to 0 for internal screening.",
        },
    }


def _psc(
    monthly: dict[str, list[float]], inputs: dict[str, Any]
) -> dict[str, Any]:
    """Production Sharing Contract / EPSA with cost-oil ceiling and carry-forward.

    Per Bindemann (Oxford Energy WPM 25) and the PMC review:
        gross_t                                                = revenue at month t
        royalty_t          = gross_t * royalty_pct
        net_after_royalty  = gross_t - royalty_t
        available_cost_oil = net_after_royalty * cost_oil_limit_pct
        recoverable_t      = opex_t + capex_t * (1 + uplift_pct) + carry_forward_{t-1}
        actual_cost_oil    = min(recoverable_t, available_cost_oil)
        carry_forward_t    = recoverable_t - actual_cost_oil
        profit_oil_t       = net_after_royalty - actual_cost_oil
        contractor_profit  = profit_oil_t * contractor_profit_share_pct
        contractor_tax     = max(0, contractor_profit) * contractor_tax_pct
        contractor_cf      = actual_cost_oil + contractor_profit - contractor_tax
                             - capex_t   (contractor still funds capex out-of-pocket;
                                          recovery is via cost oil over time)
    Abandonment cost (when present) is treated as recoverable opex in that month.
    """
    n = len(monthly.get("free_cash_flow", []))
    gross = _gross_revenue_series(monthly, inputs)
    opex = monthly.get("opex", _zeros(n))
    capex = _capex_series(monthly)

    royalty_pct = float(inputs.get("psc_royalty_pct", 0.10))
    cost_oil_limit = float(inputs.get("psc_cost_oil_limit_pct", 0.60))
    contractor_profit_share = float(inputs.get("psc_contractor_profit_share_pct", 0.40))
    contractor_tax_pct = float(inputs.get("psc_contractor_tax_pct", 0.30))
    uplift_pct = float(inputs.get("psc_capex_uplift_pct", 0.0))

    royalty_arr: list[float] = []
    cost_oil_arr: list[float] = []
    profit_oil_arr: list[float] = []
    gov_profit_arr: list[float] = []
    contractor_profit_arr: list[float] = []
    tax_arr: list[float] = []
    contractor_cf: list[float] = []
    carry_arr: list[float] = []

    carry = 0.0
    for i in range(n):
        roy = gross[i] * royalty_pct
        net_after_roy = gross[i] - roy
        avail_cost_oil = max(0.0, net_after_roy) * cost_oil_limit
        recoverable = opex[i] + capex[i] * (1.0 + uplift_pct) + carry
        actual_cost_oil = min(recoverable, avail_cost_oil)
        carry = max(0.0, recoverable - actual_cost_oil)
        profit_oil = net_after_roy - actual_cost_oil
        contractor_profit = profit_oil * contractor_profit_share
        gov_profit = profit_oil - contractor_profit
        tax = max(0.0, contractor_profit) * contractor_tax_pct
        # Contractor receives cost oil (cash) + profit oil share - tax, but
        # still funds capex out-of-pocket (recovered over time via cost oil).
        contractor = actual_cost_oil + contractor_profit - tax - capex[i]

        royalty_arr.append(roy)
        cost_oil_arr.append(actual_cost_oil)
        profit_oil_arr.append(profit_oil)
        gov_profit_arr.append(gov_profit)
        contractor_profit_arr.append(contractor_profit)
        tax_arr.append(tax)
        contractor_cf.append(contractor)
        carry_arr.append(carry)

    gov_total = sum(royalty_arr) + sum(gov_profit_arr) + sum(tax_arr)

    return {
        "regime": "psc_cost_recovery",
        "contractor_cf": contractor_cf,
        "monthly": {
            "gross_revenue": _round_list(gross),
            "royalty": _round_list(royalty_arr),
            "cost_oil": _round_list(cost_oil_arr),
            "profit_oil": _round_list(profit_oil_arr),
            "government_profit_oil": _round_list(gov_profit_arr),
            "contractor_profit_oil": _round_list(contractor_profit_arr),
            "contractor_tax": _round_list(tax_arr),
            "carry_forward": _round_list(carry_arr),
            "contractor_cf": _round_list(contractor_cf),
        },
        "summary": {
            "regime": "psc_cost_recovery",
            "royalty_pct": royalty_pct,
            "cost_oil_limit_pct": cost_oil_limit,
            "contractor_profit_share_pct": contractor_profit_share,
            "contractor_tax_pct": contractor_tax_pct,
            "capex_uplift_pct": uplift_pct,
            "royalty_total": round(sum(royalty_arr), 2),
            "cost_oil_total": round(sum(cost_oil_arr), 2),
            "profit_oil_total": round(sum(profit_oil_arr), 2),
            "government_profit_oil_total": round(sum(gov_profit_arr), 2),
            "contractor_profit_oil_total": round(sum(contractor_profit_arr), 2),
            "contractor_tax_total": round(sum(tax_arr), 2),
            "carry_forward_end": round(carry_arr[-1] if carry_arr else 0.0, 2),
            "government_total": round(gov_total, 2),
            "contractor_total_cf": round(sum(contractor_cf), 2),
        },
    }


def _tsc(
    monthly: dict[str, list[float]], inputs: dict[str, Any]
) -> dict[str, Any]:
    """Technical Service Contract / Risk Service Contract (Iraq-style).

    Contractor reimbursed for eligible petroleum costs (opex + capex) subject to
    a periodic cap expressed as a share of deemed gross revenue, plus a flat
    remuneration fee per produced BOE. No hydrocarbon ownership.

        eligible_t   = opex_t + capex_t + carry_{t-1}
        cap_t        = gross_t * tsc_payment_cap_pct
        reimburse_t  = min(eligible_t, cap_t)
        carry_t      = eligible_t - reimburse_t           (carried to next period)
        fee_t        = boe_t * tsc_remuneration_per_boe
        contractor_t = reimburse_t + fee_t * (1 - tsc_contractor_tax_pct) - capex_t
        government_t = gross_t - reimburse_t - fee_t      (taxes captured implicitly)
    """
    n = len(monthly.get("free_cash_flow", []))
    gross = _gross_revenue_series(monthly, inputs)
    opex = monthly.get("opex", _zeros(n))
    capex = _capex_series(monthly)
    oil_arr = monthly.get("oil_bbl", _zeros(n))
    gas_arr = monthly.get("gas_mcf", _zeros(n))

    cap_pct = float(inputs.get("tsc_payment_cap_pct", 0.50))
    fee_per_boe = float(inputs.get("tsc_remuneration_per_boe", 1.50))
    contractor_tax = float(inputs.get("tsc_contractor_tax_pct", 0.35))

    reimburse_arr: list[float] = []
    fee_arr: list[float] = []
    tax_arr: list[float] = []
    contractor_cf: list[float] = []
    gov_arr: list[float] = []
    carry_arr: list[float] = []

    carry = 0.0
    for i in range(n):
        eligible = opex[i] + capex[i] + carry
        cap = max(0.0, gross[i]) * cap_pct
        reimburse = min(eligible, cap)
        carry = max(0.0, eligible - reimburse)
        boe = oil_arr[i] + gas_arr[i] / 6.0
        fee_gross = boe * fee_per_boe
        tax = max(0.0, fee_gross) * contractor_tax
        fee_net = fee_gross - tax
        contractor = reimburse + fee_net - capex[i]
        government = gross[i] - reimburse - fee_gross + tax  # tax flows back to gov

        reimburse_arr.append(reimburse)
        fee_arr.append(fee_gross)
        tax_arr.append(tax)
        contractor_cf.append(contractor)
        gov_arr.append(government)
        carry_arr.append(carry)

    return {
        "regime": "technical_service_contract",
        "contractor_cf": contractor_cf,
        "monthly": {
            "gross_revenue": _round_list(gross),
            "cost_reimbursement": _round_list(reimburse_arr),
            "remuneration_fee": _round_list(fee_arr),
            "contractor_tax": _round_list(tax_arr),
            "carry_forward": _round_list(carry_arr),
            "government_take": _round_list(gov_arr),
            "contractor_cf": _round_list(contractor_cf),
        },
        "summary": {
            "regime": "technical_service_contract",
            "payment_cap_pct": cap_pct,
            "remuneration_per_boe": fee_per_boe,
            "contractor_tax_pct": contractor_tax,
            "reimbursement_total": round(sum(reimburse_arr), 2),
            "remuneration_total": round(sum(fee_arr), 2),
            "contractor_tax_total": round(sum(tax_arr), 2),
            "carry_forward_end": round(carry_arr[-1] if carry_arr else 0.0, 2),
            "government_total": round(sum(gov_arr), 2),
            "contractor_total_cf": round(sum(contractor_cf), 2),
            "note": "Contractor recovers eligible costs against periodic cap; flat fee per BOE; no hydrocarbon ownership.",
        },
    }


def _progressive_royalty(price: float, tiers: list[dict[str, float]]) -> float:
    """Compute weighted royalty rate at a given oil price using progressive tiers.

    ``tiers`` is a list of ``{"upper": <price ceiling or None>, "rate": <fraction>}``
    sorted ascending. Saudi-style default per AGSI:
        [
          {"upper": 70.0,  "rate": 0.15},
          {"upper": 100.0, "rate": 0.45},
          {"upper": None,  "rate": 0.80},
        ]
    Returns the *effective* royalty rate (royalty_$ / price_$) at the given price.
    """
    if price <= 0 or not tiers:
        return 0.0
    royalty_dollars = 0.0
    prev = 0.0
    for tier in tiers:
        upper = tier.get("upper")
        rate = float(tier.get("rate", 0.0))
        ceil = price if upper is None else min(price, float(upper))
        if ceil <= prev:
            continue
        royalty_dollars += (ceil - prev) * rate
        prev = ceil
        if upper is not None and price <= upper:
            break
    return royalty_dollars / price


def _concession(
    monthly: dict[str, list[float]], inputs: dict[str, Any]
) -> dict[str, Any]:
    """Middle East concession: royalty + corporate income tax.

    Royalty can be flat (``concession_royalty_pct``) or progressive
    (``concession_royalty_tiers`` — list of ``{"upper": price|None, "rate": frac}``).
    When ``concession_royalty_progressive`` is true and tiers are absent, the
    Saudi-style defaults apply: 15% / 45% / 80% at $70 / $100. Income tax is
    flat (default 50% per AGSI).
    """
    n = len(monthly.get("free_cash_flow", []))
    gross = _gross_revenue_series(monthly, inputs)
    opex = monthly.get("opex", _zeros(n))
    capex = _capex_series(monthly)
    oil_price = float(inputs.get("oil_price", 0.0))

    progressive = bool(inputs.get("concession_royalty_progressive", False))
    flat_rate = float(inputs.get("concession_royalty_pct", 0.20))
    tax_rate = float(inputs.get("concession_income_tax_pct", 0.50))
    tiers = inputs.get("concession_royalty_tiers")
    if progressive and not tiers:
        tiers = [
            {"upper": 70.0, "rate": 0.15},
            {"upper": 100.0, "rate": 0.45},
            {"upper": None, "rate": 0.80},
        ]
    if progressive and tiers:
        effective_royalty_rate = _progressive_royalty(oil_price, tiers)
    else:
        effective_royalty_rate = flat_rate

    royalty_arr: list[float] = []
    taxable_arr: list[float] = []
    tax_arr: list[float] = []
    contractor_cf: list[float] = []
    gov_arr: list[float] = []

    for i in range(n):
        roy = gross[i] * effective_royalty_rate
        taxable = gross[i] - roy - opex[i] - capex[i]
        tax = max(0.0, taxable) * tax_rate
        contractor = gross[i] - roy - opex[i] - capex[i] - tax
        government = roy + tax

        royalty_arr.append(roy)
        taxable_arr.append(taxable)
        tax_arr.append(tax)
        contractor_cf.append(contractor)
        gov_arr.append(government)

    return {
        "regime": "concession_tax_royalty",
        "contractor_cf": contractor_cf,
        "monthly": {
            "gross_revenue": _round_list(gross),
            "royalty": _round_list(royalty_arr),
            "taxable_income": _round_list(taxable_arr),
            "income_tax": _round_list(tax_arr),
            "government_take": _round_list(gov_arr),
            "contractor_cf": _round_list(contractor_cf),
        },
        "summary": {
            "regime": "concession_tax_royalty",
            "royalty_progressive": progressive,
            "effective_royalty_rate": round(effective_royalty_rate, 4),
            "flat_royalty_pct": flat_rate,
            "income_tax_pct": tax_rate,
            "tiers_used": tiers if progressive else None,
            "royalty_total": round(sum(royalty_arr), 2),
            "income_tax_total": round(sum(tax_arr), 2),
            "government_total": round(sum(gov_arr), 2),
            "contractor_total_cf": round(sum(contractor_cf), 2),
            "note": "Saudi-style defaults: 15% to $70, 45% $70-$100, 80% above $100; income tax 50% (AGSI).",
        },
    }


__all__ = [
    "SUPPORTED_REGIMES",
    "apply_fiscal_regime",
]
