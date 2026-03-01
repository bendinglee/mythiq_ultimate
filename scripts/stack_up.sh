#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

CTX="${DOCKER_CONTEXT:-desktop-linux}"
docker context use "$CTX" >/dev/null 2>&1 || true

# Start Docker Desktop if daemon not responding
if ! docker version >/dev/null 2>&1; then
  open -a Docker || true
fi

# Wait for daemon
for i in $(seq 1 180); do
  docker version >/dev/null 2>&1 && break
  sleep 1
done

docker version >/dev/null 2>&1 || { echo "❌ Docker daemon not reachable"; exit 1; }

docker compose up -d

# Wait for Qdrant
for i in $(seq 1 120); do
  curl -sS -m 1 http://127.0.0.1:6333/collections >/dev/null 2>&1 && { echo "QDRANT_OK"; break; }
  sleep 0.5
done

# Wait for Ollama
for i in $(seq 1 120); do
  curl -sS -m 1 http://127.0.0.1:11434/api/tags >/dev/null 2>&1 && { echo "OLLAMA_OK"; break; }
  sleep 0.5
done

# Wait for API
for i in $(seq 1 160); do
  curl -fsS -m 1 http://127.0.0.1:7777/readyz >/dev/null 2>&1 && { echo "API_OK"; break; }
  sleep 0.5
done

echo "✅ STACK_UP_OK"
