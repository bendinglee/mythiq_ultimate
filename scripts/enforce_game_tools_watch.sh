#!/usr/bin/env bash
set -euo pipefail

# Canonical source (mythiq_ultimate)
ULT="$HOME/mythiq_ultimate"
CANON="$ULT/tools/canonical_game_tools"

# Target outputs (mythiq_10x)
OUT="$HOME/mythiq_10x/games/output"

LOG="$ULT/logs/enforce_game_tools.log"
SEEN="$ULT/.enforced_game_dirs.txt"

mkdir -p "$(dirname "$LOG")" "$OUT"
touch "$LOG" "$SEEN"

test -f "$CANON/ai_auto_pick.mjs"
test -f "$CANON/ai_save_variants.mjs"
test -f "$CANON/ai_gen_variants.mjs"

patch_one () {
  local d="$1"
  test -d "$d/tools" || return 0

  cp -f "$CANON/ai_auto_pick.mjs"     "$d/tools/ai_auto_pick.mjs"
  cp -f "$CANON/ai_save_variants.mjs" "$d/tools/ai_save_variants.mjs"
  cp -f "$CANON/ai_gen_variants.mjs"  "$d/tools/ai_gen_variants.mjs"

  if command -v node >/dev/null 2>&1; then
    node --check "$d/tools/ai_auto_pick.mjs"     >/dev/null 2>&1 || true
    node --check "$d/tools/ai_save_variants.mjs" >/dev/null 2>&1 || true
    node --check "$d/tools/ai_gen_variants.mjs"  >/dev/null 2>&1 || true
  fi

  local ts; ts="$(date '+%Y-%m-%d %H:%M:%S')"
  echo "[$ts] ✅ enforced $(basename "$d")" | tee -a "$LOG" >/dev/null
}

# Initial pass (existing dirs) + record seen (dedup)
for d in "$OUT"/*; do
  test -d "$d" || continue
  patch_one "$d" || true
  name="$(basename "$d")"
  grep -qxF "$name" "$SEEN" || echo "$name" >> "$SEEN"
done

# Continuous pass: also re-enforce existing dirs (in case generator overwrites tools)
while true; do
  for d in "$OUT"/*; do
    test -d "$d" || continue
    name="$(basename "$d")"
    if ! grep -qxF "$name" "$SEEN"; then
      echo "$name" >> "$SEEN"
    fi
    patch_one "$d" || true
  done
  sleep 0.5
done
