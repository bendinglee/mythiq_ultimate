#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

python3 scripts/build_shorts_review.py | tee /tmp/mythiq_review.out
DIR="$(awk '/REVIEW_READY/ {print $2}' /tmp/mythiq_review.out | tail -n 1)"
test -n "$DIR" || { echo "❌ review dir not created"; exit 1; }

PORT="${1:-8099}"
URL="http://127.0.0.1:${PORT}/"

echo "Serving $DIR at $URL"
python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$DIR" >/tmp/mythiq_review_server.log 2>&1 &
PID=$!
sleep 1

if command -v open >/dev/null 2>&1; then
  open "$URL" || true
fi

echo "REVIEW_URL=$URL"
echo "REVIEW_PID=$PID"
echo "Stop server with: kill $PID"
wait $PID
