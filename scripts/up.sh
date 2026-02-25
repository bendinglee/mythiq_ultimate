#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

docker compose up -d

./scripts/wait_ready.sh "http://127.0.0.1:7777/readyz" 60 0.5
./scripts/pull_models.sh "llama3.2:3b"
./scripts/smoke.sh

echo "UI:  http://127.0.0.1:3000"
echo "API: http://127.0.0.1:7777"
