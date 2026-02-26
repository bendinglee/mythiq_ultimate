#!/usr/bin/env bash
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:7777}"

lsof -ti :7777 | xargs kill -9 2>/dev/null || true

python3 -m uvicorn api.app.main:app --host 127.0.0.1 --port 7777 --workers 1 --no-access-log &
PID=$!

cleanup(){ kill "$PID" 2>/dev/null || true; }
trap cleanup EXIT

# wait up to ~5s
for i in $(seq 1 25); do
  curl -fsS "$BASE/readyz" >/dev/null && break
  sleep 0.2
done

./scripts/smoke_openapi.sh
echo RUN_AND_SMOKE_OK
