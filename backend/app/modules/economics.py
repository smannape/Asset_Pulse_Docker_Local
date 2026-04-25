"""
Economic indicators: NPV, PV-10, payback, breakeven price, economic limit.

References:
- Stout SEC reserve reporting: https://www.stout.com/en/insights/article/understanding-sec-oil-and-gas-reserve-reporting
- Deloitte DART Topic 12: https://dart.deloitte.com/USDART/home/accounting/sec/sec-staff-bulletins/staff-accounting-bulletins/topic-12-oil-gas-producing-activities
"""

from __future__ import annotations

from typing import Iterable


def npv(cash_flows: Iterable[float], discount_rate: float, period: str = "month") -> float:
    """
    NPV with cash_flows[0] at t=0.
    period: "month" -> rate per month = discount_rate / 12 (rate is annual)
            "year"  -> rate per year  = discount_rate
    """
    if period == "month":
        r = discount_rate / 12.0
    elif period == "year":
        r = discount_rate
    else:
        raise ValueError("period must be 'month' or 'year'")
    total = 0.0
    for t, cf in enumerate(cash_flows):
        total += cf / ((1.0 + r) ** t)
    return total


def pv10(cash_flows: Iterable[float], period: str = "year") -> float:
    """SEC-style PV-10 using a 10% annual discount."""
    return npv(cash_flows, 0.10, period=period)


def payback_months(cash_flows_monthly: Iterable[float]) -> float | None:
    """Months until cumulative cash flow turns non-negative. None if never."""
    cum = 0.0
    cf_list = list(cash_flows_monthly)
    for i, cf in enumerate(cf_list):
        cum += cf
        if cum >= 0 and i > 0:
            # Linear interpolation within the month
            prev_cum = cum - cf
            if cf == 0:
                return float(i)
            frac = -prev_cum / cf if cf != 0 else 0.0
            return round(i - 1 + max(0.0, min(1.0, frac)), 2)
    return None


def economic_limit_rate_boe_per_month(
    fixed_cost_per_month: float,
    realized_price_per_boe: float,
    royalty_per_boe: float,
    production_tax_per_boe: float,
    variable_cost_per_boe: float,
    transport_processing_per_boe: float,
) -> dict:
    net_price = (
        realized_price_per_boe
        - royalty_per_boe
        - production_tax_per_boe
        - variable_cost_per_boe
        - transport_processing_per_boe
    )
    if net_price <= 0:
        return {
            "net_price_per_boe": round(net_price, 4),
            "economic_limit_boe_per_month": None,
            "note": "Net price per BOE is non-positive; asset is uneconomic at any rate.",
        }
    rate = fixed_cost_per_month / net_price
    return {
        "net_price_per_boe": round(net_price, 4),
        "economic_limit_boe_per_month": round(rate, 2),
        "note": "Below this rate, asset cannot cover fixed cost.",
    }


def free_cash_flow_series(
    monthly_revenue: list[float],
    monthly_royalties: list[float],
    monthly_taxes: list[float],
    monthly_opex: list[float],
    monthly_sustaining_capex: list[float],
    monthly_dev_capex: list[float],
    monthly_abandonment: list[float],
    monthly_income_tax: list[float] | None = None,
) -> list[float]:
    n = len(monthly_revenue)
    income_tax = monthly_income_tax or [0.0] * n
    fcf = []
    for t in range(n):
        cf = (
            monthly_revenue[t]
            - monthly_royalties[t]
            - monthly_taxes[t]
            - monthly_opex[t]
            - monthly_sustaining_capex[t]
            - monthly_dev_capex[t]
            - monthly_abandonment[t]
            - income_tax[t]
        )
        fcf.append(cf)
    return fcf


def breakeven_price(
    base_oil_price: float,
    npv_at_base_price: float,
    sensitivity_per_dollar: float,
) -> float | None:
    """
    Linear-approximation breakeven price.
    sensitivity_per_dollar = dNPV/dPrice estimated locally.
    """
    if sensitivity_per_dollar == 0:
        return None
    return base_oil_price - (npv_at_base_price / sensitivity_per_dollar)


__all__ = [
    "npv",
    "pv10",
    "payback_months",
    "economic_limit_rate_boe_per_month",
    "free_cash_flow_series",
    "breakeven_price",
]
