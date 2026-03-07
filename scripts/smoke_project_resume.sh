#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
BASE="${BASE:-http://127.0.0.1:7777}"

test -x "$PY" || { echo "❌ missing venv python: $PY"; exit 1; }

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# 1) create project
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

# 2) status before approval
curl -fsS "$BASE/v1/project/status?project_id=${PROJECT_ID}" > "$tmp/status_before.json"

# 3) approve image stage
curl -fsS "$BASE/v1/project/approve_stage" \
  -H 'Content-Type: application/json' \
  -d "{
    \"project_id\":\"${PROJECT_ID}\",
    \"stage\":\"image\"
  }" > "$tmp/approve.json"

# 4) rerun image stage
code="$(curl -sS -o "$tmp/rerun.json" -w "%{http_code}" \
  "$BASE/v1/project/rerun_stage" \
  -H 'Content-Type: application/json' \
  -d "{
    \"project_id\":\"${PROJECT_ID}\",
    \"stage\":\"image\",
    \"prompt\":\"Build a cinematic mythic trailer concept\",
    \"goal\":\"create a multi-stage project pipeline\",
    \"improve\": true
  }")"

if [ "$code" != "200" ]; then
  echo "❌ rerun_stage returned HTTP $code"
  echo "---- body ----"
  cat "$tmp/rerun.json" || true
  exit 1
fi

# 5) verify
"$PY" - "$tmp/status_before.json" "$tmp/approve.json" "$tmp/rerun.json" <<'PY'
import json
import sys
from pathlib import Path

status = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
approve = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
rerun = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))

assert status["ok"] is True, status
assert status["project_id"].startswith("p_"), status
assert "docs" in status["stages_present"], status
assert status["blocked_stage"] == "image", status

assert approve["ok"] in (True, False), approve
assert approve["project_id"] == status["project_id"], approve
assert approve["approved_stage"] == "image", approve
assert "image" in approve.get("approved_stages", []), approve

assert rerun["ok"] in (True, False), rerun
assert rerun["project_id"] == status["project_id"], rerun
assert rerun["stage"] == "image", rerun
assert rerun["rerun"] is True, rerun
assert rerun["result"]["feature"] == "image", rerun
assert len(rerun["result"].get("files", [])) >= 2, rerun

print("SMOKE_PROJECT_RESUME_OK", rerun["project_id"], rerun["stage"])
PY
