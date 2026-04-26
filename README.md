# Asset Pulse — Forecasting & Decision Dashboard

Production-quality prototype for forecasting asset performance, analysing CAPEX, OPEX, profitability, uncertainties, event impacts, and shut-in/restart decisions across a portfolio of wells, pipelines, gathering centers, and facilities. Supports US, NOC, PSC/EPSA, TSC/RSC, and Middle East concession fiscal regimes inside the Scenario calculation flow.

- **Frontend:** React + TypeScript + Vite, Palantir-style terminal aesthetic, beige + orange theme, light/dark toggle, custom inline SVG logo. Static, Netlify-ready.
- **Backend:** Python FastAPI. All financial formulas in Python (CAPEX, OPEX, revenue, NPV, PV-10, economic limit, tornado sensitivities, Monte Carlo, weighted decision matrix, event impact stacking).
- **Database:** PostgreSQL (Neon-compatible), JSONB used where useful. Local SQLite fallback when `DATABASE_URL` is absent.
- **Knowledge base:** [`docs/oil-well-capex-opex-knowledge-base.pplx.md`](docs/oil-well-capex-opex-knowledge-base.pplx.md) — formulas, taxonomy, and source citations.
- **Application help:** [`docs/application-help.pplx.md`](docs/application-help.pplx.md) — user guide for scenarios, sensitivity, Monte Carlo, events, decision matrix, assets, and CSV exchange.

```
oil-capex-opex-dashboard/
├── frontend/        # Vite React/TS app, deployed to Netlify
├── backend/         # FastAPI + formula modules + tests
├── db/              # PostgreSQL migration (Neon-ready)
└── docs/            # Knowledge base
```

---

## Quick start (Docker Desktop) — recommended

If you have Docker Desktop installed, you can run the full stack
(PostgreSQL 17 + FastAPI backend + Nginx-served React frontend) with no
manual Python/Node/PostgreSQL setup:

```bash
cp .env.docker.example .env       # then edit POSTGRES_PASSWORD
docker compose up --build
```

Open <http://localhost:8080> — that's the entire app. The frontend container
reverse-proxies `/api/*` to the backend, so a single URL is all you need.

Step-by-step beginner guide (install, env file, health checks, logs, backup/
restore, troubleshooting):
[`docs/docker-desktop-deployment.pplx.md`](docs/docker-desktop-deployment.pplx.md).

---

## Quick start (local, without Docker)

Two terminals.

