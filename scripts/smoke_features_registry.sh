#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
BASE="${BASE:-http://127.0.0.1:7777}"

test -x "$PY" || { echo "❌ missing venv python: $PY"; exit 1; }

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

curl -fsS "$BASE/v1/features" > "$tmp"

"$PY" - "$tmp" <<'PY'
import json, sys
from pathlib import Path

j = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

assert j["ok"] is True, j
assert int(j["count"]) >= 7, j

features = j.get("features") or []
names = {x.get("feature") for x in features}
paths = {x.get("generate_path") for x in features}

required_names = {"text", "code", "docs", "shorts", "image", "game", "animation"}
required_paths = {
    "/v1/text/generate",
    "/v1/code/generate",
    "/v1/docs/generate",
    "/v1/shorts/generate",
    "/v1/image/generate",
    "/v1/game/generate",
    "/v1/animation/generate",
}

assert required_names.issubset(names), j
assert required_paths.issubset(paths), j

print("SMOKE_FEATURES_REGISTRY_OK", len(features))
PY
