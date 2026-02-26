#!/usr/bin/env bash
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:7777}"

case "${1:-}" in
  start)
    lsof -ti :7777 | xargs kill -9 2>/dev/null || true
    exec python3 -m uvicorn api.app.main:app --host 127.0.0.1 --port 7777 --reload
    ;;
  run)
    exec python3 -m uvicorn api.app.main:app --host 127.0.0.1 --port 7777
    ;;
  smoke)
    exec ./scripts/smoke_openapi.sh
    ;;
  *)
    echo "usage: $0 {start|run|smoke}"
    exit 2
    ;;
esac
