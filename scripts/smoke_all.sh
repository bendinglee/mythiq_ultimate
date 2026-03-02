#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

./scripts/stack_up.sh >/dev/null

echo "== API =="
curl -fsS -m 2 http://127.0.0.1:7777/readyz | head -c 200; echo

echo "== index libs -> qdrant =="
./scripts/index_libs_qdrant.sh >/dev/null
echo "LIBS_INDEX_OK"

echo "== RAG smoke (qdrant search) =="
./scripts/smoke_rag.sh >/dev/null
echo "SMOKE_RAG_OK"

echo "✅ SMOKE_ALL_OK"
