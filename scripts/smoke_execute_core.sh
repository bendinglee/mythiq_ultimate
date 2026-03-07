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
    "constraints":{"style":"practical"},
    "improve": true
  }' > "$tmp/execute_core.json"

"$PY" - "$tmp/execute_core.json" <<'PY'
import json
import sys
from pathlib import Path

p = Path(sys.argv[1])
j = json.loads(p.read_text(encoding="utf-8"))

assert j["ok"] is True, j
assert "project_id" in j and j["project_id"].startswith("p_"), j
assert "run_id" in j and j["run_id"].startswith("r_"), j
assert j["route"]["feature"] in ("text", "code", "game"), j
assert j["plan"]["feature"] == j["route"]["feature"], j
assert j["result"]["feature"] == j["route"]["feature"], j
assert isinstance(j["quality"]["score"], (int, float)), j
assert isinstance(j["metrics"]["latency_ms"], int), j

print("SMOKE_EXECUTE_CORE_OK", j["route"]["feature"], j["quality"]["score"])
PY
