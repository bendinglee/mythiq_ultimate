#!/usr/bin/env bash
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:7777}"

python3 -m py_compile api/app/main.py >/dev/null

curl -fsS "$BASE/readyz" >/dev/null
curl -fsS "$BASE/openapi.json" >/dev/null
curl -fsS "$BASE/v1/schema/health" >/dev/null

# quick sanity: ensure ab_pick response has picked in schema
curl -fsS "$BASE/openapi.json" | python3 -c '
import json,sys
j=json.load(sys.stdin)
ab=j["paths"]["/v1/ab_pick"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]
if "$ref" in ab:
    ab=j["components"]["schemas"][ab["$ref"].split("/")[-1]]
props=set((ab.get("properties") or {}).keys())
assert "picked" in props, f"missing picked in ab_pick schema: {sorted(props)}"
print("SMOKE_OK")
'


# decided-path contract: after decision, response must be idempotent true + inserted false
DECIDE="decide_smoke_group"
for i in 1 2 3; do
  curl -fsS "$BASE/v1/ab_pick" \
    -H "content-type: application/json" \
    -d '{"ab_group":"'"$DECIDE"'","winner":"A","user_rating":5,"voter_id":"sm'"$i"'"}' >/dev/null
done

curl -fsS "$BASE/v1/ab_pick" \
  -H "content-type: application/json" \
  -d '{"ab_group":"'"$DECIDE"'","winner":"B","user_rating":3,"voter_id":"sm4"}' \
| python3 -c '
import json,sys
j=json.load(sys.stdin)
assert j.get("decided") is True
assert j.get("idempotent") is True
assert j.get("inserted") is False
print("DECIDE_OK")
'


# outcomes contract: POST /v1/outcome inserts and export returns the row
curl -fsS "$BASE/v1/outcome" \
  -H "content-type: application/json" \
  -d '{"feature":"ab_pick","key":"smoke:decide_check:A","reward":1.0,"meta":{"smoke":true}}' >/dev/null

curl -fsS "$BASE/v1/outcomes/export?limit=5" | python3 -c '
import sys
txt=sys.stdin.read()
assert "ts,feature,key,reward,meta_json" in txt
assert "smoke:decide_check:A" in txt
print("OUTCOME_OK")
'
