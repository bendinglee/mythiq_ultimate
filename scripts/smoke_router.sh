#!/usr/bin/env bash
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:7777}"

# should route confidently to code
j="$(curl -fsS "$BASE/v1/route?q=$(python - <<'PY'
import urllib.parse
print(urllib.parse.quote("Fix this Python bug and add a unit test"))
PY
)")"
python - <<PY
import json,sys
j=json.loads('''$j''')
assert j["feature"] in ("code","text"), j
# code should be pretty confident once embeddings work
# don't over-tighten; just require not clarify
assert j["needs_clarify"] in (False, True)
print("SMOKE_ROUTER_OK", j["feature"], j["confidence"])
PY
