"""Seed sample data and bootstrap first admin user."""

from __future__ import annotations

import os

from sqlalchemy import select

from .database import (
    Asset, CostProfile, PriceDeck, Scenario, User,
    init_db, get_session,
)

# ---------------------------------------------------------------------------
# Sample data (unchanged from original)
# ---------------------------------------------------------------------------

SAMPLE_PRICE_DECK = {
    "name": "Base 2025",
    "oil_price": 72.0,
    "gas_price": 2.85,
    "ngl_price": 24.0,
    "differentials": {"oil_diff": -3.0, "gas_diff": -0.40},
}

SAMPLE_ASSETS = [
    {
        "name": "Eagle Ford Pad-3 Well A",
        "asset_type": "well",
        "region": "TX-Eagle Ford",
        "metadata_json": {"operator": "Demo Co", "lateral_ft": 9500, "spud_year": 2022},
        "capex_inputs": {
            "drilling": 3_400_000, "completion": 4_800_000,
            "tangible_equipment": 350_000, "pad_site_road": 250_000,
            "lease_equipment": 180_000, "artificial_lift": 120_000,
            "flowline_hookup": 90_000, "scada_metering": 40_000,
            "contingency_pct": 0.10, "capitalized_aro": 60_000,
        },
        "opex_inputs": {
            "fixed_opex_per_month": 14_000,
            "oil_var_per_bbl": 4.5, "gas_var_per_mcf": 0.20, "water_var_per_bbl": 1.50,
        },
        "decline_inputs": {
            "initial_oil_bopd": 650, "initial_gas_mcfd": 420, "initial_ngl_bpd": 35,
            "annual_decline": 0.45, "water_cut_initial": 0.25, "water_cut_final": 0.85,
        },
    },
    {
        "name": "Eagle Ford Pad-3 Well B",
        "asset_type": "well",
        "region": "TX-Eagle Ford",
        "metadata_json": {"operator": "Demo Co", "lateral_ft": 8200, "spud_year": 2021},
        "capex_inputs": {
            "drilling": 3_200_000, "completion": 4_500_000,
            "tangible_equipment": 320_000, "pad_site_road": 240_000,
            "lease_equipment": 170_000, "artificial_lift": 140_000,
            "flowline_hookup": 85_000, "scada_metering": 38_000,
            "contingency_pct": 0.10, "capitalized_aro": 55_000,
        },
        "opex_inputs": {
            "fixed_opex_per_month": 16_500,
            "oil_var_per_bbl": 5.2, "gas_var_per_mcf": 0.22, "water_var_per_bbl": 2.10,
        },
        "decline_inputs": {
            "initial_oil_bopd": 280, "initial_gas_mcfd": 160, "initial_ngl_bpd": 12,
            "annual_decline": 0.30, "water_cut_initial": 0.55, "water_cut_final": 0.92,
        },
    },
    {
        "name": "Permian Stripper Well-12",
        "asset_type": "well",
        "region": "TX-Permian",
        "metadata_json": {"operator": "Demo Co", "spud_year": 2008, "lift": "rod pump"},
        "capex_inputs": {
            "drilling": 0, "completion": 0,
            "tangible_equipment": 0, "pad_site_road": 0,
            "lease_equipment": 25_000, "artificial_lift": 35_000,
            "flowline_hookup": 0, "scada_metering": 5_000,
            "contingency_pct": 0.05, "capitalized_aro": 25_000,
        },
        "opex_inputs": {
            "fixed_opex_per_month": 9_500,
            "oil_var_per_bbl": 6.5, "gas_var_per_mcf": 0.10, "water_var_per_bbl": 3.20,
        },
        "decline_inputs": {
            "initial_oil_bopd": 12, "initial_gas_mcfd": 8, "initial_ngl_bpd": 0,
            "annual_decline": 0.08, "water_cut_initial": 0.92, "water_cut_final": 0.97,
        },
    },
    {
        "name": "Bakken Trunk Pipeline",
        "asset_type": "pipeline",
        "region": "ND-Bakken",
        "metadata_json": {"length_miles": 42, "diameter_in": 12, "throughput_bopd": 35_000},
        "capex_inputs": {
            "length_miles": 42, "diameter_inches": 12,
            "base_cost_per_inch_mile": 155_000, "regional_factor": 1.10,
            "compressor_hp": 0, "metering_scada": 350_000, "tie_in_costs": 220_000,
            "contingency_pct": 0.10,
        },
        "opex_inputs": {"fixed_opex_per_month": 65_000, "oil_var_per_bbl": 0.35},
        "decline_inputs": {},
    },
    {
        "name": "Central Gathering Facility",
        "asset_type": "facility",
        "region": "TX-Eagle Ford",
        "metadata_json": {"throughput_mmcfd": 30, "oil_bopd": 8000, "water_bwpd": 25000},
        "capex_inputs": {
            "processing_capacity_mmcfd": 30, "oil_handling_capacity_bopd": 8000,
            "water_handling_capacity_bwpd": 25000, "compression_hp": 4500,
            "storage_capacity_bbl": 12000, "power_or_grid": 1_200_000,
            "controls_scada": 480_000, "install_commission": 950_000,
            "contingency_pct": 0.12,
        },
        "opex_inputs": {"fixed_opex_per_month": 220_000},
        "decline_inputs": {},
    },
]

