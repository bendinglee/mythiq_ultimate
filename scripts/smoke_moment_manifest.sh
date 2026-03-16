#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PY="./.venv/bin/python"
RUN_ID="sidemen_house_party_1773597868"
LOG="/tmp/smoke_moment_manifest.log"

echo "PY=$PY" > "$LOG"
"$PY" -V >> "$LOG" 2>&1

"$PY" shortforge/viral_engine/write_moment_manifest.py --run-id "$RUN_ID" >> "$LOG" 2>&1
"$PY" shortforge/viral_engine/validate_moment_manifest.py --run-id "$RUN_ID" >> "$LOG" 2>&1

echo "SMOKE_MOMENT_MANIFEST_OK" | tee -a "$LOG"
