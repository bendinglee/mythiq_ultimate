#!/usr/bin/env bash
set -x
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
BASE="${BASE:-http://127.0.0.1:7777}"

# Ensure server is up for smokes; always stop on exit
"$ROOT/scripts/run_stable.sh" start >/dev/null
trap '"$ROOT/scripts/run_stable.sh" stop >/dev/null 2>&1 || true' EXIT

# Optional: quick sanity
curl -fsS "$BASE/readyz" >/dev/null

# Run existing smokes (keep whatever you already had; add AB smoke too)
if test -x "$ROOT/scripts/smoke_openapi.sh"; then
  "$ROOT/scripts/smoke_openapi.sh" >/dev/null
fi

if test -x "$ROOT/scripts/smoke_ab_patterns.sh"; then
  "$ROOT/scripts/smoke_ab_patterns.sh" >/dev/null
fi
if test -x "$ROOT/scripts/index_libs_qdrant.sh"; then
  if curl -fsS http://127.0.0.1:6333/collections >/dev/null 2>&1; then
    "$ROOT/scripts/index_libs_qdrant.sh"
  else
    echo "⚠️ skipping qdrant indexing: Qdrant not reachable on 127.0.0.1:6333"
  fi
fi
test -x "$ROOT/scripts/smoke_router.sh"
"$ROOT/scripts/smoke_router.sh"
if test -x "$ROOT/scripts/smoke_execute_core.sh"; then
  "$ROOT/scripts/smoke_execute_core.sh" >/dev/null
fi

test -x "$ROOT/scripts/smoke_library_budget.sh"
"$ROOT/scripts/smoke_library_budget.sh"
