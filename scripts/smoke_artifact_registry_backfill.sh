#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
BASE="${BASE:-http://127.0.0.1:7777}"

test -x "$PY" || { echo "❌ missing venv python: $PY"; exit 1; }

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

curl -fsS "$BASE/v1/code/generate" \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Write a tiny Python function that returns 7.","goal":"register artifact","improve":true}' >/dev/null

curl -fsS "$BASE/v1/artifacts?limit=20" > "$tmp"

"$PY" - "$tmp" <<'PY'
import json, sys
from pathlib import Path

j = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert j["ok"] is True, j
arts = j["artifacts"]
assert isinstance(arts, list) and arts, j
assert any(x.get("source") == "registry" for x in arts), j
print("SMOKE_ARTIFACT_REGISTRY_OK", len(arts))
PY
