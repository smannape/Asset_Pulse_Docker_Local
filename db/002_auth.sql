-- =============================================================================
-- Asset Pulse — Auth schema (migration 002)
-- Run after 001_init.sql. Idempotent (IF NOT EXISTS on all objects).
-- Compatible with PostgreSQL 14+.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- users
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    email         VARCHAR(255) NOT NULL UNIQUE,
    full_name     VARCHAR(120),
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(20)  NOT NULL DEFAULT 'user',   -- 'admin' | 'user'
    is_active     BOOLEAN      NOT NULL DEFAULT true,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    last_login    TIMESTAMPTZ,
    created_by    INTEGER REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_users_email  ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_role   ON users (role);
CREATE INDEX IF NOT EXISTS idx_users_active ON users (is_active);

-- ---------------------------------------------------------------------------
-- user_sessions — one row per login; jti mirrors the JWT "jti" claim so tokens
-- can be revoked by flipping is_active without touching the secret key.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_sessions (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    jti         VARCHAR(100) UNIQUE,
    ip_address  VARCHAR(50),
    user_agent  VARCHAR(500),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at  TIMESTAMPTZ,
    is_active   BOOLEAN NOT NULL DEFAULT true
);

CREATE INDEX IF NOT EXISTS idx_sessions_user   ON user_sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_jti    ON user_sessions (jti);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON user_sessions (is_active);

-- ---------------------------------------------------------------------------
-- activity_log — immutable audit trail; user_email denormalised so the record
-- survives even if the user row is later deleted.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS activity_log (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER REFERENCES users(id) ON DELETE SET NULL,
    user_email    VARCHAR(255),
    action        VARCHAR(80)  NOT NULL,
    resource_type VARCHAR(40),
    resource_id   INTEGER,
    details       JSONB,
    ip_address    VARCHAR(50),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_activity_user      ON activity_log (user_id);
CREATE INDEX IF NOT EXISTS idx_activity_action    ON activity_log (action);
CREATE INDEX IF NOT EXISTS idx_activity_created   ON activity_log (created_at DESC);
