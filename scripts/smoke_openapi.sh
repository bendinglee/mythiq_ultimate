#!/usr/bin/env bash
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:7777}"

python -m py_compile api/app/main.py >/dev/null

curl -fsS "$BASE/readyz" >/dev/null
curl -fsS "$BASE/openapi.json" >/dev/null

# quick sanity: ensure ab_pick response has picked in schema
curl -fsS "$BASE/openapi.json" | python -c '
import json,sys
j=json.load(sys.stdin)
ab=j["paths"]["/v1/ab_pick"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]
if "$ref" in ab:
    ab=j["components"]["schemas"][ab["$ref"].split("/")[-1]]
props=set((ab.get("properties") or {}).keys())
assert "picked" in props, f"missing picked in ab_pick schema: {sorted(props)}"
print("SMOKE_OK")
'
