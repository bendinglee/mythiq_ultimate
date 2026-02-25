#!/usr/bin/env bash
set -euo pipefail

docker compose up -d --build --force-recreate

# wait for health
for i in {1..60}; do
  api="$(docker inspect --format='{{.State.Health.Status}}' mythiq_api 2>/dev/null || echo none)"
  ui="$(docker inspect --format='{{.State.Health.Status}}' mythiq_ui 2>/dev/null || echo none)"
  echo "t=$i api=$api ui=$ui"
  if [[ "$api" == "healthy" && "$ui" == "healthy" ]]; then
    exec "$(dirname "$0")/smoke.sh"
  fi
  sleep 1
done

echo "ERROR: stack not healthy within 60s" >&2
docker compose ps
docker logs --tail 200 mythiq_api || true
docker logs --tail 200 mythiq_ui || true
exit 1
