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

curl -fsS "$BASE/v1/project/export_zip?project_id=${PROJECT_ID}" > "$tmp/zip.json"

"$PY" - "$tmp/zip.json" <<'PY'
import json
import sys
from pathlib import Path

j = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert j["ok"] is True, j
assert j["project_id"].startswith("p_"), j
assert j["zip_path"].endswith(".zip"), j
assert int(j["size_bytes"]) > 0, j
assert Path(j["zip_path"]).exists(), j
print("SMOKE_PROJECT_ZIP_OK", j["project_id"])
PY
