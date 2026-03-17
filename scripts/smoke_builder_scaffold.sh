#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
BASE="${BASE:-http://127.0.0.1:7777}"

test -x "$PY" || { echo "❌ missing venv python: $PY"; exit 1; }

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

curl -fsS "$BASE/v1/builder/run" \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt":"Build a browser strategy game with progression and save slots",
    "goal":"turn prompts into real buildable projects automatically",
    "mode":"project",
    "improve": true
  }' > "$tmp"

"$PY" - "$tmp" <<'PY'
import json, sys
from pathlib import Path

j = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

assert j["ok"] in (True, False), j
assert j["builder_target"] == "game", j

scaffold = j.get("scaffold") or {}
assert scaffold.get("root"), j
assert scaffold.get("manifest_path"), j
assert int(scaffold.get("file_count", 0)) >= 4, j
assert isinstance(scaffold.get("files"), list) and len(scaffold["files"]) >= 4, j

for fp in scaffold["files"]:
    assert Path(fp).exists(), fp

assert Path(scaffold["manifest_path"]).exists(), scaffold

print("SMOKE_BUILDER_SCAFFOLD_OK", j["builder_target"], scaffold["file_count"])
PY
