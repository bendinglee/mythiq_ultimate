#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p logs

PY="$ROOT/.venv/bin/python"
test -x "$PY" || { echo "❌ missing venv python: $PY"; exit 1; }

# kill whatever is on 7777
PID="$(lsof -nP -iTCP:7777 -sTCP:LISTEN -t 2>/dev/null | head -n 1 || true)"
test -n "${PID:-}" && kill -9 "$PID" || true

exec "$PY" -m uvicorn api.app.main:app --host 127.0.0.1 --port 7777
