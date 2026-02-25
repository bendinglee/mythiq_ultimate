#!/usr/bin/env bash
set -euo pipefail

# WAIT_FOR_READYZ
for i in $(seq 1 40); do
  if curl -fsS http://127.0.0.1:7777/readyz >/dev/null; then
    break
  fi
  sleep 0.5
done

curl -fsS http://127.0.0.1:7777/readyz | python3 -m json.tool
curl -fsS http://127.0.0.1:7777/health | python3 -m json.tool
curl -fsS http://127.0.0.1:7777/v1/run \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Write a 5-bullet plan for a tiny arcade game loop.","feature":"text","model":"llama3.2:3b"}' \
| python3 -m json.tool
