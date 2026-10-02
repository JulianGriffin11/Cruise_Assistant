#!/usr/bin/env bash
# Build the frontend and install Python dependencies for a single Render service.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -x "${HOME}/.local/bin/uv" ]]; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="${HOME}/.local/bin:${PATH}"

# Empty means the browser calls this same host (/cruises, /documents, /chat).
export VITE_API_BASE_URL="${VITE_API_BASE_URL:-}"

cd "$ROOT/frontend"
npm ci
npm run build

cd "$ROOT/backend"
uv sync --frozen --no-dev
