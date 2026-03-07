#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
BASE="${BASE:-http://127.0.0.1:7777}"

test -x "$PY" || { echo "❌ missing venv python: $PY"; exit 1; }

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

curl -fsS "$BASE/v1/execute_core" \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt":"Create a YouTube thumbnail image for a dramatic sci-fi story",
    "goal":"generate a strong visual concept",
    "mode":"project",
    "want":"image",
    "constraints":{"style":"cinematic illustrated"},
    "improve": true
  }' > "$tmp/image.json"

curl -fsS "$BASE/v1/execute_core" \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt":"Turn a long history topic into a viral short with a strong hook",
    "goal":"generate a short-form edit blueprint",
    "mode":"project",
    "want":"shorts",
    "improve": true
  }' > "$tmp/shorts.json"

"$PY" - "$tmp/image.json" "$tmp/shorts.json" <<'PY'
import json
import sys
from pathlib import Path

img = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
sho = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))

assert img["ok"] is True, img
assert img["route"]["feature"] == "image", img
assert "Image Generation Package" in img["result"]["content"], img

assert sho["ok"] is True, sho
assert sho["route"]["feature"] == "shorts", sho
assert "Shorts Blueprint" in sho["result"]["content"], sho

print("SMOKE_MULTIMODAL_CORE_OK", img["route"]["feature"], sho["route"]["feature"])
PY
