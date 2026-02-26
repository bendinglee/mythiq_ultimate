#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
BASE="${BASE:-http://127.0.0.1:7777}"

# Do NOT start/stop server here; prepush owns lifecycle.
# Just ensure it is ready.
curl -fsS "$BASE/readyz" >/dev/null

G="ab_smoke_$(date +%s)"
PAT="$G"

curl -fsS "$BASE/v1/pattern/variant/set" -H "content-type: application/json" \
  -d '{"pattern_id":"'"$PAT"'","variant":"A","system_prompt":"SYS_A","prefix":"PRE_A"}' >/dev/null

curl -fsS "$BASE/v1/pattern/variant/set" -H "content-type: application/json" \
  -d '{"pattern_id":"'"$PAT"'","variant":"B","system_prompt":"SYS_B","prefix":"PRE_B"}' >/dev/null

for i in 1 2 3; do
  curl -fsS "$BASE/v1/pattern/render" -H "content-type: application/json" \
    -d '{"pattern_id":"'"$PAT"'","ab_group":"'"$G"'","prompt":"hello","winner":"A","user_rating":5,"voter_id":"p'"$i"'"}' >/dev/null
done

# If this curl fails, pipefail stops before python runs.
curl -fsS "$BASE/v1/pattern/render" -H "content-type: application/json" \
  -d '{"pattern_id":"'"$PAT"'","ab_group":"'"$G"'","prompt":"hello"}' \
| "$PY" - <<'PY'
import json,sys
raw = sys.stdin.read().strip()
if not raw:
    raise SystemExit("❌ empty response body from /v1/pattern/render")
j = json.loads(raw)
assert j["ok"] is True
assert j["decided"] is True
assert j["variant"] == "A"
assert "SYS_A" in j["rendered"]
assert "PRE_A" in j["rendered"]
print("SMOKE_OK")
PY
