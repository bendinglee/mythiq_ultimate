#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PY="./.venv/bin/python"
LOG="/tmp/smoke_moment_mode.log"

"$PY" shortforge/viral_engine/write_moment_manifest.py --run-id "sidemen_house_party_1773597868" > "$LOG" 2>&1
"$PY" shortforge/viral_engine/detect_moment_project_mode.py --run-id "sidemen_house_party_1773597868" >> "$LOG" 2>&1
"$PY" shortforge/viral_engine/detect_moment_project_mode.py --run-id "sidemen_scene_pipeline" >> "$LOG" 2>&1

grep -q "PROJECT_MODE moment_render_pipeline" "$LOG"
grep -q "PROJECT_MODE archive_only" "$LOG"

echo "SMOKE_MOMENT_MODE_OK" | tee -a "$LOG"
