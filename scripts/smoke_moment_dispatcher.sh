#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PY="./.venv/bin/python"
LOG="/tmp/smoke_moment_dispatcher.log"

"$PY" shortforge/viral_engine/run_moment_project.py --run-id "sidemen_house_party_1773597868" > "$LOG" 2>&1
grep -q "PROJECT_MODE: moment_render_pipeline" "$LOG"

if "$PY" shortforge/viral_engine/run_moment_project.py --run-id "sidemen_scene_pipeline" >> "$LOG" 2>&1; then
  echo "❌ expected archive-only project to fail" >> "$LOG"
  cat "$LOG"
  exit 1
fi

grep -q "archive-only project" "$LOG"
echo "SMOKE_MOMENT_DISPATCHER_OK" | tee -a "$LOG"
