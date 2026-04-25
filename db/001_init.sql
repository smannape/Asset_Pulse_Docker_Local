-- CAPEX/OPEX dashboard schema.
-- Compatible with PostgreSQL 14+ (Neon free tier, 0.5 GB).
-- Source taxonomy: knowledge base /docs/oil-well-capex-opex-knowledge-base.pplx.md
-- JSONB used where appropriate to keep storage compact.

CREATE TABLE IF NOT EXISTS assets (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(120) NOT NULL,
    asset_type    VARCHAR(40)  NOT NULL CHECK (asset_type IN ('well','pipeline','gathering_center','facility')),
    region        VARCHAR(80),
    metadata_json JSONB,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assets_type   ON assets (asset_type);
CREATE INDEX IF NOT EXISTS idx_assets_region ON assets (region);

CREATE TABLE IF NOT EXISTS asset_cost_profiles (
    id              SERIAL PRIMARY KEY,
    asset_id        INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    capex_inputs    JSONB,
    opex_inputs     JSONB,
    decline_inputs  JSONB
);

CREATE INDEX IF NOT EXISTS idx_cost_profiles_asset ON asset_cost_profiles (asset_id);

CREATE TABLE IF NOT EXISTS price_decks (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(80) NOT NULL,
    oil_price     DOUBLE PRECISION,
    gas_price     DOUBLE PRECISION,
    ngl_price     DOUBLE PRECISION,
    differentials JSONB
);

CREATE TABLE IF NOT EXISTS production_forecasts (
    id            SERIAL PRIMARY KEY,
    asset_id      INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    name          VARCHAR(120),
    -- Compact monthly array as JSONB: [{"month":1,"oil":650,"gas":420,"water":...}]
    monthly       JSONB
);

CREATE TABLE IF NOT EXISTS scenarios (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(120) NOT NULL,
    asset_id    INTEGER REFERENCES assets(id) ON DELETE SET NULL,
    inputs      JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scenarios_asset ON scenarios (asset_id);

CREATE TABLE IF NOT EXISTS scenario_results (
    id                            SERIAL PRIMARY KEY,
    scenario_id                   INTEGER NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,
    npv                           DOUBLE PRECISION,
    pv10                          DOUBLE PRECISION,
    payback_months                DOUBLE PRECISION,
    netback_per_boe               DOUBLE PRECISION,
    economic_limit_boe_per_month  DOUBLE PRECISION,
    -- Aggregated monthly summary (months[], free_cash_flow[], net_revenue[], opex[])
    monthly_summary               JSONB,
    created_at                    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_results_scenario ON scenario_results (scenario_id);
CREATE INDEX IF NOT EXISTS idx_results_npv      ON scenario_results (npv);

CREATE TABLE IF NOT EXISTS cash_flows (
    id            SERIAL PRIMARY KEY,
    scenario_id   INTEGER NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,
    asset_id      INTEGER REFERENCES assets(id) ON DELETE SET NULL,
    -- Compact monthly cash flow rows as JSONB to keep row count low
    monthly_rows  JSONB
);

CREATE TABLE IF NOT EXISTS events (
    id              SERIAL PRIMARY KEY,
    asset_id        INTEGER REFERENCES assets(id) ON DELETE SET NULL,
    event_type      VARCHAR(40) NOT NULL,
    magnitude       DOUBLE PRECISION,
    duration_months INTEGER,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS decision_matrix_runs (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(120),
    criteria    JSONB,
    inputs      JSONB,
    results     JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Sample seed (idempotent guard via NOT EXISTS)
INSERT INTO price_decks (name, oil_price, gas_price, ngl_price, differentials)
SELECT 'Base 2025', 72.0, 2.85, 24.0, '{"oil_diff": -3.0, "gas_diff": -0.40}'::jsonb
WHERE NOT EXISTS (SELECT 1 FROM price_decks WHERE name = 'Base 2025');
