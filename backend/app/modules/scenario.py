"""
Scenario engine: builds a monthly cash-flow projection from compact inputs and
returns NPV, PV-10, payback, economic limit and netback.

The engine supports exponential and Arps-style hyperbolic/harmonic decline:
    exponential: rate_t = rate_0 * exp(-D * t_years)
    hyperbolic:  rate_t = rate_0 / (1 + b * D_i * t_years) ** (1 / b)
    harmonic:    hyperbolic with b = 1
Production stops at economic limit OR when months_horizon is reached, whichever is first.
"""

from __future__ import annotations

import math
from typing import Any

from .cost_models import monthly_opex, revenue
from .economics import (
    economic_limit_rate_boe_per_month,
    free_cash_flow_series,
    npv,
    payback_months,
    pv10,
)
from .fiscal_regimes import SUPPORTED_REGIMES, apply_fiscal_regime


def _annual_to_monthly_decline(annual_decline: float) -> float:
    """Convert annual nominal decline (fraction) to monthly equivalent."""
    return 1.0 - (1.0 - annual_decline) ** (1.0 / 12.0)


def _decline_factor(t_month: int, annual_decline: float, model: str = "exponential", b_factor: float = 0.7) -> float:
    """Return production multiplier at month t for exponential or Arps decline.

    annual_decline is treated as the first-year effective decline fraction.
    For hyperbolic decline, convert that first-year effective decline to an
    initial nominal decline rate:
        q(1)/qi = 1 - annual_decline = (1 + b*Di)^(-1/b)
        Di = ((1 - annual_decline)^(-b) - 1) / b
    """
    decline = max(0.0, min(float(annual_decline), 0.999999))
    t_years = max(t_month, 0) / 12.0
    model_norm = (model or "exponential").lower()
    if model_norm == "exponential" or decline <= 0:
        return (1.0 - decline) ** t_years

    b = 1.0 if model_norm == "harmonic" else max(1e-6, min(float(b_factor), 2.0))
    di = ((1.0 - decline) ** (-b) - 1.0) / b
    return 1.0 / ((1.0 + b * di * t_years) ** (1.0 / b))


