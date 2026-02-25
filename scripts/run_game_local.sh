#!/usr/bin/env bash
set -euo pipefail

API="${API:-http://127.0.0.1:7777}"
PORT="${PORT:-8088}"

TITLE="${1:-Local Run}"
PROMPT="${2:-test}"

# build
curl -fsS "$API/v1/game/build" -H "content-type: application/json" \
  -d "{\"title\":\"$TITLE\",\"prompt\":\"$PROMPT\"}" > /tmp/mythiq_game_build.json

GID="$(python3 - <<PY
import json
print(json.load(open("/tmp/mythiq_game_build.json","r",encoding="utf-8"))["game_id"])
PY
)"

# download zip into repo exports (persisted)
ZIP="exports/runs/$GID.zip"
curl -fsS -L "$API/v1/game/download/$GID" -o "$ZIP"

# unzip into repo exports (persisted)
DIR="exports/runs/$GID"
rm -rf "$DIR"
mkdir -p "$DIR"
unzip -o "$ZIP" -d "$DIR" >/dev/null

./scripts/validate_game_export.sh "$DIR"

# free port
lsof -ti ":$PORT" | xargs kill -9 2>/dev/null || true

echo "GID=$GID"
echo "DIR=$DIR"
echo "URL=http://127.0.0.1:$PORT/"
python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$DIR"
