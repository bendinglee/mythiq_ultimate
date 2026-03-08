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

curl -fsS "$BASE/v1/project/export?project_id=${PROJECT_ID}" > "$tmp/export.json"

"$PY" - "$tmp/export.json" <<'PY'
import json
import sys
from pathlib import Path

j = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert j["ok"] is True, j
assert j["project_id"].startswith("p_"), j
assert j["manifest_path"].endswith("manifest.json"), j
assert j["summary_path"].endswith("README.md"), j
manifest = j["manifest"]
assert manifest["project_id"] == j["project_id"], j
assert len(manifest.get("stages", [])) >= 1, j
print("SMOKE_PROJECT_EXPORT_OK", j["project_id"])
PY