def project_scenario(inputs: dict) -> dict:
    """
    inputs schema (all values nominal USD unless stated):
      asset_name: str
      months_horizon: int          (e.g. 120)
      initial_oil_bopd: float
      initial_gas_mcfd: float
      initial_ngl_bpd: float
      annual_decline: float        (e.g. 0.25)
      decline_model: str           ("exponential", "hyperbolic", or "harmonic")
      b_factor: float              (0..2; used for hyperbolic decline)
      water_cut_initial: float     (0..1)
      water_cut_final: float       (linear interp over horizon)
      oil_price: float             (USD/bbl)
      gas_price: float             (USD/mcf)
      ngl_price: float             (USD/bbl)
      royalty_pct: float
      production_tax_pct: float
      transport_per_boe: float
      processing_per_boe: float
      fixed_opex_per_month: float
      oil_var_per_bbl: float
      gas_var_per_mcf: float
      water_var_per_bbl: float
      development_capex: float     (one-time at t=0)
      sustaining_capex_per_month: float
      abandonment_cost: float      (applied at end of horizon)
      discount_rate_annual: float  (e.g. 0.10)
      capex_multiplier: float      (overrun factor, default 1.0)
      opex_multiplier: float       (escalation factor, default 1.0)
      apply_economic_limit: bool   (truncate when monthly margin < 0)

    Returns kpis + monthly arrays + decline truncation flag.
    """
    horizon = int(inputs.get("months_horizon", 120))
    initial_bopd = float(inputs.get("initial_oil_bopd", 0.0))
    initial_mcfd = float(inputs.get("initial_gas_mcfd", 0.0))
    initial_nglbpd = float(inputs.get("initial_ngl_bpd", 0.0))
    annual_decline = float(inputs.get("annual_decline", 0.20))
    decline_model = str(inputs.get("decline_model", "exponential"))
    b_factor = float(inputs.get("b_factor", 0.7))

    wc0 = float(inputs.get("water_cut_initial", 0.30))
    wcf = float(inputs.get("water_cut_final", 0.80))

    oil_price = float(inputs.get("oil_price", 70.0))
    gas_price = float(inputs.get("gas_price", 3.0))
    ngl_price = float(inputs.get("ngl_price", 25.0))
    royalty = float(inputs.get("royalty_pct", 0.1875))
    prod_tax = float(inputs.get("production_tax_pct", 0.05))
    transport_boe = float(inputs.get("transport_per_boe", 1.50))
    processing_boe = float(inputs.get("processing_per_boe", 0.50))

    fixed = float(inputs.get("fixed_opex_per_month", 0.0))
    oil_var = float(inputs.get("oil_var_per_bbl", 0.0))
    gas_var = float(inputs.get("gas_var_per_mcf", 0.0))
    water_var = float(inputs.get("water_var_per_bbl", 0.0))

    dev_capex = float(inputs.get("development_capex", 0.0))
    sustaining = float(inputs.get("sustaining_capex_per_month", 0.0))
    abandonment = float(inputs.get("abandonment_cost", 0.0))

    discount = float(inputs.get("discount_rate_annual", 0.10))
    capex_mult = float(inputs.get("capex_multiplier", 1.0))
    opex_mult = float(inputs.get("opex_multiplier", 1.0))
    apply_el = bool(inputs.get("apply_economic_limit", True))

    days_per_month = 30.4375

    months = []
    monthly_revenue = []
    monthly_royalties = []
    monthly_taxes = []
    monthly_opex_arr = []
    monthly_sustain = []
    monthly_dev = []
    monthly_abandon = []
    monthly_cf = []
    monthly_oil_bbl = []
    monthly_gas_mcf = []
    monthly_water_bbl = []

    truncated_at = None

    for t in range(horizon + 1):  # t=0 captures dev capex
        decline_multiplier = _decline_factor(t, annual_decline, decline_model, b_factor)
        oil_bbl = initial_bopd * days_per_month * decline_multiplier
        gas_mcf = initial_mcfd * days_per_month * decline_multiplier
        ngl_bbl = initial_nglbpd * days_per_month * decline_multiplier
        # Linear water cut interpolation
        wc = wc0 + (wcf - wc0) * (t / max(horizon, 1))
        # Water bbl tied to oil rate via water cut (water/(oil+water) = wc -> water = oil*wc/(1-wc))
        water_bbl = oil_bbl * wc / max(1e-6, (1.0 - wc))

        rev = revenue(
            oil_bbl=oil_bbl,
            gas_mcf=gas_mcf,
            ngl_bbl=ngl_bbl,
            oil_price=oil_price,
            gas_price=gas_price,
            ngl_price=ngl_price,
            royalty_pct=royalty,
            production_tax_pct=prod_tax,
            transport_per_boe=transport_boe,
            processing_per_boe=processing_boe,
        )

        op = monthly_opex(
            fixed_cost_per_month=fixed * opex_mult,
            oil_bbl=oil_bbl,
            gas_mcf=gas_mcf,
            water_bbl=water_bbl,
            oil_var_per_bbl=oil_var * opex_mult,
            gas_var_per_mcf=gas_var * opex_mult,
            water_var_per_bbl=water_var * opex_mult,
        )

        # Capex at t=0 (multiplied), sustaining ongoing, abandonment at horizon
        dev = dev_capex * capex_mult if t == 0 else 0.0
        sus = sustaining * opex_mult if t > 0 else 0.0
        aban = abandonment if t == horizon else 0.0

        cf = (
            rev["net_revenue"]
            - op["total_opex"]
            - dev
            - sus
            - aban
        )

        # Economic limit truncation: if for 3 consecutive months we're below 0 margin (excl. capex), truncate
        margin_exc_capex = rev["net_revenue"] - op["total_opex"]
        if apply_el and t > 0 and margin_exc_capex < 0:
            # Stop here: pay abandonment now, no further production
            cf = rev["net_revenue"] - op["total_opex"] - sus - abandonment
            truncated_at = t
            months.append(t)
            monthly_revenue.append(rev["net_revenue"])
            monthly_royalties.append(rev["royalties"])
            monthly_taxes.append(rev["production_taxes"])
            monthly_opex_arr.append(op["total_opex"])
            monthly_sustain.append(sus)
            monthly_dev.append(dev)
            monthly_abandon.append(abandonment)
            monthly_cf.append(cf)
            monthly_oil_bbl.append(oil_bbl)
            monthly_gas_mcf.append(gas_mcf)
            monthly_water_bbl.append(water_bbl)
            break

        months.append(t)
        monthly_revenue.append(rev["net_revenue"])
        monthly_royalties.append(rev["royalties"])
        monthly_taxes.append(rev["production_taxes"])
        monthly_opex_arr.append(op["total_opex"])
        monthly_sustain.append(sus)
        monthly_dev.append(dev)
        monthly_abandon.append(aban)
        monthly_cf.append(cf)
        monthly_oil_bbl.append(oil_bbl)
        monthly_gas_mcf.append(gas_mcf)
        monthly_water_bbl.append(water_bbl)

    # Apply fiscal regime as a layer on top of base monthly cash flows.
    # Default = us_royalty_tax (no-op pass-through; preserves backward compatibility).
    fiscal_regime = str(inputs.get("fiscal_regime", "us_royalty_tax")).lower()
    if fiscal_regime not in SUPPORTED_REGIMES:
        fiscal_regime = "us_royalty_tax"
    fiscal = apply_fiscal_regime(
        regime=fiscal_regime,
        monthly={
            "net_revenue": monthly_revenue,
            "opex": monthly_opex_arr,
            "sustaining_capex": monthly_sustain,
            "dev_capex": monthly_dev,
            "abandonment": monthly_abandon,
            "free_cash_flow": monthly_cf,
            "oil_bbl": monthly_oil_bbl,
            "gas_mcf": monthly_gas_mcf,
        },
        inputs=inputs,
    )
    contractor_cf = list(fiscal["contractor_cf"])
    if fiscal_regime != "us_royalty_tax":
        # Replace base FCF with the contractor view so all KPIs reflect the regime.
        monthly_cf = contractor_cf

    npv_val = npv(monthly_cf, discount, period="month")
    pv10_val = npv(monthly_cf, 0.10, period="month")
    payback = payback_months(monthly_cf)

    # Economic limit at base economics
    base_oil_boe_price = oil_price  # simplified
    el = economic_limit_rate_boe_per_month(
        fixed_cost_per_month=fixed * opex_mult,
        realized_price_per_boe=base_oil_boe_price,
        royalty_per_boe=royalty * base_oil_boe_price,
        production_tax_per_boe=prod_tax * base_oil_boe_price,
        variable_cost_per_boe=oil_var * opex_mult,
        transport_processing_per_boe=transport_boe + processing_boe,
    )

    total_boe = sum(o + g / 6.0 for o, g in zip(monthly_oil_bbl, monthly_gas_mcf))
    total_cf_before_capex = sum(
        r - opx - sus for r, opx, sus in zip(monthly_revenue, monthly_opex_arr, monthly_sustain)
    )
    netback = total_cf_before_capex / total_boe if total_boe > 0 else 0.0

    return {
        "asset_name": inputs.get("asset_name", "asset"),
        "kpis": {
            "npv": round(npv_val, 2),
            "pv10": round(pv10_val, 2),
            "payback_months": payback,
            "economic_limit": el,
            "total_boe": round(total_boe, 2),
            "netback_per_boe": round(netback, 2),
            "truncated_at_month": truncated_at,
            "discount_rate_annual": discount,
            "decline_model": decline_model,
            "b_factor": b_factor,
            "fiscal_regime": fiscal_regime,
        },
        "fiscal": fiscal,
        "monthly": {
            "months": months,
            "net_revenue": [round(x, 2) for x in monthly_revenue],
            "opex": [round(x, 2) for x in monthly_opex_arr],
            "sustaining_capex": [round(x, 2) for x in monthly_sustain],
            "dev_capex": [round(x, 2) for x in monthly_dev],
            "abandonment": [round(x, 2) for x in monthly_abandon],
            "free_cash_flow": [round(x, 2) for x in monthly_cf],
            "oil_bbl": [round(x, 2) for x in monthly_oil_bbl],
            "gas_mcf": [round(x, 2) for x in monthly_gas_mcf],
            "water_bbl": [round(x, 2) for x in monthly_water_bbl],
        },
    }


def npv_only(inputs: dict) -> float:
    """Lightweight NPV used by tornado/Monte Carlo callbacks."""
    res = project_scenario(inputs)
    return res["kpis"]["npv"]


__all__ = ["project_scenario", "npv_only"]
