#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY="$ROOT/.venv/bin/python"
test -x "$PY" || { echo "❌ missing venv python: $PY"; exit 1; }

# start API in background
mkdir -p logs
PID="$(lsof -nP -iTCP:7777 -sTCP:LISTEN -t 2>/dev/null | head -n 1 || true)"
test -n "${PID:-}" && kill -9 "$PID" || true
nohup "$PY" -m uvicorn api.app.main:app --host 127.0.0.1 --port 7777 > logs/uvicorn.7777.log 2>&1 & disown
sleep 0.8

curl -fsS http://127.0.0.1:7777/readyz >/dev/null
echo "✅ /readyz ok"

RES="$(curl -fsS http://127.0.0.1:7777/v1/game/build -H "Content-Type: application/json" -d "{\"title\":\"Smoke Tools\",\"prompt\":\"Make a tiny arcade loop.\"}")"
echo "$RES" | python3 -m json.tool >/dev/null

DIR="$(python3 - <<PY
import json
print(json.loads("""$RES""")["dir"])
PY
)"
ZIP="$(python3 - <<PY
import json
print(json.loads("""$RES""")["zip"])
PY
)"

test -d "$DIR/tools" || { echo "❌ tools/ missing in dir: $DIR"; ls -la "$DIR"; exit 1; }
zipinfo -1 "$ZIP" | rg "^tools/" >/dev/null || { echo "❌ tools/ missing in zip: $ZIP"; exit 1; }

echo "✅ tools present in export dir + zip"
