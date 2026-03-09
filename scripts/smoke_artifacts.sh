#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
BASE="${BASE:-http://127.0.0.1:7777}"

test -x "$PY" || { echo "❌ missing venv python: $PY"; exit 1; }

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

curl -fsS "$BASE/v1/artifacts?limit=100" > "$tmp"

"$PY" - "$tmp" <<'PY'
import json, sys
from pathlib import Path

j = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

assert j["ok"] is True, j
assert isinstance(j.get("artifacts"), list), j
assert len(j["artifacts"]) > 0, j

known = {"text", "code", "docs", "shorts", "image", "game", "animation"}
features = {x.get("feature") for x in j["artifacts"]}

assert features & known, j

for row in j["artifacts"][:10]:
    assert row.get("artifact_id"), row
    assert row.get("root"), row
    assert isinstance(row.get("files"), list), row

print("SMOKE_ARTIFACTS_OK", len(j["artifacts"]), sorted(features & known))
PY
