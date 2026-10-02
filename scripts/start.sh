#!/usr/bin/env bash
# Start the production API from the project virtualenv.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
# Free Render instances cannot set a pre-deploy command, so migrate before serving.
.venv/bin/alembic upgrade head
exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
