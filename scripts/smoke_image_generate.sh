#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
BASE="${BASE:-http://127.0.0.1:7777}"

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

curl -fsS "$BASE/v1/image/generate" \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt":"cinematic futuristic city skyline at sunset",
    "goal":"image concept",
    "improve":true
  }' > "$tmp"

"$PY" - "$tmp" <<'PY'
import json, sys
from pathlib import Path

j = json.loads(Path(sys.argv[1]).read_text())

assert j["feature"] == "image"
assert isinstance(j["files"], list)
assert len(j["files"]) >= 3

for f in j["files"]:
    assert Path(f).exists()

print("SMOKE_IMAGE_GENERATE_OK", len(j["files"]))
PY
