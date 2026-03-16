#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PY="./.venv/bin/python"
RUN_ID="sidemen_house_party_1773597868"
LOG="/tmp/smoke_moment_package.log"

"$PY" shortforge/viral_engine/run_moment_project.py --run-id "$RUN_ID" --package > "$LOG" 2>&1

ZIP="shortforge/projects/$RUN_ID/exports/${RUN_ID}_moment_bundle.zip"
test -f "$ZIP"
unzip -l "$ZIP" >> "$LOG" 2>&1

grep -q "packaged:" "$LOG"
echo "SMOKE_MOMENT_PACKAGE_OK" | tee -a "$LOG"
