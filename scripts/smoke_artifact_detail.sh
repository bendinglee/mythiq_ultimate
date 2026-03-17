#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
BASE="${BASE:-http://127.0.0.1:7777}"

test -x "$PY" || { echo "❌ missing venv python: $PY"; exit 1; }

tmp1="$(mktemp)"
tmp2="$(mktemp)"
trap 'rm -f "$tmp1" "$tmp2"' EXIT

curl -fsS "$BASE/v1/artifacts?limit=20" > "$tmp1"

ARTIFACT_ID="$("$PY" - "$tmp1" <<'PY'
import json, sys
from pathlib import Path
j = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
arts = j.get("artifacts") or []
assert arts, j
print(arts[0]["artifact_id"])
PY
)"

curl -fsS "$BASE/v1/artifacts/detail?artifact_id=$ARTIFACT_ID" > "$tmp2"

"$PY" - "$tmp2" "$ARTIFACT_ID" <<'PY'
import json, sys
from pathlib import Path

j = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
artifact_id = sys.argv[2]

assert j["ok"] is True, j
row = j["artifact"]
assert row["artifact_id"] == artifact_id, j
assert row.get("root"), j
assert isinstance(row.get("files"), list), j

print("SMOKE_ARTIFACT_DETAIL_OK", artifact_id)
PY
