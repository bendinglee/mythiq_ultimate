#!/usr/bin/env bash
set -euo pipefail

MODEL="${1:-llama3.2:3b}"
CNAME="${OLLAMA_CONTAINER:-mythiq_ollama}"

if docker exec "$CNAME" sh -lc "ollama list" | tail -n +2 | sed 's/[[:space:]].*$//' | grep -Fxq "$MODEL"; then
  echo "✅ model already present: $MODEL"
  exit 0
fi

echo "⬇️ pulling model: $MODEL"
docker exec "$CNAME" sh -lc "ollama pull '$MODEL'"
