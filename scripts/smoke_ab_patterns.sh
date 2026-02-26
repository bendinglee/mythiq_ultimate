#!/usr/bin/env bash
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:7777}"

./scripts/run_stable.sh start >/dev/null

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

curl -fsS "$BASE/v1/pattern/render" -H "content-type: application/json" \
  -d '{"pattern_id":"'"$PAT"'","ab_group":"'"$G"'","prompt":"hello"}' \
| python3 - <<'PY'
import json,sys
j=json.load(sys.stdin)
assert j["ok"] is True
assert j["decided"] is True
assert j["variant"] == "A"
assert "SYS_A" in j["rendered"]
assert "PRE_A" in j["rendered"]
print("SMOKE_OK")
PY
