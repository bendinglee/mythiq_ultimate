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
    "prompt":"Build a cinematic mythic trailer concept",
    "goal":"create a multi-stage project pipeline",
    "mode":"project",
    "improve": true
  }' > "$tmp/project.json"

PROJECT_ID="$("$PY" - "$tmp/project.json" <<'PY'
import json, sys
from pathlib import Path
j = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(j["project_id"])
PY
)"

curl -fsS "$BASE/v1/project/status?project_id=${PROJECT_ID}" > "$tmp/status_before.json"

curl -fsS -X POST "$BASE/v1/project/approve_stage" \
  -H 'Content-Type: application/json' \
  -d "{
    \"project_id\":\"${PROJECT_ID}\",
    \"stage\":\"image\"
  }" > "$tmp/approve.json"

curl -fsS "$BASE/v1/project/status?project_id=${PROJECT_ID}" > "$tmp/status_after.json"

"$PY" - "$tmp/status_before.json" "$tmp/approve.json" "$tmp/status_after.json" <<'PY'
import json
import sys
from pathlib import Path

before = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
approve = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
after = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))

assert before["ok"] is True, before
assert before["blocked_stage"] == "image", before
assert before["gates"]["image"]["requires_approval"] is True, before
assert before["gates"]["image"]["approved"] is False, before

assert approve["ok"] is True, approve
assert approve["approved_stage"] == "image", approve

assert after["ok"] is True, after
assert "image" in after["approved_stages"], after
assert after["gates"]["image"]["approved"] is True, after

print("SMOKE_PROJECT_APPROVAL_OK", approve["project_id"], approve["approved_stage"])
PY