**Backend** (Python ≥ 3.10):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./run.sh                       # serves on http://localhost:8000
```

The first request triggers schema creation and seed data (5 sample assets + 1 scenario) into a SQLite file at `/tmp/capex_opex_demo.db`. No credentials required.

> **Running against your own PostgreSQL 17 on `localhost:5433`?**
> Follow the step-by-step guide at
> [`docs/local-deployment-postgresql17.pplx.md`](docs/local-deployment-postgresql17.pplx.md).
> It covers creating the database and user, applying `db/001_init.sql`,
> configuring `backend/.env` from `backend/.env.local.example`, and using
> the cross-platform helper scripts in [`scripts/`](scripts/) to launch the
> backend and frontend on Windows, macOS, and Linux.

**Frontend** (Node ≥ 18):

```bash
cd frontend
npm install
npm run dev                    # serves on http://localhost:5173
```

Vite proxies `/api/*` to `http://localhost:8000` automatically — see `frontend/vite.config.ts`.

Visit `http://localhost:5173`. Click **Run scenario** to generate a 120-month projection, then explore Sensitivity, Monte Carlo, Events, Decision Matrix, Assets, and CSV Exchange views.

### Run tests

```bash
python backend/tests/test_modules.py
```

Eighteen tests cover well CAPEX, pipeline inch-mile CAPEX, NPV, economic limit, scenario engine, hyperbolic decline tail volume, tornado ordering, Monte Carlo percentiles, decision matrix recommendations, and the five fiscal regimes (US royalty/tax, NOC internal, PSC/EPSA cost recovery, TSC/RSC remuneration, and concession tax/royalty including Saudi-style progressive royalty).

---

## Architecture

```
                   ┌────────────────────────┐
                   │  Browser               │
                   └─────────┬──────────────┘
                             │ HTTPS, JSON
                   ┌─────────▼──────────────┐
                   │  Netlify (CDN, static) │  ← frontend/dist
                   └─────────┬──────────────┘
                             │ /api/*  (CORS or proxy)
                   ┌─────────▼──────────────┐
                   │  Python FastAPI        │  ← backend/app/main.py
                   │  formulas, scenario,   │     (separate host;
                   │  decision matrix       │      Render / Fly.io /
                   └─────────┬──────────────┘      AWS / Railway / VM)
                             │ asyncpg / SQLAlchemy
                   ┌─────────▼──────────────┐
                   │  Neon PostgreSQL       │
                   │  (free tier, 0.5 GB)   │
                   └────────────────────────┘
```

**Why is the Python backend hosted separately from Netlify?**
Netlify Functions do not natively run Python — Netlify’s Python support is for configurable Python *build* versions, not a runtime ([Netlify Python build versions](https://www.netlify.com/blog/announcing-configurable-python-versions-in-netlify-builds/), [Netlify Functions config docs](https://docs.netlify.com/build/functions/optional-configuration/)). Therefore the recommended production architecture is **React on Netlify + FastAPI on a separate Python host + Neon as shared Postgres**.

---

## Deploying the frontend to Netlify

1. Push the repo to GitHub (or connect a Netlify drop deploy).
2. In **Site settings → Build & deploy**:
   - **Base directory:** `frontend`
   - **Build command:** `npm install && npm run build`
   - **Publish directory:** `dist`
3. Add an environment variable in Netlify:

   | Var                  | Value                                      |
   | -------------------- | ------------------------------------------ |
   | `VITE_API_BASE_URL`  | `https://your-fastapi-host.example.com`    |

   At build time Vite inlines this into the bundle, so the deployed UI calls your separate Python API directly. Leave it unset to use a relative `/api` path with a Netlify redirect (see `frontend/netlify.toml`).
4. Trigger a deploy. Netlify serves the SPA from `dist/` with the SPA fallback already configured in `netlify.toml`.

Optional: instead of `VITE_API_BASE_URL`, uncomment the `[[redirects]]` block in `frontend/netlify.toml` and set the destination to your FastAPI host. The frontend will keep calling `/api/...` and Netlify will reverse-proxy to your API.

---

## Deploying the Python API

You need a Python runtime. Examples:

### Render.com
1. Create a **Web Service** from the repo.
2. **Root directory:** `backend`. **Build:** `pip install -r requirements.txt`. **Start:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
3. Set env vars (below).

### Fly.io
```bash
cd backend
fly launch --no-deploy
# edit fly.toml: internal_port = 8000, command = uvicorn app.main:app --host 0.0.0.0 --port 8000
fly secrets set DATABASE_URL='postgresql://...'
fly deploy
```

### Railway / Fly / Heroku-style
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Any VM / container
The `backend/run.sh` script starts uvicorn on port 8000. Wrap it in `systemd`, `pm2`, or a Docker image if you prefer.

### Required environment variables

| Var              | Description                                                    |
| ---------------- | -------------------------------------------------------------- |
| `DATABASE_URL`   | Neon connection string. Use the **pooled** URL for the API.    |
| `CORS_ORIGINS`   | Comma-separated list, e.g. `https://your-site.netlify.app`.    |
| `LOCAL_SQLITE_PATH` | (Optional) Path for local SQLite when `DATABASE_URL` unset. |

---

## Connecting Neon

1. Sign in at [neon.tech](https://neon.tech) and create a new project (free tier provides 0.5 GB storage and scale-to-zero after 5 minutes — see [Neon plans](https://neon.tech/docs/introduction/plans)).
2. Copy the **pooled** connection string for the API runtime, e.g.

   ```
   postgresql://user:pass@ep-xxx-pooler.aws.neon.tech/dbname?sslmode=require
   ```

   For Python, Neon recommends `DATABASE_URL` with `sslmode=require` ([Neon Python guide](https://neon.tech/docs/guides/python)). The pooled URL is appropriate for serverless or bursty APIs; use the direct (non-pooled) URL for migrations because pooled connections can cause migration issues ([Neon Knex connection guide](https://neon.tech/docs/guides/knex)).

3. Run the migration once against your Neon project (use the **direct** URL):

   ```bash
   psql "postgresql://user:pass@ep-xxx.aws.neon.tech/dbname?sslmode=require" \
     -f db/001_init.sql
   ```

4. Set `DATABASE_URL` (pooled) on your API host and restart. The FastAPI app will detect Postgres and use JSONB columns.

The local SQLite fallback used in development gracefully degrades JSONB to JSON/TEXT, so the same code runs in both environments.

---

## API surface (FastAPI)

Interactive docs at `http://localhost:8000/docs`.

| Method | Path                              | Purpose                                              |
| ------ | --------------------------------- | ---------------------------------------------------- |
| GET    | `/api/health`                     | Status + which database backend is active            |
| GET    | `/api/assets`                     | List sample wells/pipelines/facilities + cost profiles |
| GET    | `/api/price-decks`                | Price decks                                          |
| POST   | `/api/capex/well`                 | Bottom-up well CAPEX                                 |
| POST   | `/api/capex/pipeline`             | INGAA inch-mile pipeline CAPEX                       |
| POST   | `/api/capex/facility`             | Capacity-based facility CAPEX                        |
| POST   | `/api/scenario/run?persist=true`  | Run scenario, optionally store summary in DB         |
| GET    | `/api/scenarios`                  | List recent scenarios + summary KPIs                 |
| POST   | `/api/uncertainty/tornado`        | Tornado sensitivity                                  |
| POST   | `/api/uncertainty/montecarlo`     | Monte Carlo NPV (P10/P50/P90)                        |
| POST   | `/api/events/impact`              | Stack events on top of base NPV                      |
| GET    | `/api/decision-matrix/criteria`   | Default weighted criteria                            |
| POST   | `/api/decision-matrix/score`      | Score assets, return ranked recommendations          |
| POST   | `/api/seed`                       | Idempotent seed                                      |

---

## Formula modules (Python)

| Module                                  | What it does                                                                                                     |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `backend/app/modules/cost_models.py`    | Well, pipeline, facility CAPEX; OPEX (fixed + variable + chemicals + energy + maintenance + workover + taxes); revenue & netback; ARO present value. |
| `backend/app/modules/economics.py`      | NPV (monthly or annual), PV-10, payback (interpolated), economic-limit rate, FCF series, breakeven price.        |
| `backend/app/modules/uncertainty.py`    | Tornado sensitivity (sorted by NPV swing), scenario comparison, Monte Carlo (triangular / lognormal / uniform / normal). |
| `backend/app/modules/decision_matrix.py`| Weighted scoring with eight default criteria, recommendation engine, event-impact deltas (CAPEX overrun / downtime / price drop / OPEX escalation / restart cost). |
| `backend/app/modules/scenario.py`       | End-to-end monthly projection with exponential, hyperbolic, or harmonic decline, water-cut interpolation, economic-limit truncation, capex/opex multipliers. Used as the NPV callback for tornado/Monte Carlo. Also drives the fiscal-regime layer. |
| `backend/app/modules/fiscal_regimes.py` | Regime-aware post-processing of the base monthly cash flow: US royalty/tax (default no-op), NOC internal economics, PSC/EPSA cost recovery (royalty → cost-oil ceiling → carry-forward → profit-oil split → contractor tax → optional CAPEX uplift), TSC/RSC (cost reimbursement subject to periodic cap + flat remuneration $/BOE + carry-forward), and concession tax/royalty with optional Saudi-style progressive tiers (15%/45%/80% at $70/$100, AGSI). Returns `fiscal.summary` + per-month breakdown, and replaces the base FCF with the contractor view so NPV/PV-10/payback all reflect the regime. |

All formulas have inline citations to the source (EIA, INGAA, COPAS, PwC, Deloitte, SPE, AOGR, Stout, Neon docs, Bindemann/Oxford Energy, AGSI). See `docs/oil-well-capex-opex-knowledge-base.pplx.md` for the full set.

### Fiscal regime references

- PSC/EPSA cost-recovery formulas: Bindemann, *Production Sharing Agreements: An Economic Analysis*, Oxford Energy WPM 25 (1999) — https://www.oxfordenergy.org/wpcms/wp-content/uploads/2010/11/WPM25-ProductionSharingAgreementsAnEconomicAnalysis-KBindemann-1999.pdf
- Oman EPSA dispute taxonomy: Daily Jus, July 2024 — https://dailyjus.com/world/2024/07/disputes-under-omani-exploration-and-production-sharing-contracts
- General PSC fiscal review: PMC7798991 — https://pmc.ncbi.nlm.nih.gov/articles/PMC7798991/
- Saudi progressive royalty + 50% income tax: AGSI Aramco analysis — https://agsi.org/analysis/aramco-and-the-saudi-government-budget/

---

## Database schema

`db/001_init.sql` is the canonical Postgres migration (Neon free tier compatible). Tables:

- `assets` — wells, pipelines, gathering centers, facilities (`metadata_json` JSONB)
- `asset_cost_profiles` — default CAPEX/OPEX/decline assumptions per asset (JSONB)
- `price_decks` — oil/gas/NGL prices + differentials (JSONB)
- `production_forecasts` — monthly streams stored as compact JSONB arrays
- `scenarios` + `scenario_results` — inputs JSONB + summary KPIs and a compact `monthly_summary` JSONB for charting. Fiscal regime fields (`fiscal_regime`, `psc_*`, `tsc_*`, `concession_*`, `noc_*`) are stored inside `scenarios.inputs` JSONB, so no migration is needed; existing rows continue to deserialize with `fiscal_regime` defaulting to `us_royalty_tax`.
- `cash_flows` — full monthly rows as JSONB (only persist for selected scenarios to fit in 0.5 GB)
- `events` — shut-in/restart/workover/CAPEX overrun history
- `decision_matrix_runs` — saved matrix scoring runs

JSONB is used for compact monthly arrays so the row count stays low (each scenario is one row, not 120). The Python ORM models in `backend/app/database.py` mirror this schema and degrade JSONB → JSON automatically on SQLite.

---

## Frontend features

- **Top bar**: brand mark + nav links + theme toggle (`[ DARK ]` / `[ LIGHT ]`).
- **Left command rail**: keyboard-style commands (Scenario, Sensitivity, Events, Decision Matrix, Assets), loaded-asset summary, API/DB status.
- **KPI strip**: NPV, PV-10, payback, netback/BOE, EUR (BOE), economic limit, truncation flag, discount rate.
- **Scenario inputs panel**: 25+ engineering inputs in a two-column compact form. Load any sample asset profile to hydrate the form.
- **Decline model selector**: exponential, hyperbolic, or harmonic decline using first-year decline and b-factor assumptions.
- **Analysis report console**: terminal-style printout with header, KPIs, first 12 months of cash flow, profitability commentary, and blinking cursor.
- **Cash flow chart**: SVG bars (monthly FCF) + cumulative line. No external chart library required.
- **Sensitivity / tornado**: ±% swings on key drivers, ranked by NPV swing, rendered as low/high bars around the base.
- **Monte Carlo uncertainty**: configurable triangular distributions for oil price, CAPEX multiplier and OPEX multiplier; returns P10/P50/P90, mean, standard deviation, min/max and downside commentary.
- **Event impact stack**: append CAPEX overrun, downtime, price drops, OPEX escalation, or restart cost; see ΔNPV per event and final NPV.
- **Weighted decision matrix**: edit metrics for any number of assets; receive ranked weighted score, shut-in vs keep-online pressure, and a categorical recommendation (Keep online / Shut in / Choke back / Restart / Review manually).
- **Asset registry**: sample wells/pipelines/facilities with one-click load into the scenario form.
- **CSV Exchange**: export scenario assumptions, monthly cash flow, and asset registry to CSV; import edited one-row scenario input CSVs from Excel.
- **Theme**: beige + orange palette, Palantir-style UI and mono font stacks, light/dark toggle in pure React state (no localStorage).
- **Help file**: `docs/application-help.pplx.md` explains how operators should use each application view and interpret results.

---

## Limitations & next steps

- The local fallback is SQLite. For multi-user persistence and shared scenario history, set `DATABASE_URL` to your Neon pooled URL and run `db/001_init.sql`.
- CSV import/export is intentionally frontend-side for quick Excel handoff. For governed multi-user uploads, add backend validation and an import history table.
- Hyperbolic decline is available, but type-curve calibration, terminal decline switching, and well-test data fitting are not yet included.
- No authentication. Add a reverse proxy or platform-level auth before exposing the API publicly.
- Tax modeling is single-rate. Real fiscal regimes (severance, ad valorem, federal income tax, NOL carryforward) are intentionally simplified.

---

## License

Demo / educational. The default benchmarks (EIA, INGAA, COPAS) come from public sources cited inline in the knowledge base; replace seed values with your operator-specific AFE, LOE, production, water, and midstream data before any economic decision.
