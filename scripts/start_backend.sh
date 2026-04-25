#!/usr/bin/env bash
# Start the Asset Pulse FastAPI backend locally.
# Loads backend/.env (if present) and serves on http://localhost:8000.
#
# Usage:
#   ./scripts/start_backend.sh
#
# Prerequisites:
#   - Python >= 3.10 on PATH
#   - backend/.venv created and requirements installed (see local deployment guide)
#   - backend/.env configured with DATABASE_URL pointing at PostgreSQL 17 on
#     localhost:5433 (copy from backend/.env.local.example)

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR/backend"

if [ ! -d ".venv" ]; then
  echo "[start_backend] No virtualenv found at backend/.venv."
  echo "[start_backend] Create it once with:"
  echo "    cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate

if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source ./.env
  set +a
else
  echo "[start_backend] WARNING: backend/.env not found — falling back to SQLite."
  echo "[start_backend] Copy backend/.env.local.example to backend/.env to use PostgreSQL 17."
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --reload
