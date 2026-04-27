"""Persistence + scenario import endpoint tests.

Run: `python -m backend.tests.test_persistence` (uses an isolated tmp SQLite).
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Allow running directly: add backend/ to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Force a fresh, isolated SQLite db for this test process BEFORE importing app.
_tmp = tempfile.NamedTemporaryFile(prefix="asset_pulse_test_", suffix=".db", delete=False)
_tmp.close()
os.environ["LOCAL_SQLITE_PATH"] = _tmp.name
os.environ.pop("DATABASE_URL", None)

from fastapi.testclient import TestClient  # noqa: E402

from app.database import init_db  # noqa: E402
from app.main import app  # noqa: E402

init_db()  # ensure tables exist before TestClient skips startup events
client = TestClient(app)


def test_health_ok() -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_run_persists_by_default() -> None:
    payload = {
        "asset_name": "Persist-1",
        "months_horizon": 24,
        "initial_oil_bopd": 400,
        "annual_decline": 0.30,
        "oil_price": 75,
        "fixed_opex_per_month": 8000,
        "oil_var_per_bbl": 4,
        "development_capex": 2_000_000,
    }
    r = client.post("/api/scenario/run", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "scenario_id" in body and isinstance(body["scenario_id"], int)
    # Breakeven oil price returned alongside the result
    assert "breakeven_oil_price" in body

    listing = client.get("/api/scenarios").json()
    ids = [s["id"] for s in listing]
    assert body["scenario_id"] in ids
    saved = next(s for s in listing if s["id"] == body["scenario_id"])
    assert saved["result"]["npv"] is not None
    assert saved["source"] == "api"


def test_run_persist_false_does_not_save() -> None:
    before = len(client.get("/api/scenarios").json())
    r = client.post(
        "/api/scenario/run?persist=false",
        json={"asset_name": "no-persist", "months_horizon": 12, "initial_oil_bopd": 100},
    )
    assert r.status_code == 200
    after = len(client.get("/api/scenarios").json())
    assert after == before


def test_scenario_import_bulk() -> None:
    rows = [
        {
            "scenario_name": "Q1-A",
            "asset_id_or_name": "asset1",
            "notes": "csv row 1",
            "inputs": {
                "asset_name": "asset1", "months_horizon": 24, "initial_oil_bopd": 500,
                "annual_decline": 0.25, "oil_price": 70, "fixed_opex_per_month": 9000,
                "oil_var_per_bbl": 4, "development_capex": 3_000_000,
            },
        },
        {
            "scenario_name": "Q1-B",
            "asset_id_or_name": "asset2",
            "inputs": {
                "asset_name": "asset2", "months_horizon": 24, "initial_oil_bopd": 350,
                "annual_decline": 0.30, "oil_price": 72, "fixed_opex_per_month": 7000,
                "oil_var_per_bbl": 5, "development_capex": 2_500_000,
            },
        },
    ]
    r = client.post("/api/scenarios/import", json={"rows": rows, "run": True})
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["saved"]) == 2
    assert body["errors"] == []
    for entry in body["saved"]:
        assert entry["ran"] is True
        assert entry["asset_alias"] in {"asset1", "asset2"}
        assert entry["npv"] is not None
        assert "breakeven_oil_price" in entry

    listing = client.get("/api/scenarios").json()
    aliases = {s["asset_alias"] for s in listing}
    assert {"asset1", "asset2"}.issubset(aliases)
    csv_imports = [s for s in listing if s["source"] == "csv_import"]
    assert len(csv_imports) >= 2
    # Breakeven flows through to GET listing
    assert any(s["result"] and s["result"].get("breakeven_oil_price") is not None for s in csv_imports)


def test_run_with_extreme_inputs_does_not_500() -> None:
    """NaN/Inf or extreme inputs should not crash the endpoint.

    NPV may legitimately come back as None when sanitised, but the call must
    return 200 and an integer scenario_id rather than a 500.
    """
    payload = {
        "asset_name": "extreme",
        "months_horizon": 6,
        "initial_oil_bopd": 1e9,  # absurdly high — could overflow downstream
        "annual_decline": 0.0,
        "oil_price": 1e6,
        "fixed_opex_per_month": 0,
        "development_capex": 0,
    }
    r = client.post("/api/scenario/run", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "scenario_id" in body


def test_run_against_pre_migration_schema() -> None:
    """Simulate an existing Docker volume on the pre-CSV-import schema.

    init_db() must add the new columns (asset_alias, source,
    breakeven_oil_price, total_boe, fiscal_regime) so that
    /api/scenario/run can persist successfully.
    """
    import importlib
    import sqlite3

    legacy_tmp = tempfile.NamedTemporaryFile(
        prefix="asset_pulse_legacy_", suffix=".db", delete=False
    )
    legacy_tmp.close()
    db_path = legacy_tmp.name
    con = sqlite3.connect(db_path)
    con.executescript(
        """
        CREATE TABLE scenarios (
            id INTEGER PRIMARY KEY, name VARCHAR(120) NOT NULL,
            asset_id INTEGER, inputs JSON, created_at DATETIME
        );
        CREATE TABLE scenario_results (
            id INTEGER PRIMARY KEY, scenario_id INTEGER NOT NULL,
            npv DOUBLE, pv10 DOUBLE, payback_months DOUBLE,
            netback_per_boe DOUBLE, economic_limit_boe_per_month DOUBLE,
            monthly_summary JSON, created_at DATETIME
        );
        """
    )
    con.commit()
    con.close()

    # Re-import the app module against the legacy DB.
    os.environ["LOCAL_SQLITE_PATH"] = db_path
    os.environ.pop("DATABASE_URL", None)
    import app.database as db_mod
    import app.main as main_mod
    importlib.reload(db_mod)
    importlib.reload(main_mod)
    db_mod.init_db()

    legacy_client = TestClient(main_mod.app)
    r = legacy_client.post(
        "/api/scenario/run",
        json={
            "asset_name": "legacy",
            "months_horizon": 12,
            "initial_oil_bopd": 200,
            "oil_price": 70,
            "development_capex": 100_000,
        },
    )
    assert r.status_code == 200, r.text
    assert "scenario_id" in r.json()

    # Restore the original test DB so the rest of the suite continues to work.
    os.environ["LOCAL_SQLITE_PATH"] = _tmp.name
    importlib.reload(db_mod)
    importlib.reload(main_mod)


def test_run_persists_via_jit_migration_without_startup() -> None:
    """Simulate the user's reported 500 path: an existing DB volume that is
    missing the new columns AND the backend that never ran startup migrations
    (e.g. a stale image still in flight before the Hardening commit).

    The persist path's JIT migration retry should still succeed without
    requiring a DB volume reset.
    """
    import importlib
    import sqlite3

    legacy_tmp = tempfile.NamedTemporaryFile(
        prefix="asset_pulse_jit_", suffix=".db", delete=False
    )
    legacy_tmp.close()
    db_path = legacy_tmp.name
    con = sqlite3.connect(db_path)
    con.executescript(
        """
        CREATE TABLE scenarios (
            id INTEGER PRIMARY KEY, name VARCHAR(120) NOT NULL,
            asset_id INTEGER, inputs JSON, created_at DATETIME
        );
        CREATE TABLE scenario_results (
            id INTEGER PRIMARY KEY, scenario_id INTEGER NOT NULL,
            npv DOUBLE, pv10 DOUBLE, payback_months DOUBLE,
            netback_per_boe DOUBLE, economic_limit_boe_per_month DOUBLE,
            monthly_summary JSON, created_at DATETIME
        );
        """
    )
    con.commit()
    con.close()

    os.environ["LOCAL_SQLITE_PATH"] = db_path
    os.environ.pop("DATABASE_URL", None)
    import app.database as db_mod
    import app.main as main_mod
    importlib.reload(db_mod)
    importlib.reload(main_mod)
    # NB: deliberately skip init_db here to mirror the reported failure mode.

    jit_client = TestClient(main_mod.app)
    r = jit_client.post(
        "/api/scenario/run",
        json={
            "asset_name": "jit-migration",
            "months_horizon": 12,
            "initial_oil_bopd": 250,
            "oil_price": 68,
            "development_capex": 200_000,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "scenario_id" in body
    assert body.get("persist_error") is None, body.get("persist_error")

    os.environ["LOCAL_SQLITE_PATH"] = _tmp.name
    importlib.reload(db_mod)
    importlib.reload(main_mod)


def test_run_with_unexpected_inputs_returns_400_not_500() -> None:
    """Pydantic validation already guards most cases. This covers the residual
    path where ``project_scenario`` would otherwise blow up with a non-input
    error: we should surface 400, never 500."""
    bad = {
        "asset_name": "bad",
        "months_horizon": 12,
        "initial_oil_bopd": 100,
        # b_factor inside the allowed range but combined with extreme decline
        # this used to fall through to a generic 500.
        "annual_decline": 0.999,
        "decline_model": "hyperbolic",
        "b_factor": 2.0,
        "oil_price": 70,
        "development_capex": 1_000,
    }
    r = client.post("/api/scenario/run", json=bad)
    # Either a successful run or a clean 400 — never 500.
    assert r.status_code in (200, 400), r.text


def test_scenarios_report_pdf() -> None:
    # Ensure there are at least two scenarios saved to compare in the PDF.
    payload_a = {
        "asset_name": "report-A", "months_horizon": 24, "initial_oil_bopd": 400,
        "annual_decline": 0.30, "oil_price": 70, "fixed_opex_per_month": 8000,
        "oil_var_per_bbl": 4, "development_capex": 1_500_000,
    }
    payload_b = {
        "asset_name": "report-B", "months_horizon": 24, "initial_oil_bopd": 600,
        "annual_decline": 0.40, "oil_price": 75, "fixed_opex_per_month": 9000,
        "oil_var_per_bbl": 4, "development_capex": 2_500_000,
    }
    a = client.post("/api/scenario/run", json=payload_a).json()
    b = client.post("/api/scenario/run", json=payload_b).json()
    ids = [a["scenario_id"], b["scenario_id"]]

    r = client.post("/api/scenarios/report.pdf", json={"scenario_ids": ids})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content.startswith(b"%PDF-")
    # Should be at least a few KB — sanity bound, not exact.
    assert len(r.content) > 2000

    r2 = client.post("/api/scenarios/report.pdf", json={"scenario_ids": [10**9]})
    assert r2.status_code == 404


def test_scenario_delete() -> None:
    payload = {
        "asset_name": "to-delete", "months_horizon": 12, "initial_oil_bopd": 200,
        "annual_decline": 0.4, "oil_price": 60, "fixed_opex_per_month": 5000,
        "oil_var_per_bbl": 4, "development_capex": 1_000_000,
    }
    sid = client.post("/api/scenario/run", json=payload).json()["scenario_id"]
    r = client.delete(f"/api/scenarios/{sid}")
    assert r.status_code == 200
    after = client.get("/api/scenarios").json()
    assert sid not in [s["id"] for s in after]


def main() -> None:
    tests = [
        test_health_ok,
        test_run_persists_by_default,
        test_run_persist_false_does_not_save,
        test_scenario_import_bulk,
        test_run_with_extreme_inputs_does_not_500,
        test_run_against_pre_migration_schema,
        test_run_persists_via_jit_migration_without_startup,
        test_run_with_unexpected_inputs_returns_400_not_500,
        test_scenarios_report_pdf,
        test_scenario_delete,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL  {t.__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"ERROR {t.__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} tests passed.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
