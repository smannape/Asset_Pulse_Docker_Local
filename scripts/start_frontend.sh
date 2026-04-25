#!/usr/bin/env bash
# Start the Asset Pulse Vite frontend locally on http://localhost:5173.
#
# Usage:
#   ./scripts/start_frontend.sh
#
# Prerequisites:
#   - Node.js >= 18 on PATH
#   - frontend/node_modules installed (run `npm install` in frontend/ first)

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR/frontend"

if [ ! -d "node_modules" ]; then
  echo "[start_frontend] node_modules missing — running 'npm install' first."
  npm install
fi

exec npm run dev
