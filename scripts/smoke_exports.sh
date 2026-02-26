#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="${BASE:-http://127.0.0.1:7777}"

curl -fsS "$BASE/readyz" >/dev/null

# seed 2 rows to test ordering
curl -fsS -X POST "$BASE/v1/outcomes/seed?feature=ab_pick&key=smoke1&reward=1.0" >/dev/null
sleep 0.1
curl -fsS -X POST "$BASE/v1/outcomes/seed?feature=ab_pick&key=smoke2&reward=2.0" >/dev/null

curl -fsS -X POST "$BASE/v1/generations/seed?feature=gen&key=smoke1&prompt=p1&output=o1" >/dev/null
sleep 0.1
curl -fsS -X POST "$BASE/v1/generations/seed?feature=gen&key=smoke2&prompt=p2&output=o2" >/dev/null

# outcomes/export must be csv with correct header
OUT="/tmp/mythiq_outcomes.$$"
GEN="/tmp/mythiq_gens.$$"
trap 'rm -f "$OUT" "$GEN" >/dev/null 2>&1 || true' EXIT

curl -fsS "$BASE/v1/outcomes/export?limit=5" >"$OUT"
head -n 1 "$OUT" | LC_ALL=C tr -d "\r\n" | grep -q '^ts,feature,key,reward,meta_json$'
# newest should appear first (smoke2 above smoke1)
awk -F, 'NR==2{print $3} NR==3{print $3}' "$OUT" | tr '\n' ' ' | grep -q 'smoke2 smoke1'

curl -fsS "$BASE/v1/generations/export?limit=5" >"$GEN"
head -n 1 "$GEN" | LC_ALL=C tr -d "\r\n" | grep -q '^ts,feature,key,prompt,output,meta_json$'
awk -F, 'NR==2{print $3} NR==3{print $3}' "$GEN" | tr '\n' ' ' | grep -q 'smoke2 smoke1'

echo "SMOKE_EXPORTS_OK"
