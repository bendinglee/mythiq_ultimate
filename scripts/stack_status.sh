#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== docker context =="
docker context show || true

echo
echo "== compose ps =="
docker compose ps || true

echo
echo "== health checks =="
echo -n "API /readyz: " ; (curl -fsS -m 1 http://127.0.0.1:7777/readyz >/dev/null && echo OK) || echo FAIL
echo -n "Qdrant /collections: " ; (curl -sS -m 1 http://127.0.0.1:6333/collections >/dev/null && echo OK) || echo FAIL
echo -n "Ollama /api/tags: " ; (curl -sS -m 1 http://127.0.0.1:11434/api/tags >/dev/null && echo OK) || echo FAIL

echo
echo "== recent logs (api/qdrant/ollama) =="
docker compose logs --tail=80 api qdrant ollama 2>/dev/null || true
