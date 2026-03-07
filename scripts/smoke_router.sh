#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
BASE="${BASE:-http://127.0.0.1:7777}"

test -x "$PY" || { echo "❌ missing venv python: $PY"; exit 1; }

payload="$("$PY" - <<'PY'
import json
print(json.dumps({
    "prompt": "Fix this Python bug and add a unit test",
    "max_secondary": 1
}))
PY
)"

j="$(curl -fsS -X POST "$BASE/v1/route_v3" \
  -H 'Content-Type: application/json' \
  -d "$payload")"

"$PY" - <<PY
import json

j = json.loads('''$j''')
assert isinstance(j, dict), j
assert j.get("ok") is True, j
assert "feature" in j, j
assert j["feature"] in ("code", "text"), j
assert "confidence" in j, j
assert isinstance(j.get("scores"), dict), j

print("SMOKE_ROUTER_OK", j["feature"], j["confidence"])
PY
