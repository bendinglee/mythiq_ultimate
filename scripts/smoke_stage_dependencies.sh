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
  }' > "$tmp/run.json"

PROJECT_ID="$("$PY" - "$tmp/run.json" <<'PY'
import json, sys
from pathlib import Path
j = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(j["project_id"])
PY
)"

code="$(curl -sS -o "$tmp/rerun.json" -w "%{http_code}" \
  "$BASE/v1/project/rerun_stage" \
  -H 'Content-Type: application/json' \
  -d "{
    \"project_id\":\"${PROJECT_ID}\",
    \"stage\":\"animation\",
    \"prompt\":\"Build a cinematic mythic trailer concept\",
    \"goal\":\"create a multi-stage project pipeline\",
    \"improve\": true
  }")"

"$PY" - "$code" "$tmp/rerun.json" <<'PY'
import json
import sys
from pathlib import Path

status_code = int(sys.argv[1])
body = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))

assert status_code in (403, 409), (status_code, body)
detail = body.get("detail", "")
assert "missing stage dependencies" in detail or "requires approval" in detail, body

print("SMOKE_STAGE_DEPS_OK", status_code)
PY
