#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
BASE="${BASE:-http://127.0.0.1:7777}"

curl -fsS "$BASE/readyz" >/dev/null

tmp="/tmp/mythiq_smoke_openapi.$$"
mkdir -p "$tmp"
trap 'rm -rf "$tmp" >/dev/null 2>&1 || true' EXIT

fail() {
  echo "❌ $*" >&2
  echo "---- uvicorn tail ----" >&2
  tail -n 200 "$ROOT/logs/uvicorn.log" >&2 || true
  exit 1
}

curl_to() {
  local url="$1" out="$2" hdr="$3" meta="$4"
  curl -sS -o "$out" -D "$hdr" -w 'status=%{http_code} size=%{size_download}\n' "$url" >"$meta"
}

check_ok() {
  local name="$1" url="$2" out="$3" hdr="$4" meta="$5" expect_ct="$6"

  curl_to "$url" "$out" "$hdr" "$meta"
  local STATUS SIZE
  STATUS="$(sed -n 's/.*status=\([0-9][0-9][0-9]\).*/\1/p' "$meta" | head -n1 || true)"
  SIZE="$(sed -n 's/.*size=\([0-9][0-9]*\).*/\1/p' "$meta" | head -n1 || true)"

  if test "${STATUS:-}" != "200" || test "${SIZE:-0}" = "0"; then
    sleep 0.4
    curl_to "$url" "$out" "$hdr" "$meta"
    STATUS="$(sed -n 's/.*status=\([0-9][0-9][0-9]\).*/\1/p' "$meta" | head -n1 || true)"
    SIZE="$(sed -n 's/.*size=\([0-9][0-9]*\).*/\1/p' "$meta" | head -n1 || true)"
  fi

  if test "${STATUS:-}" != "200"; then
    echo "❌ $name status=$STATUS url=$url" >&2
    echo "---- META ----" >&2; cat "$meta" >&2 || true
    echo "---- HEADERS ----" >&2; sed -n '1,120p' "$hdr" >&2 || true
    echo "---- BODY BYTES ----" >&2; wc -c "$out" >&2 || true
    echo "---- BODY HEAD(200) ----" >&2; head -c 200 "$out" >&2 || true; echo >&2
    fail "$name non-200"
  fi

  if test "${SIZE:-0}" = "0"; then
    echo "❌ $name empty body (status=200) url=$url" >&2
    echo "---- HEADERS ----" >&2; sed -n '1,120p' "$hdr" >&2 || true
    fail "$name empty body"
  fi

  if ! LC_ALL=C tr -d '[:space:]' <"$out" | grep -q .; then
    echo "❌ $name whitespace-only body (status=200) url=$url" >&2
    echo "---- BODY HEAD(200) ----" >&2; head -c 200 "$out" >&2 || true; echo >&2
    fail "$name whitespace body"
  fi

  local CT
  CT="$(sed -n 's/^[Cc][Oo][Nn][Tt][Ee][Nn][Tt]-[Tt][Yy][Pp][Ee]:[[:space:]]*//p' "$hdr" | head -n1 | tr -d '\r' || true)"
  if test -n "${expect_ct:-}"; then
    case "$CT" in
      ${expect_ct}*) : ;;
      *)
        echo "❌ $name unexpected content-type='$CT' expected prefix='${expect_ct}' url=$url" >&2
        echo "---- HEADERS ----" >&2; sed -n '1,120p' "$hdr" >&2 || true
        echo "---- BODY HEAD(200) ----" >&2; head -c 200 "$out" >&2 || true; echo >&2
        fail "$name bad content-type"
        ;;
    esac
  fi
  # If we expect JSON, ensure it starts with { or [
  if test -n "${expect_ct:-}" && printf "%s" "$expect_ct" | grep -q '^application/json'; then
    if ! head -c 1 "$out" | LC_ALL=C grep -q '[\{\[]'; then
      echo "❌ $name body is not JSON (first byte not '{' or '[') url=$url" >&2
      echo "---- HEADERS ----" >&2; sed -n '1,120p' "$hdr" >&2 || true
      echo "---- BODY HEAD(200) ----" >&2; head -c 200 "$out" >&2 || true; echo >&2
      fail "$name non-json body"
    fi
  fi

}

# compile
"$PY" -m py_compile "$ROOT/api/app/main.py" >/dev/null || fail "py_compile failed"

# openapi.json
check_ok "openapi.json" "$BASE/openapi.json" "$tmp/openapi.json" "$tmp/openapi.hdr" "$tmp/openapi.meta" "application/json"
MYTHIQ_JSON_PATH="$tmp/openapi.json" "$PY" - <<'PY'
import json, os
raw = open(os.environ["MYTHIQ_JSON_PATH"], "r", encoding="utf-8", errors="replace").read()
try:
    j = json.loads(raw)
except Exception as e:
    import sys
    print("❌ JSON parse failed:", repr(e), file=sys.stderr)
    print("---- RAW HEAD(200) ----", file=sys.stderr)
    print(raw[:200], file=sys.stderr)
    raise

assert ("openapi" in j) or ("swagger" in j), list(j.keys())
assert "paths" in j and isinstance(j["paths"], dict) and j["paths"], "missing paths"
PY

# outcomes/export
check_ok "outcomes/export" "$BASE/v1/outcomes/export?limit=5" "$tmp/outcomes.csv" "$tmp/outcomes.hdr" "$tmp/outcomes.meta" "text/csv"
head -n 1 "$tmp/outcomes.csv" | LC_ALL=C tr -d "\r\n" | grep -q "^ts," || fail "outcomes/export bad csv header"


# generations/export
check_ok "generations/export" "$BASE/v1/generations/export?limit=50" "$tmp/gens.csv" "$tmp/gens.hdr" "$tmp/gens.meta" "text/csv"
head -n 1 "$tmp/gens.csv" | LC_ALL=C tr -d "\r\n" | grep -q "^ts," || fail "generations/export bad csv header"


echo "SMOKE_OPENAPI_OK"
