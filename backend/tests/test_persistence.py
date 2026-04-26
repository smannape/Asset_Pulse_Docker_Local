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
