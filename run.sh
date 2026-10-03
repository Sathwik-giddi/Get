#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

API_PORT="${API_PORT:-8123}"
WEB_PORT="${WEB_PORT:-3000}"
MODE="${1:-dev}"

if [ -f .env ]; then
  set -a; source .env; set +a
fi

cleanup() {
  kill "${API_PID:-}" 2>/dev/null || true
  kill "${WEB_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "starting api on :$API_PORT"
.venv/bin/python -m uvicorn api.main:app --host 127.0.0.1 --port "$API_PORT" &
API_PID=$!

for _ in $(seq 1 40); do
  curl -fsS "http://localhost:$API_PORT/health" >/dev/null 2>&1 && break
  sleep 0.5
done
curl -fsS "http://localhost:$API_PORT/health" && echo

if [ "$MODE" = "dev" ]; then
  echo "starting web on :$WEB_PORT (vite dev, proxying /api to :$API_PORT)"
  cd web
  GET_API="http://localhost:$API_PORT" exec npm run dev -- --port "$WEB_PORT"
else
  echo "building web"
  (cd web && npm run build)
  echo "serving web from :$API_PORT (single container, this is what Cloud Run gets)"
  wait "$API_PID"
fi