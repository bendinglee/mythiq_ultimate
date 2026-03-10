#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PORT="${MYTHIQ_CANVAS_PORT:-8099}"
lsof -ti tcp:$PORT | xargs kill -9 2>/dev/null || true
sleep 1

MYTHIQ_CANVAS_PORT="$PORT" python3 command_canvas/server.py
