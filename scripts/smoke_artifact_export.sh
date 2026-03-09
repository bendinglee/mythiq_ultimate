#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
BASE="${BASE:-http://127.0.0.1:7777}"

test -x "$PY" || { echo "❌ missing venv python: $PY"; exit 1; }

tmp1="$(mktemp)"
tmp2="$(mktemp)"
trap 'rm -f "$tmp1" "$tmp2"' EXIT

curl -fsS "$BASE/v1/artifacts?limit=50" > "$tmp1"

ARTIFACT_ID="$("$PY" - "$tmp1" <<'PY'
import json, sys
from pathlib import Path

j = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
rows = j.get("artifacts") or []
assert rows, j
print(rows[0]["artifact_id"])
PY
)"

curl -fsS "$BASE/v1/artifacts/export_zip?artifact_id=$ARTIFACT_ID" > "$tmp2"

"$PY" - "$tmp2" <<'PY'
import json, sys
from pathlib import Path

j = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

assert j["ok"] is True, j
assert j.get("artifact_id"), j
assert j.get("zip_path"), j
assert j.get("download_path"), j
assert Path(j["zip_path"]).exists(), j

print("SMOKE_ARTIFACT_EXPORT_OK", j["artifact_id"])
PY
