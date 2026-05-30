#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PY="$ROOT/.venv/bin/python"

if [[ ! -x "$VENV_PY" ]]; then
  echo ".venv not found. Run: make setup"
  exit 1
fi

if ! command -v pnpm >/dev/null 2>&1; then
  echo "pnpm is required. Install it, then run: make setup"
  exit 1
fi

if ! command -v redis-cli >/dev/null 2>&1; then
  echo "redis-cli is required. On macOS: brew install redis"
  exit 1
fi

"$ROOT/scripts/native-db-setup.sh"

if ! redis-cli -u "${REDIS_URL:-redis://localhost:6379/0}" ping >/dev/null 2>&1; then
  echo "Redis is not accepting connections at ${REDIS_URL:-redis://localhost:6379/0}."
  echo "On macOS: brew services start redis"
  exit 1
fi

for port in 3000 3001 3002 8000 8001 8002; do
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Port $port is already in use. Stop that process before running the native stack."
    lsof -nP -iTCP:"$port" -sTCP:LISTEN
    exit 1
  fi
done

mkdir -p "$ROOT/logs" "$ROOT/runs" "$ROOT/suts/lms/backend/uploads"

if [[ ! -f "$ROOT/.env" && -f "$ROOT/.env.example" ]]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
fi

pids=()
names=()

cleanup() {
  for pid in "${pids[@]:-}"; do
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill "$pid" >/dev/null 2>&1 || true
    fi
  done
}
trap cleanup INT TERM EXIT

start() {
  local name="$1"
  shift
  echo "Starting $name..."
  (
    cd "$ROOT"
    "$@"
  ) >"$ROOT/logs/$name.log" 2>&1 &
  pids+=("$!")
  names+=("$name")
}

start dashboard env \
  NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8000}" \
  ORCHESTRATOR_INTERNAL_URL="${ORCHESTRATOR_INTERNAL_URL:-http://localhost:8000}" \
  pnpm --filter dashboard dev

start orchestrator env \
  DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://debugra:debugra@localhost:5432/debugra}" \
  REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}" \
  "$VENV_PY" -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 --app-dir "$ROOT/apps/orchestrator"

start lms-backend env \
  DATABASE_URL="${LMS_DATABASE_URL:-postgresql+asyncpg://lms:lms@localhost:5432/lms}" \
  UPLOAD_DIR="$ROOT/suts/lms/backend/uploads" \
  "$VENV_PY" -m uvicorn main:app --reload --host 0.0.0.0 --port 8001 --app-dir "$ROOT/suts/lms/backend"

start lms-frontend env \
  NEXT_PUBLIC_API_URL="${LMS_API_URL:-http://localhost:8001}" \
  BACKEND_URL="${LMS_API_URL:-http://localhost:8001}" \
  pnpm --filter lms-frontend dev

start shop-backend env \
  DATABASE_URL="${SHOP_DATABASE_URL:-postgresql+asyncpg://shop:shop@localhost:5432/shop}" \
  "$VENV_PY" -m uvicorn main:app --reload --host 0.0.0.0 --port 8002 --app-dir "$ROOT/suts/shop/backend"

start shop-frontend env \
  NEXT_PUBLIC_API_URL="${SHOP_API_URL:-http://localhost:8002}" \
  BACKEND_URL="${SHOP_API_URL:-http://localhost:8002}" \
  pnpm --filter shop-frontend dev

cat <<EOF

Debugra native stack is starting.

Dashboard:     http://localhost:3000
Orchestrator:  http://localhost:8000/docs
LMS:           http://localhost:3001
Shop:          http://localhost:3002

Logs are in $ROOT/logs/*.log. Press Ctrl-C to stop everything.
EOF

while true; do
  for i in "${!pids[@]}"; do
    pid="${pids[$i]}"
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      if wait "$pid"; then
        code=0
      else
        code="$?"
      fi
      echo "${names[$i]} exited with status $code. See $ROOT/logs/${names[$i]}.log"
      exit "$code"
    fi
  done
  sleep 1
done
