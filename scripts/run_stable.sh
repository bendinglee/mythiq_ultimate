#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
BASE="${BASE:-http://127.0.0.1:7777}"
PIDFILE=".uvicorn.pid"
LOG="logs/uvicorn.log"

wait_readyz() {
  # wait up to ~6s for readyz
  for i in $(seq 1 30); do
    curl -fsS "$BASE/readyz" >/dev/null 2>&1 && return 0
    sleep 0.2
  done
  return 1
}

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
"$PY" -m uvicorn api.app.main:app --host 127.0.0.1 --port 7777 --workers 1 --no-access-log \
      >>"$LOG" 2>&1 &
    echo $! > "$PIDFILE"
    if wait_readyz; then
      echo "STARTED pid=$(cat "$PIDFILE") log=$LOG READYZ_OK"
    else
      echo "STARTED pid=$(cat "$PIDFILE") log=$LOG READYZ_FAIL"
      echo "---- last log lines ----"
      tail -n 80 "$LOG" || true
      exit 1
    fi
    ;;
  stop)
    stop
    echo "STOPPED"
    ;;
  status)
    if test -f "$PIDFILE" && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
      echo "RUNNING pid=$(cat "$PIDFILE")"
      if wait_readyz; then echo "READYZ_OK"; else echo "READYZ_FAIL"; exit 1; fi
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