#!/usr/bin/env bash
set -euo pipefail

API="${API:-http://127.0.0.1:7777}"
UI="${UI:-http://127.0.0.1:3000}"

echo "API readyz:"
curl -fsS "$API/readyz" | python3 -m json.tool

echo "API health:"
curl -fsS "$API/health" | python3 -m json.tool

echo "UI:"
curl -fsS -I "$UI" | head -n 5

echo "OK"
