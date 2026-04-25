#!/usr/bin/env bash
# Apply db/001_init.sql to your local PostgreSQL 17 instance on port 5433.
#
# Usage:
#   ./scripts/init_db.sh                        # uses defaults below
#   PGUSER=asset_pulse PGDATABASE=asset_pulse ./scripts/init_db.sh
#
# Defaults match the local deployment guide. Override with environment variables
# if your database, user, host, or port differ.

set -euo pipefail

PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5433}"
PGUSER="${PGUSER:-asset_pulse}"
PGDATABASE="${PGDATABASE:-asset_pulse}"

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SQL_FILE="$ROOT_DIR/db/001_init.sql"

if [ ! -f "$SQL_FILE" ]; then
  echo "[init_db] Could not find $SQL_FILE"
  exit 1
fi

echo "[init_db] Applying $SQL_FILE to $PGHOST:$PGPORT/$PGDATABASE as $PGUSER"
echo "[init_db] You will be prompted for the database password."

exec psql "host=$PGHOST port=$PGPORT user=$PGUSER dbname=$PGDATABASE" -f "$SQL_FILE"
