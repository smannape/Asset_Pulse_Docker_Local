"""
CAPEX and OPEX cost-model formulas for wells, pipelines, gathering systems and facilities.

Sources / seed values:
- EIA upstream cost study: https://www.eia.gov/analysis/studies/drilling/pdf/upstream.pdf
- INGAA midstream infrastructure study: https://ingaa.org/wp-content/uploads/2016/04/27962.pdf
- COPAS ARO accounting: https://copas.org/asset-retirement-obligation-accounting-in-the-oil-and-gas-industry/
- CGA operating expense guidance: https://www.cgaus.com/oil-gas-operating-expenses-preparing-compliant-forecasts/

All money values are nominal USD unless otherwise stated.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# -----------------------------------------------------------------------------
# Well CAPEX
# -----------------------------------------------------------------------------

def well_capex(
    drilling: float = 0.0,
    completion: float = 0.0,
    tangible_equipment: float = 0.0,
    pad_site_road: float = 0.0,
    lease_equipment: float = 0.0,
    artificial_lift: float = 0.0,
    flowline_hookup: float = 0.0,
    scada_metering: float = 0.0,
    contingency_pct: float = 0.10,
    capitalized_aro: float = 0.0,
) -> dict:
    """Bottom-up well CAPEX. Returns dict with subtotal, contingency and total."""
    subtotal = (
        drilling
        + completion
        + tangible_equipment
        + pad_site_road
        + lease_equipment
        + artificial_lift
        + flowline_hookup
        + scada_metering
    )
    contingency = subtotal * contingency_pct
    total = subtotal + contingency + capitalized_aro
    return {
        "subtotal": round(subtotal, 2),
        "contingency": round(contingency, 2),
        "capitalized_aro": round(capitalized_aro, 2),
        "total_capex": round(total, 2),
    }


# -----------------------------------------------------------------------------
# Pipeline CAPEX (INGAA inch-mile method)
# -----------------------------------------------------------------------------

def pipeline_capex(
    length_miles: float,
    diameter_inches: float,
    base_cost_per_inch_mile: float = 155_000.0,
    regional_factor: float = 1.0,
    compressor_hp: float = 0.0,
    cost_per_hp: float = 3_000.0,
    compression_region_factor: float = 1.0,
    metering_scada: float = 0.0,
    tie_in_costs: float = 0.0,
    contingency_pct: float = 0.10,
) -> dict:
    pipe = length_miles * diameter_inches * base_cost_per_inch_mile * regional_factor
    compression = compressor_hp * cost_per_hp * compression_region_factor
    subtotal = pipe + compression + metering_scada + tie_in_costs
    contingency = subtotal * contingency_pct
    return {
        "pipe_capex": round(pipe, 2),
        "compression_capex": round(compression, 2),
        "metering_scada": round(metering_scada, 2),
        "tie_in": round(tie_in_costs, 2),
        "contingency": round(contingency, 2),
        "total_capex": round(subtotal + contingency, 2),
    }


# -----------------------------------------------------------------------------
# Facility CAPEX
# -----------------------------------------------------------------------------

def facility_capex(
    processing_capacity_mmcfd: float = 0.0,
    gas_processing_cost_per_mmcfd: float = 525_000.0,
    oil_handling_capacity_bopd: float = 0.0,
    oil_facility_unit_cost: float = 250.0,  # $/bopd seed
    water_handling_capacity_bwpd: float = 0.0,
    water_facility_unit_cost: float = 150.0,  # $/bwpd seed
    compression_hp: float = 0.0,
    cost_per_hp: float = 3_000.0,
    storage_capacity_bbl: float = 0.0,
    storage_cost_per_bbl: float = 15.0,
    power_or_grid: float = 0.0,
    controls_scada: float = 0.0,
    install_commission: float = 0.0,
    contingency_pct: float = 0.10,
) -> dict:
    gas_proc = processing_capacity_mmcfd * gas_processing_cost_per_mmcfd
    oil_h = oil_handling_capacity_bopd * oil_facility_unit_cost
    water_h = water_handling_capacity_bwpd * water_facility_unit_cost
    comp = compression_hp * cost_per_hp
    storage = storage_capacity_bbl * storage_cost_per_bbl
    subtotal = gas_proc + oil_h + water_h + comp + storage + power_or_grid + controls_scada + install_commission
    contingency = subtotal * contingency_pct
    return {
        "gas_processing": round(gas_proc, 2),
        "oil_handling": round(oil_h, 2),
        "water_handling": round(water_h, 2),
        "compression": round(comp, 2),
        "storage": round(storage, 2),
        "power_grid": round(power_or_grid, 2),
        "controls_scada": round(controls_scada, 2),
        "install_commission": round(install_commission, 2),
        "contingency": round(contingency, 2),
        "total_capex": round(subtotal + contingency, 2),
    }


# -----------------------------------------------------------------------------
# Asset Retirement Obligation
# -----------------------------------------------------------------------------

def aro_present_value(
    future_abandonment_cost: float,
    credit_adjusted_risk_free_rate: float,
    years_to_abandonment: float,
) -> float:
    return future_abandonment_cost / ((1.0 + credit_adjusted_risk_free_rate) ** years_to_abandonment)


# -----------------------------------------------------------------------------
# OPEX
# -----------------------------------------------------------------------------

def monthly_opex(
    fixed_cost_per_month: float,
    oil_bbl: float = 0.0,
    gas_mcf: float = 0.0,
    water_bbl: float = 0.0,
    oil_var_per_bbl: float = 0.0,
    gas_var_per_mcf: float = 0.0,
    water_var_per_bbl: float = 0.0,
    chemicals: float = 0.0,
    energy: float = 0.0,
    maintenance: float = 0.0,
    workover: float = 0.0,
    gathering_processing_transport: float = 0.0,
    production_taxes: float = 0.0,
    environmental: float = 0.0,
    allocated_g_and_a: float = 0.0,
) -> dict:
    var_oil = oil_var_per_bbl * oil_bbl
    var_gas = gas_var_per_mcf * gas_mcf
    var_water = water_var_per_bbl * water_bbl
    variable_total = var_oil + var_gas + var_water
    other = (
        chemicals
        + energy
        + maintenance
        + workover
        + gathering_processing_transport
        + production_taxes
        + environmental
        + allocated_g_and_a
    )
    total = fixed_cost_per_month + variable_total + other
    return {
        "fixed": round(fixed_cost_per_month, 2),
        "variable_oil": round(var_oil, 2),
        "variable_gas": round(var_gas, 2),
        "variable_water": round(var_water, 2),
        "other": round(other, 2),
        "total_opex": round(total, 2),
    }


# -----------------------------------------------------------------------------
# Revenue and Netback
# -----------------------------------------------------------------------------

def revenue(
    oil_bbl: float,
    gas_mcf: float,
    ngl_bbl: float,
    oil_price: float,
    gas_price: float,
    ngl_price: float,
    royalty_pct: float = 0.0,
    production_tax_pct: float = 0.0,
    transport_per_boe: float = 0.0,
    processing_per_boe: float = 0.0,
) -> dict:
    gross = oil_bbl * oil_price + gas_mcf * gas_price + ngl_bbl * ngl_price
    royalties = gross * royalty_pct
    prod_tax = gross * production_tax_pct
    # Convert mcf to BOE at 6 mcf/BOE for transport/processing per BOE costs
    boe = oil_bbl + ngl_bbl + gas_mcf / 6.0
    transport = transport_per_boe * boe
    processing = processing_per_boe * boe
    net = gross - royalties - prod_tax - transport - processing
    return {
        "gross_revenue": round(gross, 2),
        "royalties": round(royalties, 2),
        "production_taxes": round(prod_tax, 2),
        "transport": round(transport, 2),
        "processing": round(processing, 2),
        "net_revenue": round(net, 2),
        "boe": round(boe, 2),
    }


def netback_per_boe(operating_cash_flow_before_sustaining: float, boe: float) -> float:
    if boe <= 0:
        return 0.0
    return operating_cash_flow_before_sustaining / boe


__all__ = [
    "well_capex",
    "pipeline_capex",
    "facility_capex",
    "aro_present_value",
    "monthly_opex",
    "revenue",
    "netback_per_boe",
]
