#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# bring stack up (build if needed)
docker compose up -d --build

# wait for API to be stably ready (2 consecutive hits)
./scripts/wait_ready.sh "http://127.0.0.1:7777/readyz" 60 0.5

# run smoke
./scripts/smoke.sh
