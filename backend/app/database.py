"""
Database layer.

Production: Postgres / Neon via SQLAlchemy. Set DATABASE_URL env var with
postgresql://user:pass@host/db?sslmode=require

Local fallback: when DATABASE_URL is absent, uses a file-backed SQLite database
so QA can run without credentials. JSONB columns degrade to JSON on SQLite.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer,
    MetaData, String, Text, create_engine, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.types import JSON


def _resolve_database_url() -> tuple[str, bool]:
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        return url, True
    fallback_path = os.getenv("LOCAL_SQLITE_PATH", "/tmp/capex_opex_demo.db")
    return f"sqlite:///{fallback_path}", False


DATABASE_URL, IS_POSTGRES = _resolve_database_url()


def _json_column():
    return JSONB if IS_POSTGRES else JSON


engine: Engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
Base = declarative_base()


# =============================================================================
# Existing domain models (unchanged)
# =============================================================================

class Asset(Base):
    __tablename__ = "assets"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    asset_type = Column(String(40), nullable=False)
    region = Column(String(80))
    metadata_json = Column(_json_column())
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CostProfile(Base):
    __tablename__ = "asset_cost_profiles"
    id = Column(Integer, primary_key=True)
    asset_id = Column(Integer, nullable=False)
    capex_inputs = Column(_json_column())
    opex_inputs = Column(_json_column())
    decline_inputs = Column(_json_column())


class PriceDeck(Base):
    __tablename__ = "price_decks"
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    oil_price = Column(Float)
    gas_price = Column(Float)
    ngl_price = Column(Float)
    differentials = Column(_json_column())


class Scenario(Base):
    __tablename__ = "scenarios"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    asset_id = Column(Integer)
    asset_alias = Column(String(160))
    source = Column(String(40))
    inputs = Column(_json_column())
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ScenarioResult(Base):
    __tablename__ = "scenario_results"
    id = Column(Integer, primary_key=True)
    scenario_id = Column(Integer, nullable=False)
    npv = Column(Float)
    pv10 = Column(Float)
    payback_months = Column(Float)
    netback_per_boe = Column(Float)
    economic_limit_boe_per_month = Column(Float)
    breakeven_oil_price = Column(Float)
    total_boe = Column(Float)
    fiscal_regime = Column(String(40))
    monthly_summary = Column(_json_column())
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    asset_id = Column(Integer)
    event_type = Column(String(40), nullable=False)
    magnitude = Column(Float)
    duration_months = Column(Integer)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DecisionMatrixRun(Base):
    __tablename__ = "decision_matrix_runs"
    id = Column(Integer, primary_key=True)
    name = Column(String(120))
    criteria = Column(_json_column())
    inputs = Column(_json_column())
    results = Column(_json_column())
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# =============================================================================
# Auth models (Task 1 & 2)
# =============================================================================

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    full_name = Column(String(120))
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="user")   # "admin" | "user"
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True))
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))


class UserSession(Base):
    """One row per successful login. jti mirrors the JWT claim for future revocation."""
    __tablename__ = "user_sessions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    jti = Column(String(100), unique=True, index=True)
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, nullable=False, default=True)


class ActivityLog(Base):
    """Immutable audit trail. user_email is denormalised so it survives user deletion."""
    __tablename__ = "activity_log"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True)
    user_email = Column(String(255))
    action = Column(String(80), nullable=False)
    resource_type = Column(String(40))
    resource_id = Column(Integer)
    details = Column(_json_column())
    ip_address = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# =============================================================================
# DB init + migrations
# =============================================================================

def init_db() -> None:
    Base.metadata.create_all(engine)
    _migrate_columns()


def ensure_scenario_schema() -> None:
    Base.metadata.create_all(engine)
    _migrate_columns()


def _migrate_columns() -> None:
    """Idempotent column adds for schema upgrades on running containers."""
    additions: list[tuple[str, str, str]] = [
        ("scenarios", "asset_alias", "VARCHAR(160)"),
        ("scenarios", "source", "VARCHAR(40)"),
        ("scenario_results", "breakeven_oil_price", "DOUBLE PRECISION"),
        ("scenario_results", "total_boe", "DOUBLE PRECISION"),
        ("scenario_results", "fiscal_regime", "VARCHAR(40)"),
    ]
    is_sqlite = DATABASE_URL.startswith("sqlite")
    for table, col, coltype in additions:
        try:
            with engine.begin() as conn:
                conn.exec_driver_sql(
                    f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {coltype}"
                )
            continue
        except Exception:
            pass
        try:
            with engine.begin() as conn:
                if is_sqlite:
                    rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
                    existing = {r[1] for r in rows}
                else:
                    rows = conn.exec_driver_sql(
                        "SELECT column_name FROM information_schema.columns "
                        f"WHERE table_name = '{table}'"
                    ).fetchall()
                    existing = {r[0] for r in rows}
                if col not in existing:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}")
        except Exception:
            pass


@contextmanager
def get_session() -> Iterator[Session]:
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def is_postgres() -> bool:
    return IS_POSTGRES


def db_url_redacted() -> str:
    if not IS_POSTGRES:
        return DATABASE_URL
    try:
        from urllib.parse import urlparse, urlunparse
        u = urlparse(DATABASE_URL)
        netloc = u.hostname or ""
        if u.port:
            netloc = f"{netloc}:{u.port}"
        return urlunparse((u.scheme, netloc, u.path, u.params, u.query, u.fragment))
    except Exception:
        return "postgresql://[redacted]"
