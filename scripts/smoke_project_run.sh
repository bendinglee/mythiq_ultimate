#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
BASE="${BASE:-http://127.0.0.1:7777}"

test -x "$PY" || { echo "❌ missing venv python: $PY"; exit 1; }

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

curl -fsS "$BASE/v1/project/run" \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt":"Build a viral history short about an ancient empire",
    "goal":"produce a chain of outputs for a short-form content project",
    "mode":"project",
    "improve": true
  }' > "$tmp/project.json"

"$PY" - "$tmp/project.json" <<'PY'
import json
import sys
from pathlib import Path

j = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert j["ok"] in (True, False), j
assert j["project_id"].startswith("p_"), j
assert isinstance(j["stages"], list) and len(j["stages"]) >= 1, j
assert isinstance(j["final_summary"], str) and j["final_summary"], j
assert int(j["metrics"]["deliverable_count"]) >= 1, j

first = j["stages"][0]
assert first["stage"] == "docs", j
assert first["route"]["feature"] == "docs", j
assert first["result"]["feature"] == "docs", j

for stage in j["stages"]:
    meta = stage["result"]["meta"]
    artifact = meta.get("artifact") or {}
    assert artifact.get("artifact_type"), stage
    assert artifact.get("artifact_data"), stage
    assert artifact.get("next_stage_inputs"), stage

print("SMOKE_PROJECT_RUN_OK", len(j["stages"]), first["route"]["feature"])
PY
