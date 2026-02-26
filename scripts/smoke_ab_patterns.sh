#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
BASE="${BASE:-http://127.0.0.1:7777}"
MAX_TIME="${MAX_TIME:-5}"

# Ensure server is ready (give it a moment even after readyz)
curl -fsS --max-time "$MAX_TIME" "$BASE/readyz" >/dev/null
sleep 0.2

G="ab_smoke_$(date +%s)"
PAT="$G"

curl -fsS --max-time "$MAX_TIME" "$BASE/v1/pattern/variant/set" -H "content-type: application/json" \
  -d '{"pattern_id":"'"$PAT"'","variant":"A","system_prompt":"SYS_A","prefix":"PRE_A"}' >/dev/null

curl -fsS --max-time "$MAX_TIME" "$BASE/v1/pattern/variant/set" -H "content-type: application/json" \
  -d '{"pattern_id":"'"$PAT"'","variant":"B","system_prompt":"SYS_B","prefix":"PRE_B"}' >/dev/null

for i in 1 2 3; do
  curl -fsS --max-time "$MAX_TIME" "$BASE/v1/pattern/render" -H "content-type: application/json" \
    -d '{"pattern_id":"'"$PAT"'","ab_group":"'"$G"'","prompt":"hello","winner":"A","user_rating":5,"voter_id":"p'"$i"'"}' >/dev/null
done

call_render() {
  curl -sS --max-time "$MAX_TIME" \
    -H "content-type: application/json" \
    -d '{"pattern_id":"'"$PAT"'","ab_group":"'"$G"'","prompt":"hello"}' \
    -o /tmp/mythiq_render_body.$$ \
    -w "status=%{http_code}\n" \
    "$BASE/v1/pattern/render" > /tmp/mythiq_render_status.$$ || true
}

call_render

STATUS="$(cat /tmp/mythiq_render_status.$$ | tr -d '\r' | sed -n 's/^status=//p')"
BODY="$(cat /tmp/mythiq_render_body.$$ || true)"

# Retry once if empty or non-200 (common race)
if test "${STATUS:-}" != "200" || test -z "${BODY:-}"; then
  sleep 0.4
  call_render
  STATUS="$(cat /tmp/mythiq_render_status.$$ | tr -d '\r' | sed -n 's/^status=//p')"
  BODY="$(cat /tmp/mythiq_render_body.$$ || true)"
fi

rm -f /tmp/mythiq_render_status.$$ /tmp/mythiq_render_body.$$ || true

if test "${STATUS:-}" != "200"; then
  echo "❌ /v1/pattern/render status=$STATUS" >&2
  echo "---- uvicorn tail ----" >&2
  tail -n 120 "$ROOT/logs/uvicorn.log" >&2 || true
  exit 1
fi

if test -z "${BODY:-}"; then
  echo "❌ empty response body from /v1/pattern/render (status=200)" >&2
  echo "---- uvicorn tail ----" >&2
  tail -n 120 "$ROOT/logs/uvicorn.log" >&2 || true
  exit 1
fi

printf '%s' "$BODY" | "$PY" - <<'PY'
import json,sys
raw = sys.stdin.read().strip()
j = json.loads(raw)
assert j["ok"] is True
assert j["decided"] is True
assert j["variant"] == "A"
assert "SYS_A" in j["rendered"]
assert "PRE_A" in j["rendered"]
print("SMOKE_OK")
PY
