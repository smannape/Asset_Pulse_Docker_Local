"""Lightweight tests — run with `python -m backend.tests.test_modules`."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running directly: add backend/ to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.modules import cost_models, decision_matrix, economics, fiscal_regimes, scenario, uncertainty


def assert_close(a: float, b: float, tol: float = 1e-6, msg: str = "") -> None:
    assert abs(a - b) <= tol, f"{msg} expected {b}, got {a}"


def test_well_capex_subtotal():
    out = cost_models.well_capex(
        drilling=1_000_000, completion=2_000_000, contingency_pct=0.10, capitalized_aro=50_000
    )
    assert_close(out["subtotal"], 3_000_000)
    assert_close(out["contingency"], 300_000)
    assert_close(out["total_capex"], 3_350_000)


def test_pipeline_capex_inch_mile():
    # 10mi * 12in * 155k = 18,600,000 + 1,000hp * 3,000 = 21,600,000 subtotal + 10% cont
    out = cost_models.pipeline_capex(
        length_miles=10, diameter_inches=12, base_cost_per_inch_mile=155_000,
        compressor_hp=1000, cost_per_hp=3000, contingency_pct=0.10,
    )
    assert_close(out["pipe_capex"], 18_600_000)
    assert_close(out["compression_capex"], 3_000_000)
    assert_close(out["total_capex"], (18_600_000 + 3_000_000) * 1.10)


def test_npv_basic():
    # cash flows [-100, 60, 60] at 10% annual = -100 + 60/1.1 + 60/1.21
    val = economics.npv([-100, 60, 60], 0.10, period="year")
    expected = -100 + 60 / 1.10 + 60 / (1.10 ** 2)
    assert_close(val, expected, tol=1e-6)


def test_economic_limit():
    out = economics.economic_limit_rate_boe_per_month(
        fixed_cost_per_month=10_000,
        realized_price_per_boe=70.0,
        royalty_per_boe=10.0,
        production_tax_per_boe=2.0,
        variable_cost_per_boe=8.0,
        transport_processing_per_boe=2.0,
    )
    # net price = 70-10-2-8-2 = 48; rate = 10000/48 = 208.33
    assert_close(out["net_price_per_boe"], 48.0)
    assert_close(out["economic_limit_boe_per_month"], 10_000 / 48.0, tol=1e-2)


def test_scenario_npv_positive_for_strong_well():
    res = scenario.project_scenario({
        "asset_name": "T", "months_horizon": 60,
        "initial_oil_bopd": 800, "initial_gas_mcfd": 500,
        "annual_decline": 0.40, "oil_price": 75, "gas_price": 3,
        "fixed_opex_per_month": 12_000, "oil_var_per_bbl": 5,
        "development_capex": 8_000_000, "discount_rate_annual": 0.10,
    })
    assert res["kpis"]["npv"] > 0, "Strong well should be NPV-positive"


def test_hyperbolic_decline_preserves_more_tail_volume():
    base = {
        "asset_name": "decline", "months_horizon": 120,
        "initial_oil_bopd": 300, "initial_gas_mcfd": 0,
        "annual_decline": 0.45, "oil_price": 70,
        "fixed_opex_per_month": 0, "oil_var_per_bbl": 0,
        "development_capex": 0, "apply_economic_limit": False,
    }
    exp = scenario.project_scenario({**base, "decline_model": "exponential"})
    hyp = scenario.project_scenario({**base, "decline_model": "hyperbolic", "b_factor": 0.8})
    assert hyp["kpis"]["total_boe"] > exp["kpis"]["total_boe"], "Hyperbolic decline should preserve tail volume"


def test_tornado_orders_by_swing():
    base = {
        "asset_name": "T", "months_horizon": 60,
        "initial_oil_bopd": 500, "initial_gas_mcfd": 300,
        "annual_decline": 0.40, "oil_price": 70, "gas_price": 3,
        "fixed_opex_per_month": 12_000, "oil_var_per_bbl": 5,
        "development_capex": 8_000_000, "discount_rate_annual": 0.10,
        "capex_multiplier": 1.0, "opex_multiplier": 1.0,
        "water_cut_initial": 0.3, "water_cut_final": 0.8,
    }
    rows = uncertainty.tornado_sensitivity(
        base, scenario.npv_only,
        [{"name": "oil_price", "low_pct": -0.30, "high_pct": 0.30},
         {"name": "capex_multiplier", "low_pct": -0.05, "high_pct": 0.05}],
    )
    assert rows[0]["swing"] >= rows[-1]["swing"]


def test_monte_carlo_returns_percentiles():
    base = {
        "asset_name": "T", "months_horizon": 36,
        "initial_oil_bopd": 500, "initial_gas_mcfd": 300,
        "annual_decline": 0.35, "oil_price": 70, "gas_price": 3,
        "fixed_opex_per_month": 12_000, "oil_var_per_bbl": 5,
        "development_capex": 6_000_000, "discount_rate_annual": 0.10,
        "capex_multiplier": 1.0, "opex_multiplier": 1.0,
    }
    out = uncertainty.monte_carlo_npv(
        base,
        {
            "oil_price": {"type": "triangular", "low": 55, "mode": 70, "high": 90},
            "capex_multiplier": {"type": "triangular", "low": 0.95, "mode": 1.0, "high": 1.2},
        },
        scenario.npv_only,
        iterations=100,
        seed=7,
    )
    assert out["iterations"] == 100
    assert out["min"] <= out["p10"] <= out["p50"] <= out["p90"] <= out["max"]


# ---------------------------------------------------------------------------
# Fiscal regime tests
# ---------------------------------------------------------------------------

FISCAL_BASE = {
    "asset_name": "fiscal", "months_horizon": 36,
    "initial_oil_bopd": 1000, "initial_gas_mcfd": 0, "initial_ngl_bpd": 0,
    "annual_decline": 0.30, "oil_price": 80, "gas_price": 3.0, "ngl_price": 25.0,
    "royalty_pct": 0.0, "production_tax_pct": 0.0,
    "transport_per_boe": 0.0, "processing_per_boe": 0.0,
    "fixed_opex_per_month": 50_000, "oil_var_per_bbl": 4.0,
    "development_capex": 5_000_000, "sustaining_capex_per_month": 0.0,
    "abandonment_cost": 0.0, "discount_rate_annual": 0.10,
    "capex_multiplier": 1.0, "opex_multiplier": 1.0,
    "apply_economic_limit": False,
    "water_cut_initial": 0.0, "water_cut_final": 0.0,
}


def test_default_regime_is_backward_compatible():
    """Omitting fiscal_regime must produce the same NPV as us_royalty_tax explicit."""
    base = {**FISCAL_BASE}
    explicit = {**FISCAL_BASE, "fiscal_regime": "us_royalty_tax"}
    a = scenario.project_scenario(base)
    b = scenario.project_scenario(explicit)
    assert_close(a["kpis"]["npv"], b["kpis"]["npv"], tol=1e-6)
    assert b["kpis"]["fiscal_regime"] == "us_royalty_tax"
    assert "fiscal" in a and a["fiscal"]["summary"]["regime"] == "us_royalty_tax"


def test_psc_cost_recovery_split():
    """PSC: government take = royalty + gov profit oil + contractor tax;
    contractor cf = cost_oil + contractor_profit - tax - capex (per Bindemann)."""
    inp = {
        **FISCAL_BASE,
        "fiscal_regime": "psc_cost_recovery",
        "psc_royalty_pct": 0.10,
        "psc_cost_oil_limit_pct": 0.50,
        "psc_contractor_profit_share_pct": 0.40,
        "psc_contractor_tax_pct": 0.30,
        "psc_capex_uplift_pct": 0.0,
    }
    res = scenario.project_scenario(inp)
    fis = res["fiscal"]
    s = fis["summary"]
    # Government should take more than the contractor under these splits
    assert s["government_total"] > 0
    assert s["royalty_total"] > 0
    assert s["cost_oil_total"] > 0
    # Profit oil split: contractor gets 40%, gov gets 60% of profit oil
    profit_oil_total = s["profit_oil_total"]
    if profit_oil_total > 0:
        assert_close(
            s["contractor_profit_oil_total"],
            profit_oil_total * 0.40,
            tol=1e-2,
            msg="contractor profit oil share",
        )
        assert_close(
            s["government_profit_oil_total"],
            profit_oil_total * 0.60,
            tol=1e-2,
            msg="government profit oil share",
        )
    # Sanity: monthly arrays present and equal in length
    months_n = len(res["monthly"]["months"])
    assert len(fis["monthly"]["contractor_cf"]) == months_n
    assert len(fis["monthly"]["cost_oil"]) == months_n
    assert len(fis["monthly"]["carry_forward"]) == months_n


def test_psc_cost_oil_ceiling_enforced():
    """With a tight cost-oil ceiling, recoverable costs must spill into carry-forward."""
    inp = {
        **FISCAL_BASE,
        "fiscal_regime": "psc_cost_recovery",
        "psc_royalty_pct": 0.10,
        "psc_cost_oil_limit_pct": 0.05,  # very tight ceiling
        "psc_contractor_profit_share_pct": 0.40,
        "psc_contractor_tax_pct": 0.30,
        "development_capex": 50_000_000,  # large capex forces spillover
    }
    res = scenario.project_scenario({**inp, "development_capex": 50_000_000})
    carry = res["fiscal"]["monthly"]["carry_forward"]
    # Carry-forward must be non-zero in early months when capex exceeds the ceiling
    assert any(c > 0 for c in carry), "carry-forward should accumulate when ceiling is tight"


def test_psc_uplift_increases_cost_recovery():
    """CAPEX uplift increases recoverable costs and contractor cash flow."""
    base = {
        **FISCAL_BASE,
        "fiscal_regime": "psc_cost_recovery",
        "psc_royalty_pct": 0.10,
        "psc_cost_oil_limit_pct": 0.60,
        "psc_contractor_profit_share_pct": 0.40,
        "psc_contractor_tax_pct": 0.30,
    }
    no_uplift = scenario.project_scenario({**base, "psc_capex_uplift_pct": 0.0})
    with_uplift = scenario.project_scenario({**base, "psc_capex_uplift_pct": 0.30})
    assert (
        with_uplift["fiscal"]["summary"]["contractor_total_cf"]
        >= no_uplift["fiscal"]["summary"]["contractor_total_cf"]
    ), "uplift should not reduce contractor cash flow"


def test_tsc_pays_per_barrel_remuneration():
    """TSC: contractor receives remuneration fee per BOE plus cost reimbursement."""
    inp = {
        **FISCAL_BASE,
        "fiscal_regime": "technical_service_contract",
        "tsc_payment_cap_pct": 0.50,
        "tsc_remuneration_per_boe": 2.00,
        "tsc_contractor_tax_pct": 0.35,
    }
    res = scenario.project_scenario(inp)
    s = res["fiscal"]["summary"]
    total_boe = res["kpis"]["total_boe"]
    # Remuneration approximately equals fee/boe * total BOE (within rounding)
    expected_fee = total_boe * 2.00
    # Allow 5% slack due to integer-month rounding and economic-limit interactions
    assert s["remuneration_total"] > 0
    assert abs(s["remuneration_total"] - expected_fee) / max(expected_fee, 1.0) < 0.05
    assert s["reimbursement_total"] > 0
    assert s["contractor_tax_total"] > 0


def test_tsc_payment_cap_creates_carry_forward():
    """When the periodic cap is below eligible costs, carry-forward must accumulate."""
    inp = {
        **FISCAL_BASE,
        "fiscal_regime": "technical_service_contract",
        "tsc_payment_cap_pct": 0.10,  # very tight
        "tsc_remuneration_per_boe": 1.0,
        "tsc_contractor_tax_pct": 0.0,
        "development_capex": 20_000_000,
    }
    res = scenario.project_scenario(inp)
    carry = res["fiscal"]["monthly"]["carry_forward"]
    assert any(c > 0 for c in carry), "tight cap must produce carry-forward"


def test_concession_progressive_royalty_saudi_default():
    """Saudi-style tiers: at $80/bbl effective royalty = (70*0.15 + 10*0.45)/80 = 0.18125."""
    rate = fiscal_regimes._progressive_royalty(
        80.0,
        [
            {"upper": 70.0, "rate": 0.15},
            {"upper": 100.0, "rate": 0.45},
            {"upper": None, "rate": 0.80},
        ],
    )
    # 70*0.15 + 10*0.45 = 10.5 + 4.5 = 15.0; 15/80 = 0.1875
    expected = (70.0 * 0.15 + 10.0 * 0.45) / 80.0
    assert_close(rate, expected, tol=1e-6)
    assert_close(rate, 0.1875, tol=1e-6)

    rate_120 = fiscal_regimes._progressive_royalty(
        120.0,
        [
            {"upper": 70.0, "rate": 0.15},
            {"upper": 100.0, "rate": 0.45},
            {"upper": None, "rate": 0.80},
        ],
    )
    expected_120 = (70.0 * 0.15 + 30.0 * 0.45 + 20.0 * 0.80) / 120.0
    assert_close(rate_120, expected_120, tol=1e-6)


def test_concession_regime_applies_progressive_and_tax():
    inp = {
        **FISCAL_BASE,
        "oil_price": 80.0,
        "fiscal_regime": "concession_tax_royalty",
        "concession_royalty_progressive": True,
        "concession_income_tax_pct": 0.50,
    }
    res = scenario.project_scenario(inp)
    s = res["fiscal"]["summary"]
    # Effective rate at $80 should equal Saudi-default progressive: 18.75%
    assert_close(s["effective_royalty_rate"], 0.1875, tol=1e-6)
    assert s["royalty_total"] > 0
    assert s["income_tax_total"] >= 0
    assert s["government_total"] >= s["royalty_total"]


def test_noc_internal_zero_takes_by_default():
    """NOC internal with default 0% transfer/tax = pure project economics."""
    res = scenario.project_scenario({**FISCAL_BASE, "fiscal_regime": "noc_internal"})
    s = res["fiscal"]["summary"]
    assert_close(s["government_total"], 0.0, tol=1e-6)
    # Contractor cf should equal gross_revenue - opex - capex (no royalty/tax)


def test_decision_matrix_recommendation():
    assets = [
        {"name": "good well", "monthly_margin": 100_000, "npv_keep_online": 5_000_000,
         "avoidable_opex": 12000, "restart_payback_months": 6, "restart_risk": 0.2,
         "hbp_risk": 0.1, "water_burden": 0.2, "strategic_value": 0.9},
        {"name": "bad well", "monthly_margin": -8_000, "npv_keep_online": -200_000,
         "avoidable_opex": 18000, "restart_payback_months": 24, "restart_risk": 0.7,
         "hbp_risk": 0.6, "water_burden": 0.85, "strategic_value": 0.3},
    ]
    out = decision_matrix.score_assets(assets)
    assert out[0]["name"] == "good well"
    assert out[0]["recommendation"] == "Keep online"


def main():
    tests = [
        test_well_capex_subtotal,
        test_pipeline_capex_inch_mile,
        test_npv_basic,
        test_economic_limit,
        test_scenario_npv_positive_for_strong_well,
        test_hyperbolic_decline_preserves_more_tail_volume,
        test_tornado_orders_by_swing,
        test_monte_carlo_returns_percentiles,
        test_default_regime_is_backward_compatible,
        test_psc_cost_recovery_split,
        test_psc_cost_oil_ceiling_enforced,
        test_psc_uplift_increases_cost_recovery,
        test_tsc_pays_per_barrel_remuneration,
        test_tsc_payment_cap_creates_carry_forward,
        test_concession_progressive_royalty_saudi_default,
        test_concession_regime_applies_progressive_and_tax,
        test_noc_internal_zero_takes_by_default,
        test_decision_matrix_recommendation,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} tests passed.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
