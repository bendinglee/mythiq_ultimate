#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
BASE="${BASE:-http://127.0.0.1:7777}"

test -x "$PY" || { echo "❌ missing venv python: $PY"; exit 1; }

tmp1="$(mktemp)"
tmp2="$(mktemp)"
trap 'rm -f "$tmp1" "$tmp2"' EXIT

curl -fsS "$BASE/v1/generate/code" \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt":"Write a tiny Python CLI that prints Hello, Mythiq and exits 0.",
    "goal":"return usable code output",
    "improve": true
  }' > "$tmp1"

curl -fsS "$BASE/v1/generate/docs" \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt":"Create a concise product strategy memo for a local-first AI platform.",
    "goal":"return usable markdown docs output",
    "improve": true
  }' > "$tmp2"

"$PY" - "$tmp1" "$tmp2" <<'PY'
import json, sys
from pathlib import Path

code = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
docs = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))

assert code["feature"] == "code", code
assert code["type"] == "python", code
assert isinstance(code.get("files"), list) and len(code["files"]) >= 3, code

assert docs["feature"] == "docs", docs
assert docs["type"] == "markdown", docs
assert isinstance(docs.get("files"), list) and len(docs["files"]) >= 3, docs

print("SMOKE_GENERATE_GENERIC_OK", code["feature"], docs["feature"])
PY