SAMPLE_SCENARIOS = [
    {
        "name": "Base Case - Eagle Ford A",
        "inputs": {
            "asset_name": "Eagle Ford Pad-3 Well A",
            "months_horizon": 120,
            "initial_oil_bopd": 650, "initial_gas_mcfd": 420, "initial_ngl_bpd": 35,
            "annual_decline": 0.45,
            "water_cut_initial": 0.25, "water_cut_final": 0.85,
            "oil_price": 72, "gas_price": 2.85, "ngl_price": 24,
            "royalty_pct": 0.1875, "production_tax_pct": 0.045,
            "transport_per_boe": 1.50, "processing_per_boe": 0.50,
            "fixed_opex_per_month": 14000,
            "oil_var_per_bbl": 4.5, "gas_var_per_mcf": 0.20, "water_var_per_bbl": 1.50,
            "development_capex": 9_290_000,
            "sustaining_capex_per_month": 4500,
            "abandonment_cost": 180_000,
            "discount_rate_annual": 0.10,
            "capex_multiplier": 1.0, "opex_multiplier": 1.0,
            "apply_economic_limit": True,
        },
    },
]


def _create_default_admin() -> bool:
    """Create the first admin user from env vars if no users exist. Returns True if created."""
    from .modules.auth import hash_password
    email = os.environ.get("ADMIN_EMAIL", "admin@assetpulse.local")
    password = os.environ.get("ADMIN_PASSWORD", "AssetPulse2025!")
    with get_session() as s:
        existing = s.execute(select(User)).first()
        if existing:
            return False
        admin = User(
            email=email,
            full_name="System Admin",
            password_hash=hash_password(password),
            role="admin",
            is_active=True,
        )
        s.add(admin)
    return True


def seed() -> dict:
    init_db()

    # Bootstrap admin user (runs before asset seed so a user always exists)
    admin_created = False
    try:
        admin_created = _create_default_admin()
    except Exception:
        pass

    inserted_assets = 0
    inserted_scenarios = 0

    with get_session() as s:
        existing = s.execute(select(Asset)).first()
        if existing:
            return {"status": "already_seeded", "admin_created": admin_created}

        s.add(PriceDeck(**SAMPLE_PRICE_DECK))

        for a in SAMPLE_ASSETS:
            asset = Asset(
                name=a["name"], asset_type=a["asset_type"],
                region=a["region"], metadata_json=a["metadata_json"],
            )
            s.add(asset)
            s.flush()
            s.add(CostProfile(
                asset_id=asset.id,
                capex_inputs=a["capex_inputs"],
                opex_inputs=a["opex_inputs"],
                decline_inputs=a["decline_inputs"],
            ))
            inserted_assets += 1

        for sc in SAMPLE_SCENARIOS:
            s.add(Scenario(name=sc["name"], inputs=sc["inputs"]))
            inserted_scenarios += 1

    return {
        "status": "seeded",
        "assets": inserted_assets,
        "scenarios": inserted_scenarios,
        "admin_created": admin_created,
    }


if __name__ == "__main__":
    print(seed())
