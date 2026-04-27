"""FastAPI entrypoint."""

from __future__ import annotations

import logging
import math
import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select

from .database import (
    Asset, CostProfile, DecisionMatrixRun, Event, PriceDeck, Scenario,
    ScenarioResult, db_url_redacted, ensure_scenario_schema, get_session,
    init_db, is_postgres,
)

logger = logging.getLogger("asset_pulse")


def _sanitize_floats(obj: Any) -> Any:
    """Recursively replace NaN/Inf floats with None so the result is
    JSON-serialisable and safe for JSONB columns.

    Without this, an inf/NaN slipping through (e.g. from extreme inputs or
    a divide producing inf) bubbles up as a generic 500 from FastAPI's JSON
    encoder.
    """
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _sanitize_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_floats(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_sanitize_floats(v) for v in obj)
    return obj
from .modules import cost_models, decision_matrix, economics, scenario, uncertainty
from .schemas import (
    DecisionMatrixRequest, EventImpactRequest, MonteCarloRequest,
    ScenarioImportRequest, ScenarioInputs, TornadoRequest,
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

def _persist_scenario_result(
    s,
    *,
    name: str,
    payload: dict,
    result: dict,
    asset_alias: str | None,
    asset_id: int | None,
    source: str,
    compute_breakeven: bool = True,
) -> tuple[int, float | None]:
    """Insert Scenario + ScenarioResult and return (scenario_id, breakeven)."""
    sc = Scenario(
        name=name,
        asset_id=asset_id,
        asset_alias=asset_alias,
        source=source,
        inputs=_sanitize_floats(payload),
    )
    s.add(sc)
    s.flush()
    kpis = result["kpis"]
    el = kpis.get("economic_limit") or {}
    breakeven: float | None = None
    if compute_breakeven:
        try:
            breakeven = scenario.breakeven_oil_price(payload)
        except Exception as exc:  # noqa: BLE001 — never block persistence on this
            logger.warning("breakeven_oil_price failed for %s: %s", name, exc)
            breakeven = None
    monthly_summary = _sanitize_floats({
        "months": result["monthly"]["months"],
        "free_cash_flow": result["monthly"]["free_cash_flow"],
        "net_revenue": result["monthly"]["net_revenue"],
        "opex": result["monthly"]["opex"],
    })
    sr = ScenarioResult(
        scenario_id=sc.id,
        npv=_safe_float(kpis.get("npv")),
        pv10=_safe_float(kpis.get("pv10")),
        payback_months=_safe_float(kpis.get("payback_months")),
        netback_per_boe=_safe_float(kpis.get("netback_per_boe")),
        economic_limit_boe_per_month=_safe_float(el.get("economic_limit_boe_per_month")),
        breakeven_oil_price=_safe_float(breakeven),
        total_boe=_safe_float(kpis.get("total_boe")),
        fiscal_regime=kpis.get("fiscal_regime"),
        monthly_summary=monthly_summary,
    )
    s.add(sr)
    return sc.id, breakeven


def _safe_float(v: Any) -> float | None:
    """Coerce to float, mapping NaN/Inf/non-numeric to None."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def _resolve_asset_id(s, alias: str | None) -> int | None:
    """Best-effort: match a CSV asset_id_or_name to an existing assets.id.

    Accepts numeric ids, exact names, or case-insensitive name matches. Returns
    None when nothing matches — the alias is still stored on Scenario.asset_alias.
    """
    if not alias:
        return None
    alias = alias.strip()
    if not alias:
        return None
    if alias.isdigit():
        a = s.get(Asset, int(alias))
        if a is not None:
            return a.id
    a = s.execute(select(Asset).where(Asset.name == alias)).scalar_one_or_none()
    if a is not None:
        return a.id
    a = s.execute(select(Asset).where(func.lower(Asset.name) == alias.lower())).scalar_one_or_none()
    return a.id if a is not None else None


@app.post("/api/scenario/run")
def run_scenario(inputs: ScenarioInputs, persist: bool = True, name: str | None = None) -> dict:
    """Run a scenario. By default, persists to DB so it is visible in the
    Scenario Compare tab. Pass persist=false to compute without saving."""
    payload = inputs.model_dump()
    try:
        result = scenario.project_scenario(payload)
    except (ValueError, ZeroDivisionError, OverflowError, TypeError, KeyError) as exc:
        # Bad/extreme inputs — surface a 400 instead of a generic 500.
        raise HTTPException(status_code=400, detail=f"invalid scenario inputs: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 — last-resort guardrail
        logger.exception("project_scenario crashed unexpectedly")
        raise HTTPException(status_code=400, detail=f"scenario calculation failed: {exc}") from exc

    if persist:
        scenario_id, breakeven, persist_error = _try_persist(
            name=name or f"{result['asset_name']} - run",
            payload=payload,
            result=result,
            asset_alias=payload.get("asset_name"),
            asset_id=None,
            source="api",
        )
        if scenario_id is not None:
            result["scenario_id"] = scenario_id
            result["breakeven_oil_price"] = breakeven
        if persist_error:
            result["persist_error"] = persist_error
    return _sanitize_floats(result)


def _try_persist(
    *, name: str, payload: dict, result: dict,
    asset_alias: str | None, asset_id: int | None, source: str,
) -> tuple[int | None, float | None, str | None]:
    """Persist with a JIT-migration retry.

    First attempt uses the current schema. If it fails with what looks like a
    schema-drift error (missing column / missing table), we run
    ``ensure_scenario_schema`` and retry exactly once. Any further failure is
    surfaced as a ``persist_error`` field on the response so the user still
    gets their KPIs.
    """
    try:
        with get_session() as s:
            sid, be = _persist_scenario_result(
                s, name=name, payload=payload, result=result,
                asset_alias=asset_alias, asset_id=asset_id, source=source,
            )
            return sid, be, None
    except Exception as first_exc:  # noqa: BLE001
        logger.warning("scenario persist failed (will retry after JIT migration): %s", first_exc)
        try:
            ensure_scenario_schema()
        except Exception as mig_exc:  # noqa: BLE001
            logger.exception("JIT scenario schema migration failed")
            return None, None, f"persist failed: {first_exc}; migration failed: {mig_exc}"
        try:
            with get_session() as s:
                sid, be = _persist_scenario_result(
                    s, name=name, payload=payload, result=result,
                    asset_alias=asset_alias, asset_id=asset_id, source=source,
                )
                return sid, be, None
        except Exception as exc:  # noqa: BLE001
            logger.exception("scenario persist failed after JIT migration")
            return None, None, str(exc)


@app.post("/api/scenarios/import")
def import_scenarios(req: ScenarioImportRequest) -> dict:
    """Bulk-save scenarios staged from a CSV. When run=True (default), each
    row is also evaluated and its KPIs (incl. breakeven) are persisted."""
    saved: list[dict] = []
    errors: list[dict] = []
    with get_session() as s:
        for idx, row in enumerate(req.rows):
            try:
                payload = row.inputs.model_dump()
                alias = (row.asset_id_or_name or "").strip() or payload.get("asset_name")
                name = (row.scenario_name or "").strip() or f"{payload.get('asset_name', 'asset')} - csv{idx + 1}"
                asset_id = _resolve_asset_id(s, alias)
                if req.run:
                    result = scenario.project_scenario(payload)
                    scenario_id, breakeven = _persist_scenario_result(
                        s,
                        name=name,
                        payload=payload,
                        result=result,
                        asset_alias=alias,
                        asset_id=asset_id,
                        source=req.source or "csv_import",
                    )
                    saved.append({
                        "scenario_id": scenario_id,
                        "name": name,
                        "asset_alias": alias,
                        "asset_id": asset_id,
                        "npv": result["kpis"].get("npv"),
                        "breakeven_oil_price": breakeven,
                        "ran": True,
                    })
                else:
                    sc = Scenario(
                        name=name, asset_id=asset_id, asset_alias=alias,
                        source=req.source or "csv_import", inputs=payload,
                    )
                    s.add(sc)
                    s.flush()
                    saved.append({
                        "scenario_id": sc.id, "name": name, "asset_alias": alias,
                        "asset_id": asset_id, "ran": False,
                    })
            except Exception as exc:  # noqa: BLE001 — propagate as row-level error
                errors.append({"row": idx + 1, "error": str(exc)})
    return {"saved": saved, "errors": errors}


@app.get("/api/scenarios")
def list_scenarios(limit: int = 100) -> list[dict]:
    out: list[dict] = []
    with get_session() as s:
        for sc in s.execute(select(Scenario).order_by(Scenario.id.desc()).limit(limit)).scalars().all():
            res = s.execute(
                select(ScenarioResult).where(ScenarioResult.scenario_id == sc.id)
            ).scalar_one_or_none()
            out.append({
                "id": sc.id,
                "name": sc.name,
                "asset_id": sc.asset_id,
                "asset_alias": sc.asset_alias,
                "source": sc.source,
                "created_at": sc.created_at.isoformat() if sc.created_at else None,
                "inputs": sc.inputs,
                "result": {
                    "npv": res.npv,
                    "pv10": res.pv10,
                    "payback_months": res.payback_months,
                    "netback_per_boe": res.netback_per_boe,
                    "economic_limit_boe_per_month": res.economic_limit_boe_per_month,
                    "breakeven_oil_price": res.breakeven_oil_price,
                    "total_boe": res.total_boe,
                    "fiscal_regime": res.fiscal_regime,
                } if res else None,
            })
    return out


@app.delete("/api/scenarios/{scenario_id}")
def delete_scenario(scenario_id: int) -> dict:
    with get_session() as s:
        sc = s.get(Scenario, scenario_id)
        if sc is None:
            raise HTTPException(status_code=404, detail="scenario not found")
        s.execute(ScenarioResult.__table__.delete().where(ScenarioResult.scenario_id == scenario_id))
        s.delete(sc)
    return {"deleted": scenario_id}


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
