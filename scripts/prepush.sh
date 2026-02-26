#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
"$PY" -m py_compile api/app/main.py >/dev/null
./scripts/run_and_smoke.sh >/dev/null
./scripts/smoke_ab_patterns.sh >/dev/null
./scripts/run_stable.sh start
trap './scripts/run_stable.sh stop >/dev/null 2>&1 || true' EXIT
