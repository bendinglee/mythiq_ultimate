#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
BASE="${BASE:-http://127.0.0.1:7777}"

test -x "$PY" || { echo "❌ missing venv python: $PY"; exit 1; }

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

curl -fsS "$BASE/v1/execute_core" \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt":"Fix this Python bug and add a unit test",
    "goal":"reliably finish work",
    "mode":"project",
    "want":"code",
    "improve": true
  }' > "$tmp/execute_core.json"

"$PY" - "$tmp/execute_core.json" <<'PY'
import json
import sys
from pathlib import Path

j = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

assert "project_id" in j and j["project_id"].startswith("p_"), j
assert "run_id" in j and j["run_id"].startswith("r_"), j
assert j["route"]["feature"] in ("text", "code", "game", "image", "shorts", "docs", "animation"), j
assert j["plan"]["feature"] == j["result"]["feature"], j
assert isinstance(j["quality"]["score"], (int, float)), j
assert isinstance(j["metrics"]["latency_ms"], int), j

meta = j["result"]["meta"]
artifact = meta.get("artifact") or {}
assert artifact.get("artifact_type") == "code_patch", j
assert artifact.get("artifact_data", {}).get("language") == "python", j
assert len(artifact.get("artifact_data", {}).get("functions", [])) >= 1, j
assert artifact.get("next_stage_inputs", {}).get("code_summary"), j

reliability = j.get("reliability") or {}
assert isinstance(reliability.get("attempts"), int) and reliability["attempts"] >= 1, j
assert isinstance(reliability.get("fallback_used"), bool), j
assert reliability.get("final_feature") == j["result"]["feature"], j
assert isinstance(reliability.get("tried_features"), list) and len(reliability["tried_features"]) >= 1, j

print("SMOKE_EXECUTE_CORE_OK", j["result"]["feature"], j["quality"]["score"])
PY
