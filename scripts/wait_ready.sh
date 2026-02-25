#!/usr/bin/env bash
set -euo pipefail

URL="${1:-http://127.0.0.1:7777/readyz}"
N="${2:-60}"
SLEEP="${3:-0.5}"

ok=0
for _ in $(seq 1 "$N"); do
  if curl -fs "$URL" >/dev/null 2>&1; then
    ok=$((ok+1))
    if [ "$ok" -ge 2 ]; then
      echo "✅ ready (stable): $URL"
      exit 0
    fi
  else
    ok=0
  fi
  sleep "$SLEEP"
done

echo "❌ not ready (stable) after $N tries: $URL" >&2
exit 1
