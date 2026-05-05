"""FastAPI entrypoint — Oil CAPEX/OPEX Dashboard API with JWT auth."""

from __future__ import annotations

import logging
import math
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from jose import JWTError
from pydantic import BaseModel
from sqlalchemy import func, select

from .database import (
    ActivityLog, Asset, CostProfile, DecisionMatrixRun, Event,
    PriceDeck, Scenario, ScenarioResult, User, UserSession,
    db_url_redacted, ensure_scenario_schema, get_session,
    init_db, is_postgres,
)
from .modules.auth import (
    create_access_token, decode_access_token,
    hash_password, verify_password,
)
from .modules import cost_models, decision_matrix, economics, report, scenario, uncertainty
from .schemas import (
    ChangePasswordRequest, DecisionMatrixRequest, EventImpactRequest,
    LoginRequest, LoginResponse, AuthUserOut,
    MonteCarloRequest, ScenarioImportRequest, ScenarioInputs, TornadoRequest,
    UserCreate, UserOut, UserUpdate,
)
from .seed import seed as run_seed

logger = logging.getLogger("asset_pulse")

# =============================================================================
# App setup
# =============================================================================

app = FastAPI(
    title="Asset Pulse API",
    version="1.0.0",
    description="Oil CAPEX/OPEX forecasting and decision intelligence — with JWT auth.",
    # Disable docs in production via env (set APP_ENV=production)
    docs_url="/docs" if os.getenv("APP_ENV", "development") != "production" else None,
    redoc_url=None,
)

# CORS — MUST be added before the auth middleware so preflight passes through.
_allowed_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,  # Bearer tokens don't require credentials mode
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# =============================================================================
# Auth middleware — validates JWT on every request except public paths
# =============================================================================

_PUBLIC_PATHS = {"/api/health", "/api/auth/login"}


@app.middleware("http")
async def require_auth(request: Request, call_next: Any) -> Any:
    # Always pass preflight requests to CORS middleware
    if request.method == "OPTIONS":
        return await call_next(request)

    if request.url.path in _PUBLIC_PATHS:
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    token = auth_header[7:]
    try:
        payload = decode_access_token(token)
    except JWTError:
        return JSONResponse(status_code=401, content={"detail": "Token expired or invalid"})

    user_id = int(payload.get("sub", 0))
    try:
        with get_session() as s:
            user = s.get(User, user_id)
            if not user or not user.is_active:
                return JSONResponse(status_code=401, content={"detail": "User not found or inactive"})
    except Exception:
        return JSONResponse(status_code=500, content={"detail": "Auth check failed"})

    request.state.user = {
        "id": user_id,
        "email": payload.get("email", ""),
        "role": payload.get("role", "user"),
        "jti": payload.get("jti", ""),
    }
    return await call_next(request)


# =============================================================================
# FastAPI dependencies
# =============================================================================

def get_current_user(request: Request) -> dict:
    """Dependency: returns the user dict attached by the auth middleware."""
    if not hasattr(request.state, "user"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return request.state.user


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# =============================================================================
# Activity logging helper (Task 2)
# =============================================================================

def _log_activity(
    user: dict,
    action: str,
    *,
    resource_type: str | None = None,
    resource_id: int | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> None:
    """Write an audit row. Fire-and-forget: never raises."""
    try:
        with get_session() as s:
            s.add(ActivityLog(
                user_id=user["id"],
                user_email=user["email"],
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details or {},
                ip_address=ip_address,
            ))
    except Exception as exc:
        logger.warning("activity_log write failed: %s", exc)


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


# =============================================================================
# Startup
# =============================================================================

@app.on_event("startup")
def _startup() -> None:
    init_db()
    try:
        run_seed()
    except Exception:
        pass


# =============================================================================
# Health (public)
# =============================================================================

@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "database": "postgres" if is_postgres() else "sqlite-fallback",
        "database_url_redacted": db_url_redacted(),
    }


# =============================================================================
# Auth endpoints (POST /api/auth/login is public; others require token)
# =============================================================================

@app.post("/api/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request) -> LoginResponse:
    with get_session() as s:
        user = s.execute(
            select(User).where(User.email == payload.email.lower().strip())
        ).scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token, jti = create_access_token(user.id, user.email, user.role)

    # Record session + update last_login
    ip = _client_ip(request)
    ua = request.headers.get("User-Agent", "")[:500]
    from datetime import timedelta
    expire_minutes = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
    with get_session() as s:
        db_user = s.get(User, user.id)
        db_user.last_login = datetime.now(timezone.utc)
        s.add(UserSession(
            user_id=user.id,
            jti=jti,
            ip_address=ip,
            user_agent=ua,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=expire_minutes),
        ))
        s.add(ActivityLog(
            user_id=user.id,
            user_email=user.email,
            action="login",
            details={"ip": ip, "user_agent": ua[:120] if ua else None},
            ip_address=ip,
        ))

    return LoginResponse(
        access_token=token,
        user=AuthUserOut(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
        ),
    )


@app.post("/api/auth/logout")
def logout(request: Request, current_user: dict = Depends(get_current_user)) -> dict:
    jti = current_user.get("jti")
    if jti:
        try:
            with get_session() as s:
                sess = s.execute(
                    select(UserSession).where(UserSession.jti == jti)
                ).scalar_one_or_none()
                if sess:
                    sess.is_active = False
        except Exception:
            pass
    _log_activity(current_user, "logout", ip_address=_client_ip(request))
    return {"message": "Logged out"}


@app.get("/api/auth/me")
def me(current_user: dict = Depends(get_current_user)) -> dict:
    with get_session() as s:
        user = s.get(User, current_user["id"])
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "last_login": user.last_login.isoformat() if user.last_login else None,
        }


