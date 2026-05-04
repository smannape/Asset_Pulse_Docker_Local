"""Pydantic request/response schemas — domain + auth."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# =============================================================================
# Existing domain schemas (unchanged)
# =============================================================================

class ScenarioInputs(BaseModel):
    asset_name: str = "asset"
    months_horizon: int = 120
    initial_oil_bopd: float = 0.0
    initial_gas_mcfd: float = 0.0
    initial_ngl_bpd: float = 0.0
    annual_decline: float = 0.20
    decline_model: str = Field(default="exponential", pattern="^(exponential|hyperbolic|harmonic)$")
    b_factor: float = Field(default=0.7, ge=0.0, le=2.0)
    water_cut_initial: float = 0.30
    water_cut_final: float = 0.80
    oil_price: float = 70.0
    gas_price: float = 3.0
    ngl_price: float = 25.0
    royalty_pct: float = 0.1875
    production_tax_pct: float = 0.045
    transport_per_boe: float = 1.50
    processing_per_boe: float = 0.50
    fixed_opex_per_month: float = 0.0
    oil_var_per_bbl: float = 0.0
    gas_var_per_mcf: float = 0.0
    water_var_per_bbl: float = 0.0
    development_capex: float = 0.0
    sustaining_capex_per_month: float = 0.0
    abandonment_cost: float = 0.0
    discount_rate_annual: float = 0.10
    capex_multiplier: float = 1.0
    opex_multiplier: float = 1.0
    apply_economic_limit: bool = True

    fiscal_regime: str = Field(
        default="us_royalty_tax",
        pattern="^(us_royalty_tax|noc_internal|psc_cost_recovery|technical_service_contract|concession_tax_royalty)$",
    )
    noc_government_share_pct: float = 0.0
    noc_corp_tax_pct: float = 0.0
    psc_royalty_pct: float = 0.10
    psc_cost_oil_limit_pct: float = 0.60
    psc_contractor_profit_share_pct: float = 0.40
    psc_contractor_tax_pct: float = 0.30
    psc_capex_uplift_pct: float = 0.0
    tsc_payment_cap_pct: float = 0.50
    tsc_remuneration_per_boe: float = 1.50
    tsc_contractor_tax_pct: float = 0.35
    concession_royalty_pct: float = 0.20
    concession_income_tax_pct: float = 0.50
    concession_royalty_progressive: bool = False
    concession_royalty_tiers: Optional[list[dict[str, Any]]] = None


class TornadoVariable(BaseModel):
    name: str
    low_pct: float = -0.30
    high_pct: float = 0.30


class TornadoRequest(BaseModel):
    base_inputs: ScenarioInputs
    variables: list[TornadoVariable] = Field(default_factory=lambda: [
        TornadoVariable(name="oil_price"),
        TornadoVariable(name="initial_oil_bopd"),
        TornadoVariable(name="capex_multiplier", low_pct=-0.10, high_pct=0.30),
        TornadoVariable(name="opex_multiplier", low_pct=-0.10, high_pct=0.30),
        TornadoVariable(name="annual_decline", low_pct=-0.20, high_pct=0.20),
        TornadoVariable(name="water_cut_final", low_pct=-0.10, high_pct=0.10),
        TornadoVariable(name="discount_rate_annual", low_pct=-0.20, high_pct=0.20),
    ])


class MonteCarloRequest(BaseModel):
    base_inputs: ScenarioInputs
    distributions: dict[str, dict[str, Any]] = Field(default_factory=lambda: {
        "oil_price": {"type": "triangular", "low": 55.0, "mode": 72.0, "high": 95.0},
        "capex_multiplier": {"type": "triangular", "low": 0.95, "mode": 1.05, "high": 1.30},
        "opex_multiplier": {"type": "triangular", "low": 0.95, "mode": 1.05, "high": 1.25},
    })
    iterations: int = 500
    seed: int = 42


class EventInput(BaseModel):
    type: str
    magnitude: float = 0.0
    duration_months: int = 0
    notes: Optional[str] = None


class EventImpactRequest(BaseModel):
    base_npv: float
    base_monthly_cf: float
    events: list[EventInput]


class DecisionMatrixAsset(BaseModel):
    asset_id: Optional[str] = None
    name: str
    monthly_margin: float
    npv_keep_online: float
    avoidable_opex: float
    restart_payback_months: float
    restart_risk: float = Field(ge=0.0, le=1.0)
    hbp_risk: float = Field(ge=0.0, le=1.0)
    water_burden: float = Field(ge=0.0, le=1.0)
    strategic_value: float = Field(ge=0.0, le=1.0)


class DecisionMatrixRequest(BaseModel):
    assets: list[DecisionMatrixAsset]
    criteria: Optional[list[dict]] = None


class ScenarioImportRow(BaseModel):
    scenario_name: Optional[str] = None
    asset_id_or_name: Optional[str] = None
    notes: Optional[str] = None
    inputs: ScenarioInputs


class ScenarioImportRequest(BaseModel):
    rows: list[ScenarioImportRow]
    run: bool = True
    source: str = "csv_import"


# =============================================================================
# Auth schemas (Task 1)
# =============================================================================

class LoginRequest(BaseModel):
    email: str
    password: str


class AuthUserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserOut


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def strong_enough(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserCreate(BaseModel):
    email: str
    full_name: Optional[str] = None
    password: str
    role: str = Field(default="user", pattern="^(admin|user)$")

    @field_validator("password")
    @classmethod
    def strong_enough(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = Field(default=None, pattern="^(admin|user)$")
    is_active: Optional[bool] = None
    password: Optional[str] = None

    @field_validator("password")
    @classmethod
    def strong_enough(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: Optional[str]
    last_login: Optional[str]


class ActivityLogOut(BaseModel):
    id: int
    user_email: Optional[str]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[int]
    details: Optional[dict]
    ip_address: Optional[str]
    created_at: Optional[str]
