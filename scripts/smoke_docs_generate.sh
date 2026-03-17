#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
BASE="${BASE:-http://127.0.0.1:7777}"

test -x "$PY" || { echo "❌ missing venv python: $PY"; exit 1; }

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

curl -fsS "$BASE/v1/docs/generate" \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt":"Create a concise product strategy memo for a local-first AI platform.",
    "goal":"return usable markdown docs output",
    "improve": true
  }' > "$tmp"

"$PY" - "$tmp" <<'PY'
import json, sys
from pathlib import Path

j = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

assert j["ok"] in (True, False), j
assert j.get("feature") == "docs", j
assert j.get("type") == "markdown", j

content = j.get("content", "")
files = j.get("files", [])

assert "# Document Blueprint" in content, j
assert isinstance(files, list) and len(files) >= 3, j

for fp in files:
    assert Path(fp).exists(), fp

bundle = (j.get("meta") or {}).get("bundle") or {}
assert bundle.get("root"), j
assert int(bundle.get("file_count", 0)) >= 3, j

print("SMOKE_DOCS_GENERATE_OK", j.get("feature"), j.get("type"), len(files))
PY
