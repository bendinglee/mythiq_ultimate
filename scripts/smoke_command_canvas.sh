#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PORT="${MYTHIQ_CANVAS_PORT:-8099}"
lsof -ti tcp:$PORT | xargs kill -9 2>/dev/null || true
sleep 1

MYTHIQ_CANVAS_PORT="$PORT" python3 command_canvas/server.py >/tmp/mythiq_canvas.log 2>&1 &
PID=$!
trap 'kill $PID >/dev/null 2>&1 || true' EXIT

sleep 1

BASE="http://127.0.0.1:$PORT"

curl -fsS "$BASE/" >/dev/null
curl -fsS "$BASE/api/history" >/dev/null

TEXT="$(curl -sS -H 'Content-Type: application/json' \
  -d '{"prompt":"Explain Nikola Tesla free energy theory and in practice","mode":"docs"}' \
  "$BASE/api/command")"

CODE="$(curl -sS -H 'Content-Type: application/json' \
  -d '{"prompt":"Write a FastAPI starter app for tasks","mode":"code"}' \
  "$BASE/api/command")"

GAME="$(curl -sS -H 'Content-Type: application/json' \
  -d '{"prompt":"Build a football pack opening game","mode":"game"}' \
  "$BASE/api/command")"

SHORTS="$(curl -sS -H 'Content-Type: application/json' \
  -d '{"prompt":"Turn this long video into ranked shorts","mode":"shorts","source_url":"https://youtu.be/La1zClF8jdY?si=yRFUe9taWKtJNe-Z","transcript":"I joined the biggest Minecraft server and chaos started immediately. Then things escalated. I was overwhelmed at first. Then came the biggest reveal. Finally I understood why this server is legendary.","target_count":5}' \
  "$BASE/api/command")"

python3 - <<'PY' "$TEXT" "$CODE" "$GAME" "$SHORTS"
import json, sys
for raw in sys.argv[1:]:
    x = json.loads(raw)
    assert x["feature"] in {"docs","code","game","shorts"}
    assert len(x["artifacts"]) >= 1
    assert "metrics" in x
    assert "critique_score" in x["metrics"]
    assert "validation_passed" in x["metrics"]
    assert "critic_report" in x
print("✅ smoke passed")
PY
