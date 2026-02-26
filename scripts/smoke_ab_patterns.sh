#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
BASE="${BASE:-http://127.0.0.1:7777}"

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

tmp_body="/tmp/mythiq_render_body.$$"
tmp_hdr="/tmp/mythiq_render_hdr.$$"
tmp_status="/tmp/mythiq_render_status.$$"
rm -f "$tmp_body" "$tmp_hdr" "$tmp_status" || true

call_render() {
  curl -sS --fail-with-body \
    -H "content-type: application/json" \
    -d '{"pattern_id":"'"$PAT"'","ab_group":"'"$G"'","prompt":"hello"}' \
    "$BASE/v1/pattern/render" \
    -o "$tmp_body" \
    -D "$tmp_hdr" \
    -w 'status=%{http_code}\n' >"$tmp_status" || true
}

call_render
STATUS="$(sed -n 's/^status=//p' "$tmp_status" 2>/dev/null || true)"

if test "${STATUS:-}" != "200"; then
  sleep 0.4
  call_render
  STATUS="$(sed -n 's/^status=//p' "$tmp_status" 2>/dev/null || true)"
fi

if test "${STATUS:-}" != "200"; then
  echo "❌ /v1/pattern/render status=$STATUS" >&2
  echo "---- HEADERS ----" >&2
  sed -n '1,120p' "$tmp_hdr" >&2 || true
  echo "---- BODY (bytes) ----" >&2
  wc -c "$tmp_body" >&2 || true
  echo "---- BODY (first 200 bytes) ----" >&2
  head -c 200 "$tmp_body" >&2 || true
  echo >&2
  echo "---- uvicorn tail ----" >&2
  tail -n 200 "$ROOT/logs/uvicorn.log" >&2 || true
  exit 1
fi

if ! LC_ALL=C tr -d '[:space:]' <"$tmp_body" | grep -q .; then
  echo "❌ /v1/pattern/render returned empty/whitespace body (status=200)" >&2
  echo "---- HEADERS ----" >&2
  sed -n '1,120p' "$tmp_hdr" >&2 || true
  echo "---- uvicorn tail ----" >&2
  tail -n 200 "$ROOT/logs/uvicorn.log" >&2 || true
  exit 1
fi

MYTHIQ_BODY_PATH="$tmp_body" "$PY" - <<'PY'
import json, os
path = os.environ["MYTHIQ_BODY_PATH"]
raw = open(path, "r", encoding="utf-8", errors="replace").read()
j = json.loads(raw)
assert j["ok"] is True
assert j["decided"] is True
assert j["variant"] == "A"
assert "SYS_A" in j["rendered"]
assert "PRE_A" in j["rendered"]
print("SMOKE_OK")
PY

rm -f "$tmp_body" "$tmp_hdr" "$tmp_status" || true
