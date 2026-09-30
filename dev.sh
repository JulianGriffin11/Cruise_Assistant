# ./dev.sh

ROOT="$(cd "$(dirname "$0")" && pwd)"

cleanup() {
  kill $(jobs -p) 2>/dev/null
}
trap cleanup EXIT INT TERM

(cd "$ROOT/backend" && uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000) &
(cd "$ROOT/frontend" && npm run dev) &

wait
