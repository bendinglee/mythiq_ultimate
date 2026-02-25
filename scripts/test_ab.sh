#!/usr/bin/env bash
set -euo pipefail

API="${API:-http://127.0.0.1:7777}"
GROUP="${1:-test_group_$(date +%s)}"



# prefer python3 on macOS
PY="${PY:-python3}"

# 1) first vote
curl -fsS -H 'Content-Type: application/json' \
  -d '{"ab_group":"'"$GROUP"'","winner":"A","user_rating":5,"voter_id":"t1"}' \
  "$API/v1/ab_pick" >/dev/null

# 2) drive to early-stop (3-0)
for i in 2 3; do
  curl -fsS -H 'Content-Type: application/json' \
    -d '{"ab_group":"'"$GROUP"'","winner":"A","user_rating":5,"voter_id":"t'$i'"}' \
    "$API/v1/ab_pick" >/dev/null
done

# 3) final check
out="$(curl -fsS -H 'Content-Type: application/json' \
  -d '{"ab_group":"'"$GROUP"'","winner":"A","user_rating":5,"voter_id":"t4"}' \
  "$API/v1/ab_pick")"

echo "$out" | "$PY" -m json.tool

"$PY" - <<PY
import json
d=json.loads("""$out""")
assert d["ok"] is True
assert d["decided"] is True
assert d["winner"] == "A"
print("✅ AB decision test passed")
PY
