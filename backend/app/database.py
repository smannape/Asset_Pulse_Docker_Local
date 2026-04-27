"""
Database layer.

Production: Postgres / Neon via SQLAlchemy. Set DATABASE_URL env var with
postgresql://user:pass@host/db?sslmode=require

Local fallback: when DATABASE_URL is absent, uses an in-memory SQLite database
so QA can run without credentials. JSONB columns degrade to JSON/text on SQLite.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import (
    Column, DateTime, Float, Integer, MetaData, String, Text, create_engine, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.types import JSON


def _resolve_database_url() -> tuple[str, bool]:
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        return url, True
    # Local fallback. Use file-backed SQLite so seed survives across calls.
    fallback_path = os.getenv("LOCAL_SQLITE_PATH", "/tmp/capex_opex_demo.db")
    return f"sqlite:///{fallback_path}", False


DATABASE_URL, IS_POSTGRES = _resolve_database_url()


# JSONB on Postgres, JSON on SQLite
def _json_column():
    if IS_POSTGRES:
        return JSONB
    return JSON


engine: Engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Asset(Base):
    __tablename__ = "assets"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    asset_type = Column(String(40), nullable=False)  # well, pipeline, gathering_center, facility
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
    asset_alias = Column(String(160))  # raw asset_id_or_name from CSV when no FK match
    source = Column(String(40))  # "manual" | "csv_import" | "api"
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
    breakeven_oil_price = Column(Float)  # USD/bbl that drives NPV to ~zero
    total_boe = Column(Float)
    fiscal_regime = Column(String(40))
    monthly_summary = Column(_json_column())  # compact: months, net_revenue, opex, fcf
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


def init_db() -> None:
    Base.metadata.create_all(engine)
    _migrate_columns()


def ensure_scenario_schema() -> None:
    """Idempotent, cheap schema check used at request time.

    On long-running containers built before the CSV-import / breakeven release,
    the new columns may still be missing on the existing volume even after
    startup migrations. Calling this from the persist path guarantees a clean
    insert without forcing the user to wipe their DB.
    """
    Base.metadata.create_all(engine)
    _migrate_columns()


def _migrate_columns() -> None:
    """Idempotent column adds for upgrades from earlier schemas.

    Runs each ALTER on its own short-lived connection so a failure on one
    column never poisons the others (Postgres aborts a whole transaction on
    error). For SQLite versions older than 3.35 we fall back to checking
    PRAGMA before adding the column.
    """
    _add_columns: list[tuple[str, str, str]] = [
        ("scenarios", "asset_alias", "VARCHAR(160)"),
        ("scenarios", "source", "VARCHAR(40)"),
        ("scenario_results", "breakeven_oil_price", "DOUBLE PRECISION"),
        ("scenario_results", "total_boe", "DOUBLE PRECISION"),
        ("scenario_results", "fiscal_regime", "VARCHAR(40)"),
    ]
    is_sqlite = DATABASE_URL.startswith("sqlite")
    for table, col, coltype in _add_columns:
        # Try the standard, atomic path first.
        added = False
        try:
            with engine.begin() as conn:
                conn.exec_driver_sql(
                    f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {coltype}"
                )
            added = True
        except Exception:
            added = False
        if added:
            continue
        # Fallback: introspect existing columns, then add only if missing.
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
                    conn.exec_driver_sql(
                        f"ALTER TABLE {table} ADD COLUMN {col} {coltype}"
                    )
        except Exception:
            # Final swallow: never let a migration failure crash startup.
            # /api/scenario/run will surface a clearer error if the column is
            # actually missing at insert time.
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
    # Redact credentials before returning
    try:
        from urllib.parse import urlparse, urlunparse
        u = urlparse(DATABASE_URL)
        netloc = u.hostname or ""
        if u.port:
            netloc = f"{netloc}:{u.port}"
        return urlunparse((u.scheme, netloc, u.path, u.params, u.query, u.fragment))
    except Exception:
        return "postgresql://[redacted]"
