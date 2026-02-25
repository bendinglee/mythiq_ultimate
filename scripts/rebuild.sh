#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# --- fail-fast guards ---
./scripts/verify_api.sh >/dev/null
python3 scripts/fix_route_indent.py api/app/main.py /v1/ab_pick >/dev/null
python3 -m py_compile api/app/main.py
# --- end guards ---

docker compose up -d --build --force-recreate --no-deps api ui

./scripts/wait_ready.sh "http://127.0.0.1:7777/readyz" 60 0.5
./scripts/test_ab.sh >/dev/null
./scripts/pull_models.sh "llama3.2:3b"
./scripts/smoke.sh

echo "UI:  http://127.0.0.1:3000"
echo "API: http://127.0.0.1:7777"