@app.post("/api/auth/change-password")
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    with get_session() as s:
        user = s.get(User, current_user["id"])
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not verify_password(payload.current_password, user.password_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        user.password_hash = hash_password(payload.new_password)
    _log_activity(current_user, "password_changed", ip_address=_client_ip(request))
    return {"message": "Password updated"}


# =============================================================================
# Admin endpoints
# =============================================================================

@app.get("/api/admin/users")
def admin_list_users(current_user: dict = Depends(require_admin)) -> list[dict]:
    with get_session() as s:
        users = s.execute(select(User).order_by(User.created_at)).scalars().all()
        return [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "last_login": u.last_login.isoformat() if u.last_login else None,
            }
            for u in users
        ]


@app.post("/api/admin/users", status_code=201)
def admin_create_user(
    payload: UserCreate,
    request: Request,
    current_user: dict = Depends(require_admin),
) -> dict:
    email = payload.email.lower().strip()
    with get_session() as s:
        existing = s.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")
        new_user = User(
            email=email,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
            role=payload.role,
            is_active=True,
            created_by=current_user["id"],
        )
        s.add(new_user)
        s.flush()
        user_id = new_user.id

    _log_activity(
        current_user, "user_created",
        resource_type="user", resource_id=user_id,
        details={"email": email, "role": payload.role},
        ip_address=_client_ip(request),
    )
    return {"id": user_id, "email": email, "role": payload.role, "message": "User created"}


@app.put("/api/admin/users/{user_id}")
def admin_update_user(
    user_id: int,
    payload: UserUpdate,
    request: Request,
    current_user: dict = Depends(require_admin),
) -> dict:
    if user_id == current_user["id"] and payload.is_active is False:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")

    changes: dict = {}
    with get_session() as s:
        user = s.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if payload.full_name is not None:
            user.full_name = payload.full_name
            changes["full_name"] = payload.full_name
        if payload.role is not None:
            user.role = payload.role
            changes["role"] = payload.role
        if payload.is_active is not None:
            user.is_active = payload.is_active
            changes["is_active"] = payload.is_active
        if payload.password:
            user.password_hash = hash_password(payload.password)
            changes["password"] = "reset"

    _log_activity(
        current_user, "user_updated",
        resource_type="user", resource_id=user_id,
        details=changes, ip_address=_client_ip(request),
    )
    return {"id": user_id, "message": "User updated", "changes": changes}


@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(
    user_id: int,
    request: Request,
    current_user: dict = Depends(require_admin),
) -> dict:
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    with get_session() as s:
        user = s.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        email = user.email
        s.delete(user)
    _log_activity(
        current_user, "user_deleted",
        resource_type="user", resource_id=user_id,
        details={"email": email}, ip_address=_client_ip(request),
    )
    return {"deleted": user_id}


