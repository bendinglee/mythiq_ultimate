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
  -d '{
    "prompt":"Write a tiny Python CLI that prints Hello, Mythiq and exits 0.",
    "goal":"return usable code output",
    "improve": true
  }' > "$tmp"

"$PY" - "$tmp" <<'PY'
import json, sys
from pathlib import Path

j = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

assert j["ok"] in (True, False), j
assert j.get("feature") == "code", j
assert isinstance(j.get("type"), str) and j["type"], j

content = j.get("content", "")
files = j.get("files", [])

assert content, j
assert isinstance(files, list) and len(files) >= 3, j

for fp in files:
    assert Path(fp).exists(), fp

text = content.lower()
assert "def solve" in text or "print(" in text or "hello" in text, j

bundle = (j.get("meta") or {}).get("bundle") or {}
assert bundle.get("root"), j
assert int(bundle.get("file_count", 0)) >= 3, j

print("SMOKE_CODE_GENERATE_OK", j.get("feature"), j.get("type"), len(files))
PY
