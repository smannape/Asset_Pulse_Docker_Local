"""FastAPI entrypoint."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .database import (
    Asset, CostProfile, DecisionMatrixRun, Event, PriceDeck, Scenario,
    ScenarioResult, db_url_redacted, get_session, init_db, is_postgres,
)
from .modules import cost_models, decision_matrix, economics, scenario, uncertainty
from .schemas import (
    DecisionMatrixRequest, EventImpactRequest, MonteCarloRequest,
    ScenarioInputs, TornadoRequest,
)
from .seed import seed as run_seed


app = FastAPI(
    title="Oil CAPEX/OPEX Dashboard API",
    version="0.1.0",
    description="Python FastAPI backend for the Oil Well CAPEX/OPEX terminal dashboard.",
)

# CORS — permissive for local dev; tighten via env in production
allowed = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()
    # Auto-seed on first boot if DB is empty
    try:
        run_seed()
    except Exception:
        pass


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "database": "postgres" if is_postgres() else "sqlite-fallback",
        "database_url_redacted": db_url_redacted(),
    }


# -----------------------------------------------------------------------------
# Assets
# -----------------------------------------------------------------------------

@app.get("/api/assets")
def list_assets() -> list[dict]:
    out: list[dict] = []
    with get_session() as s:
        for a in s.execute(select(Asset)).scalars().all():
            cp = s.execute(select(CostProfile).where(CostProfile.asset_id == a.id)).scalar_one_or_none()
            out.append({
                "id": a.id,
                "name": a.name,
                "asset_type": a.asset_type,
                "region": a.region,
                "metadata": a.metadata_json,
                "cost_profile": {
                    "capex_inputs": cp.capex_inputs if cp else None,
                    "opex_inputs": cp.opex_inputs if cp else None,
                    "decline_inputs": cp.decline_inputs if cp else None,
                } if cp else None,
            })
    return out


@app.get("/api/price-decks")
def list_price_decks() -> list[dict]:
    out: list[dict] = []
    with get_session() as s:
        for p in s.execute(select(PriceDeck)).scalars().all():
            out.append({
                "id": p.id, "name": p.name,
                "oil_price": p.oil_price, "gas_price": p.gas_price, "ngl_price": p.ngl_price,
                "differentials": p.differentials,
            })
    return out


# -----------------------------------------------------------------------------
# CAPEX calculators
# -----------------------------------------------------------------------------

@app.post("/api/capex/well")
def calc_well_capex(payload: dict) -> dict:
    return cost_models.well_capex(**payload)


@app.post("/api/capex/pipeline")
def calc_pipeline_capex(payload: dict) -> dict:
    return cost_models.pipeline_capex(**payload)


@app.post("/api/capex/facility")
def calc_facility_capex(payload: dict) -> dict:
    return cost_models.facility_capex(**payload)


# -----------------------------------------------------------------------------
# Scenario engine
# -----------------------------------------------------------------------------

@app.post("/api/scenario/run")
def run_scenario(inputs: ScenarioInputs, persist: bool = False, name: str | None = None) -> dict:
    payload = inputs.model_dump()
    result = scenario.project_scenario(payload)

    if persist:
        with get_session() as s:
            sc = Scenario(name=name or f"{result['asset_name']} - run", inputs=payload)
            s.add(sc)
            s.flush()
            kpis = result["kpis"]
            el = kpis.get("economic_limit") or {}
            sr = ScenarioResult(
                scenario_id=sc.id,
                npv=kpis.get("npv"),
                pv10=kpis.get("pv10"),
                payback_months=kpis.get("payback_months"),
                netback_per_boe=kpis.get("netback_per_boe"),
                economic_limit_boe_per_month=el.get("economic_limit_boe_per_month"),
                monthly_summary={
                    "months": result["monthly"]["months"],
                    "free_cash_flow": result["monthly"]["free_cash_flow"],
                    "net_revenue": result["monthly"]["net_revenue"],
                    "opex": result["monthly"]["opex"],
                },
            )
            s.add(sr)
            result["scenario_id"] = sc.id
    return result


@app.get("/api/scenarios")
def list_scenarios() -> list[dict]:
    out: list[dict] = []
    with get_session() as s:
        for sc in s.execute(select(Scenario).order_by(Scenario.id.desc()).limit(50)).scalars().all():
            res = s.execute(
                select(ScenarioResult).where(ScenarioResult.scenario_id == sc.id)
            ).scalar_one_or_none()
            out.append({
                "id": sc.id,
                "name": sc.name,
                "asset_id": sc.asset_id,
                "inputs": sc.inputs,
                "result": {
                    "npv": res.npv if res else None,
                    "pv10": res.pv10 if res else None,
                    "payback_months": res.payback_months if res else None,
                    "netback_per_boe": res.netback_per_boe if res else None,
                    "economic_limit_boe_per_month": res.economic_limit_boe_per_month if res else None,
                } if res else None,
            })
    return out


# -----------------------------------------------------------------------------
# Sensitivity / tornado
# -----------------------------------------------------------------------------

@app.post("/api/uncertainty/tornado")
def tornado(req: TornadoRequest) -> dict:
    base_inputs = req.base_inputs.model_dump()
    variables = [v.model_dump() for v in req.variables]
    rows = uncertainty.tornado_sensitivity(
        base_inputs=base_inputs,
        npv_fn=scenario.npv_only,
        variables=variables,
    )
    return {"base_npv": scenario.npv_only(base_inputs), "rows": rows}


@app.post("/api/uncertainty/montecarlo")
def montecarlo(req: MonteCarloRequest) -> dict:
    return uncertainty.monte_carlo_npv(
        base_inputs=req.base_inputs.model_dump(),
        distributions=req.distributions,
        npv_fn=scenario.npv_only,
        iterations=req.iterations,
        seed=req.seed,
    )


# -----------------------------------------------------------------------------
# Events impact
# -----------------------------------------------------------------------------

@app.post("/api/events/impact")
def events_impact(req: EventImpactRequest) -> dict:
    impacts = []
    running_npv = req.base_npv
    for ev in req.events:
        out = decision_matrix.event_impact(
            base_npv=running_npv,
            base_monthly_cf=req.base_monthly_cf,
            event=ev.model_dump(),
        )
        running_npv = out["adjusted_npv"]
        impacts.append(out)
    return {"final_npv": running_npv, "impacts": impacts}


# -----------------------------------------------------------------------------
# Decision matrix
# -----------------------------------------------------------------------------

@app.post("/api/decision-matrix/score")
def score_dm(req: DecisionMatrixRequest, persist: bool = False, name: str | None = None) -> dict:
    assets = [a.model_dump() for a in req.assets]
    results = decision_matrix.score_assets(assets, req.criteria)
    if persist:
        with get_session() as s:
            run = DecisionMatrixRun(
                name=name or "matrix-run",
                criteria=req.criteria or decision_matrix.DEFAULT_CRITERIA,
                inputs=assets,
                results=results,
            )
            s.add(run)
    return {
        "criteria": req.criteria or decision_matrix.DEFAULT_CRITERIA,
        "results": results,
    }


@app.get("/api/decision-matrix/criteria")
def default_criteria() -> dict:
    return {"criteria": decision_matrix.DEFAULT_CRITERIA}


# -----------------------------------------------------------------------------
# Seed (manual)
# -----------------------------------------------------------------------------

@app.post("/api/seed")
def seed_now() -> dict:
    return run_seed()
