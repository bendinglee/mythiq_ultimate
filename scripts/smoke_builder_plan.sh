#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
BASE="${BASE:-http://127.0.0.1:7777}"

test -x "$PY" || { echo "❌ missing venv python: $PY"; exit 1; }

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

curl -fsS "$BASE/v1/builder/plan" \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt":"Build a browser strategy game with progression and save slots",
    "goal":"turn prompts into real buildable projects automatically",
    "mode":"project",
    "improve": true
  }' > "$tmp/builder.json"

"$PY" - "$tmp/builder.json" <<'PY'
import json
import sys
from pathlib import Path

j = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

assert j["ok"] is True, j
assert j["builder_target"] in ("game", "app", "media", "automation"), j
assert isinstance(j["project_spec"], dict), j
assert isinstance(j["project_spec"].get("stages"), list) and len(j["project_spec"]["stages"]) >= 2, j
assert isinstance(j["plan"], dict), j
assert j["plan"]["feature"] == "builder", j
assert isinstance(j["blueprint"], str) and "Builder Engine Blueprint" in j["blueprint"], j

print("SMOKE_BUILDER_PLAN_OK", j["builder_target"], len(j["project_spec"]["stages"]))
PY