@app.get("/api/admin/activity")
def admin_activity_log(
    limit: int = 200,
    current_user: dict = Depends(require_admin),
) -> list[dict]:
    with get_session() as s:
        rows = s.execute(
            select(ActivityLog)
            .order_by(ActivityLog.created_at.desc())
            .limit(min(limit, 1000))
        ).scalars().all()
        return [
            {
                "id": r.id,
                "user_email": r.user_email,
                "action": r.action,
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "details": r.details,
                "ip_address": r.ip_address,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]


@app.get("/api/admin/sessions")
def admin_sessions(current_user: dict = Depends(require_admin)) -> list[dict]:
    with get_session() as s:
        rows = s.execute(
            select(UserSession, User)
            .join(User, UserSession.user_id == User.id)
            .where(UserSession.is_active == True)
            .order_by(UserSession.created_at.desc())
            .limit(200)
        ).all()
        return [
            {
                "id": sess.id,
                "user_email": user.email,
                "ip_address": sess.ip_address,
                "created_at": sess.created_at.isoformat() if sess.created_at else None,
                "expires_at": sess.expires_at.isoformat() if sess.expires_at else None,
            }
            for sess, user in rows
        ]


# =============================================================================
# Domain routes — all protected by auth middleware
# =============================================================================

# --- Utility helpers (unchanged) ---

def _sanitize_floats(obj: Any) -> Any:
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, dict):
        return {k: _sanitize_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_floats(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_sanitize_floats(v) for v in obj)
    return obj


def _safe_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if (math.isnan(f) or math.isinf(f)) else f


def _resolve_asset_id(s: Any, alias: str | None) -> int | None:
    if not alias:
        return None
    alias = alias.strip()
    if not alias:
        return None
    if alias.isdigit():
        a = s.get(Asset, int(alias))
        return a.id if a else None
    a = s.execute(select(Asset).where(Asset.name == alias)).scalar_one_or_none()
    if a:
        return a.id
    a = s.execute(select(Asset).where(func.lower(Asset.name) == alias.lower())).scalar_one_or_none()
    return a.id if a else None


# --- Assets ---

@app.get("/api/assets")
def list_assets() -> list[dict]:
    out: list[dict] = []
    with get_session() as s:
        for a in s.execute(select(Asset)).scalars().all():
            cp = s.execute(
                select(CostProfile).where(CostProfile.asset_id == a.id)
            ).scalar_one_or_none()
            out.append({
                "id": a.id, "name": a.name,
                "asset_type": a.asset_type, "region": a.region,
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
    with get_session() as s:
        return [
            {
                "id": p.id, "name": p.name,
                "oil_price": p.oil_price, "gas_price": p.gas_price,
                "ngl_price": p.ngl_price, "differentials": p.differentials,
            }
            for p in s.execute(select(PriceDeck)).scalars().all()
        ]


# --- CAPEX calculators ---

@app.post("/api/capex/well")
def calc_well_capex(payload: dict) -> dict:
    return cost_models.well_capex(**payload)


@app.post("/api/capex/pipeline")
def calc_pipeline_capex(payload: dict) -> dict:
    return cost_models.pipeline_capex(**payload)


@app.post("/api/capex/facility")
def calc_facility_capex(payload: dict) -> dict:
    return cost_models.facility_capex(**payload)


# --- Scenario engine ---

def _persist_scenario_result(
    s: Any, *, name: str, payload: dict, result: dict,
    asset_alias: str | None, asset_id: int | None, source: str,
    compute_breakeven: bool = True,
) -> tuple[int, float | None]:
    sc = Scenario(
        name=name, asset_id=asset_id, asset_alias=asset_alias,
        source=source, inputs=_sanitize_floats(payload),
    )
    s.add(sc)
    s.flush()
    kpis = result["kpis"]
    el = kpis.get("economic_limit") or {}
    breakeven: float | None = None
    if compute_breakeven:
        try:
            breakeven = scenario.breakeven_oil_price(payload)
        except Exception as exc:
            logger.warning("breakeven_oil_price failed for %s: %s", name, exc)
    monthly_summary = _sanitize_floats({
        "months": result["monthly"]["months"],
        "free_cash_flow": result["monthly"]["free_cash_flow"],
        "net_revenue": result["monthly"]["net_revenue"],
        "opex": result["monthly"]["opex"],
        "oil_bbl": result["monthly"].get("oil_bbl", []),
        "water_bbl": result["monthly"].get("water_bbl", []),
    })
    s.add(ScenarioResult(
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
    ))
    return sc.id, breakeven


def _try_persist(
    *, name: str, payload: dict, result: dict,
    asset_alias: str | None, asset_id: int | None, source: str,
) -> tuple[int | None, float | None, str | None]:
    try:
        with get_session() as s:
            sid, be = _persist_scenario_result(
                s, name=name, payload=payload, result=result,
                asset_alias=asset_alias, asset_id=asset_id, source=source,
            )
            return sid, be, None
    except Exception as first_exc:
        logger.warning("scenario persist failed (retry after JIT migration): %s", first_exc)
        try:
            ensure_scenario_schema()
        except Exception as mig_exc:
            return None, None, f"persist failed: {first_exc}; migration: {mig_exc}"
        try:
            with get_session() as s:
                sid, be = _persist_scenario_result(
                    s, name=name, payload=payload, result=result,
                    asset_alias=asset_alias, asset_id=asset_id, source=source,
                )
                return sid, be, None
        except Exception as exc:
            return None, None, str(exc)


def _try_update(
    *, scenario_id: int, payload: dict, result: dict, name: str | None,
) -> tuple[int | None, float | None, str | None]:
    def _do(s: Any) -> tuple[int, float | None]:
        sc = s.get(Scenario, scenario_id)
        if sc is None:
            return 0, None
        sc.inputs = _sanitize_floats(payload)
        if name:
            sc.name = name
        alias = payload.get("asset_name")
        if alias:
            sc.asset_alias = alias
        s.execute(
            ScenarioResult.__table__.delete().where(
                ScenarioResult.scenario_id == scenario_id
            )
        )
        s.flush()
        kpis = result["kpis"]
        el = kpis.get("economic_limit") or {}
        try:
            breakeven = scenario.breakeven_oil_price(payload)
        except Exception:
            breakeven = None
        monthly_summary = _sanitize_floats({
            "months": result["monthly"]["months"],
            "free_cash_flow": result["monthly"]["free_cash_flow"],
            "net_revenue": result["monthly"]["net_revenue"],
            "opex": result["monthly"]["opex"],
        })
        s.add(ScenarioResult(
            scenario_id=scenario_id,
            npv=_safe_float(kpis.get("npv")),
            pv10=_safe_float(kpis.get("pv10")),
            payback_months=_safe_float(kpis.get("payback_months")),
            netback_per_boe=_safe_float(kpis.get("netback_per_boe")),
            economic_limit_boe_per_month=_safe_float(el.get("economic_limit_boe_per_month")),
            breakeven_oil_price=_safe_float(breakeven),
            total_boe=_safe_float(kpis.get("total_boe")),
            fiscal_regime=kpis.get("fiscal_regime"),
            monthly_summary=monthly_summary,
        ))
        return scenario_id, breakeven

    try:
        with get_session() as s:
            sid, be = _do(s)
            if sid == 0:
                return None, None, None
            return sid, be, None
    except Exception as first_exc:
        logger.warning("scenario update failed (retry): %s", first_exc)
        try:
            ensure_scenario_schema()
        except Exception as mig_exc:
            return None, None, f"update failed: {first_exc}; migration: {mig_exc}"
        try:
            with get_session() as s:
                sid, be = _do(s)
                if sid == 0:
                    return None, None, None
                return sid, be, None
        except Exception as exc:
            return None, None, str(exc)


@app.post("/api/scenario/run")
def run_scenario(
    request: Request,
    inputs: ScenarioInputs,
    persist: bool = True,
    name: str | None = None,
    scenario_id: int | None = None,
) -> dict:
    payload = inputs.model_dump()
    try:
        result = scenario.project_scenario(payload)
    except (ValueError, ZeroDivisionError, OverflowError, TypeError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=f"invalid scenario inputs: {exc}") from exc
    except Exception as exc:
        logger.exception("project_scenario crashed")
        raise HTTPException(status_code=400, detail=f"scenario calculation failed: {exc}") from exc

    if persist:
        if scenario_id is not None:
            sid, breakeven, persist_error = _try_update(
                scenario_id=scenario_id, payload=payload, result=result, name=name,
            )
            if sid is None:
                sid, breakeven, persist_error = _try_persist(
                    name=name or f"{result['asset_name']} - run",
                    payload=payload, result=result,
                    asset_alias=payload.get("asset_name"),
                    asset_id=None, source="api",
                )
        else:
            sid, breakeven, persist_error = _try_persist(
                name=name or f"{result['asset_name']} - run",
                payload=payload, result=result,
                asset_alias=payload.get("asset_name"),
                asset_id=None, source="api",
            )
        if sid is not None:
            result["scenario_id"] = sid
            result["breakeven_oil_price"] = breakeven
        if persist_error:
            result["persist_error"] = persist_error

    # Activity log (Task 2)
    if hasattr(request.state, "user"):
        _log_activity(
            request.state.user, "scenario_run",
            resource_type="scenario",
            resource_id=result.get("scenario_id"),
            details={"asset_name": payload.get("asset_name"), "persist": persist},
            ip_address=_client_ip(request),
        )

    return _sanitize_floats(result)


@app.post("/api/scenarios/{scenario_id}/run")
def run_saved_scenario(
    scenario_id: int,
    request: Request,
    inputs: ScenarioInputs | None = None,
) -> dict:
    if inputs is None:
        with get_session() as s:
            sc = s.get(Scenario, scenario_id)
            if sc is None:
                raise HTTPException(status_code=404, detail="scenario not found")
            stored = sc.inputs or {}
        try:
            inputs = ScenarioInputs(**stored)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"stored inputs invalid: {exc}") from exc
    return run_scenario(
        request=request, inputs=inputs, persist=True, name=None, scenario_id=scenario_id,
    )


@app.post("/api/scenarios/import")
def import_scenarios(req: ScenarioImportRequest, request: Request) -> dict:
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
                    sid, breakeven = _persist_scenario_result(
                        s, name=name, payload=payload, result=result,
                        asset_alias=alias, asset_id=asset_id,
                        source=req.source or "csv_import",
                    )
                    saved.append({
                        "scenario_id": sid, "name": name,
                        "asset_alias": alias, "asset_id": asset_id,
                        "npv": result["kpis"].get("npv"),
                        "breakeven_oil_price": breakeven, "ran": True,
                    })
                else:
                    sc = Scenario(
                        name=name, asset_id=asset_id, asset_alias=alias,
                        source=req.source or "csv_import", inputs=payload,
                    )
                    s.add(sc)
                    s.flush()
                    saved.append({
                        "scenario_id": sc.id, "name": name,
                        "asset_alias": alias, "asset_id": asset_id, "ran": False,
                    })
            except Exception as exc:
                errors.append({"row": idx + 1, "error": str(exc)})

    if hasattr(request.state, "user"):
        _log_activity(
            request.state.user, "csv_import",
            resource_type="scenario",
            details={"rows_saved": len(saved), "errors": len(errors)},
            ip_address=_client_ip(request),
        )
    return {"saved": saved, "errors": errors}


@app.get("/api/scenarios")
def list_scenarios(limit: int = 100) -> list[dict]:
    out: list[dict] = []
    with get_session() as s:
        for sc in s.execute(
            select(Scenario).order_by(Scenario.id.desc()).limit(limit)
        ).scalars().all():
            res = s.execute(
                select(ScenarioResult).where(ScenarioResult.scenario_id == sc.id)
            ).scalar_one_or_none()
            out.append({
                "id": sc.id, "name": sc.name,
                "asset_id": sc.asset_id, "asset_alias": sc.asset_alias,
                "source": sc.source,
                "created_at": sc.created_at.isoformat() if sc.created_at else None,
                "inputs": sc.inputs,
                "result": {
                    "npv": res.npv, "pv10": res.pv10,
                    "payback_months": res.payback_months,
                    "netback_per_boe": res.netback_per_boe,
                    "economic_limit_boe_per_month": res.economic_limit_boe_per_month,
                    "breakeven_oil_price": res.breakeven_oil_price,
                    "total_boe": res.total_boe,
                    "fiscal_regime": res.fiscal_regime,
                    "monthly_summary": res.monthly_summary,
                } if res else None,
            })
    return out


class ScenarioReportRequest(BaseModel):
    scenario_ids: list[int] | None = None


def _scenarios_for_report(scenario_ids: list[int] | None) -> list[dict]:
    out: list[dict] = []
    with get_session() as s:
        q = select(Scenario)
        if scenario_ids:
            q = q.where(Scenario.id.in_(scenario_ids))
        q = q.order_by(Scenario.id.desc()).limit(200)
        for sc in s.execute(q).scalars().all():
            res = s.execute(
                select(ScenarioResult).where(ScenarioResult.scenario_id == sc.id)
            ).scalar_one_or_none()
            out.append({
                "id": sc.id, "name": sc.name,
                "asset_id": sc.asset_id, "asset_alias": sc.asset_alias,
                "source": sc.source,
                "created_at": sc.created_at.isoformat() if sc.created_at else None,
                "inputs": sc.inputs,
                "result": {
                    "npv": res.npv, "pv10": res.pv10,
                    "payback_months": res.payback_months,
                    "netback_per_boe": res.netback_per_boe,
                    "economic_limit_boe_per_month": res.economic_limit_boe_per_month,
                    "breakeven_oil_price": res.breakeven_oil_price,
                    "total_boe": res.total_boe,
                    "fiscal_regime": res.fiscal_regime,
                } if res else None,
            })
    if scenario_ids:
        order = {sid: i for i, sid in enumerate(scenario_ids)}
        out.sort(key=lambda x: order.get(x["id"], 1_000_000))
    return out


@app.post("/api/scenarios/report.pdf")
def scenarios_report_pdf(
    request: Request,
    req: ScenarioReportRequest | None = None,
) -> Response:
    ids = req.scenario_ids if req and req.scenario_ids else None
    scenarios = _scenarios_for_report(ids)
    if not scenarios:
        raise HTTPException(status_code=404, detail="no scenarios available for report")
    pdf_bytes = report.build_scenario_comparison_pdf(scenarios)

    if hasattr(request.state, "user"):
        _log_activity(
            request.state.user, "report_generate",
            resource_type="scenario",
            details={"scenario_ids": ids, "count": len(scenarios)},
            ip_address=_client_ip(request),
        )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="asset-pulse-report.pdf"'},
    )


@app.delete("/api/scenarios/{scenario_id}")
def delete_scenario(scenario_id: int, request: Request) -> dict:
    with get_session() as s:
        sc = s.get(Scenario, scenario_id)
        if sc is None:
            raise HTTPException(status_code=404, detail="scenario not found")
        s.execute(
            ScenarioResult.__table__.delete().where(
                ScenarioResult.scenario_id == scenario_id
            )
        )
        s.delete(sc)

    if hasattr(request.state, "user"):
        _log_activity(
            request.state.user, "scenario_delete",
            resource_type="scenario", resource_id=scenario_id,
            ip_address=_client_ip(request),
        )
    return {"deleted": scenario_id}


# --- Sensitivity ---

@app.post("/api/uncertainty/tornado")
def tornado(req: TornadoRequest, request: Request) -> dict:
    base_inputs = req.base_inputs.model_dump()
    rows = uncertainty.tornado_sensitivity(
        base_inputs=base_inputs,
        npv_fn=scenario.npv_only,
        variables=[v.model_dump() for v in req.variables],
    )
    if hasattr(request.state, "user"):
        _log_activity(request.state.user, "tornado_run", ip_address=_client_ip(request))
    return {"base_npv": scenario.npv_only(base_inputs), "rows": rows}


@app.post("/api/uncertainty/montecarlo")
def montecarlo(req: MonteCarloRequest, request: Request) -> dict:
    result = uncertainty.monte_carlo_npv(
        base_inputs=req.base_inputs.model_dump(),
        distributions=req.distributions,
        npv_fn=scenario.npv_only,
        iterations=req.iterations,
        seed=req.seed,
    )
    if hasattr(request.state, "user"):
        _log_activity(request.state.user, "montecarlo_run", ip_address=_client_ip(request))
    return result


# --- Events ---

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


# --- Decision matrix ---

@app.post("/api/decision-matrix/score")
def score_dm(
    req: DecisionMatrixRequest,
    request: Request,
    persist: bool = False,
    name: str | None = None,
) -> dict:
    assets = [a.model_dump() for a in req.assets]
    results = decision_matrix.score_assets(assets, req.criteria)
    if persist:
        with get_session() as s:
            s.add(DecisionMatrixRun(
                name=name or "matrix-run",
                criteria=req.criteria or decision_matrix.DEFAULT_CRITERIA,
                inputs=assets,
                results=results,
            ))
    if hasattr(request.state, "user"):
        _log_activity(request.state.user, "decision_matrix_run", ip_address=_client_ip(request))
    return {
        "criteria": req.criteria or decision_matrix.DEFAULT_CRITERIA,
        "results": results,
    }


@app.get("/api/decision-matrix/criteria")
def default_criteria() -> dict:
    return {"criteria": decision_matrix.DEFAULT_CRITERIA}


# --- Seed (admin only) ---

@app.post("/api/seed")
def seed_now(current_user: dict = Depends(require_admin)) -> dict:
    return run_seed()
