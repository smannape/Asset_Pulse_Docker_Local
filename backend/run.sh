#!/usr/bin/env bash
# Convenience launcher: starts FastAPI on port 8000 with reload.
set -euo pipefail
cd "$(dirname "$0")"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --reload
