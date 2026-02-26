#!/usr/bin/env bash
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:7777}"
PIDFILE=".uvicorn.pid"
LOG="logs/uvicorn.log"

stop() {
  if test -f "$PIDFILE"; then
    kill "$(cat "$PIDFILE")" 2>/dev/null || true
    rm -f "$PIDFILE"
  fi
  lsof -ti :7777 | xargs kill -9 2>/dev/null || true
}

case "${1:-}" in
  start)
    stop
    nohup env PYTHONUNBUFFERED=1 UVICORN_LOOP=asyncio \
      python3 -m uvicorn api.app.main:app --host 127.0.0.1 --port 7777 --workers 1 --no-access-log \
      >>"$LOG" 2>&1 &
    echo $! > "$PIDFILE"
    echo "STARTED pid=$(cat "$PIDFILE") log=$LOG"
    ;;
  stop)
    stop
    echo "STOPPED"
    ;;
  status)
    if test -f "$PIDFILE" && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
      echo "RUNNING pid=$(cat "$PIDFILE")"
      curl -fsS "$BASE/readyz" >/dev/null && echo "READYZ_OK" || echo "READYZ_FAIL"
      exit 0
    fi
    echo "NOT_RUNNING"
    exit 1
    ;;
  *)
    echo "usage: $0 {start|stop|status}"
    exit 2
    ;;
esac
