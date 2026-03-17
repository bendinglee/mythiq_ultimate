#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

URL="${1:-}"
TOPIC="${2:-}"
TARGET_COUNT="${3:-10}"

test -n "$URL" || { echo "usage: scripts/url_to_10_shorts.sh <youtube_url> [topic_hint] [target_count]"; exit 1; }

STAMP="$(date +%s)"
JOB="artifacts/url_shorts_${STAMP}"
mkdir -p "$JOB/source" "$JOB/transcript" "$JOB/meta" "$JOB/renders" "$JOB/review"

echo "== 1) download source =="
if command -v yt-dlp >/dev/null 2>&1; then
  yt-dlp -f "mp4/bestvideo+bestaudio/best" --merge-output-format mp4 -o "$JOB/source/original.%(ext)s" "$URL"
else
  echo "❌ yt-dlp missing. brew install yt-dlp"
  exit 1
fi

SRC="$(find "$JOB/source" -maxdepth 1 -type f -name '*.mp4' | head -n 1)"
test -n "${SRC:-}" || { echo "❌ source mp4 missing"; exit 1; }

echo
echo "== 2) transcript =="
if command -v whisper >/dev/null 2>&1; then
  whisper "$SRC" --model turbo --output_format json --output_dir "$JOB/transcript" >/dev/null 2>&1 || true
fi

if [ ! -f "$JOB/transcript/$(basename "${SRC%.*}").json" ]; then
  python3 - <<'PY'
from pathlib import Path
import json, os
job = Path(os.environ["JOB"])
src = next((job/"source").glob("*.mp4"))
out = job/"transcript"/"transcript.json"
out.write_text(json.dumps({"segments":[
    {"start":0.0,"end":3.0,"text":"Opening segment placeholder for transcript not found."},
    {"start":3.0,"end":6.0,"text":"Install whisper for real transcript extraction."}
]}, indent=2), encoding="utf-8")
print(out)
PY
else
  cp "$JOB/transcript/$(basename "${SRC%.*}").json" "$JOB/transcript/transcript.json"
fi

echo
echo "== 3) rank moments =="
python3 api/app/moment_ranker.py "$JOB" --topic "$TOPIC" --out "$JOB/meta/candidates.json"

echo
echo "== 4) select diverse top moments =="
python3 api/app/diversity_selector.py "$JOB/meta/candidates.json" --out "$JOB/meta/selected.json" --target-count "$TARGET_COUNT"

echo
echo "== 5) build edit decisions =="
python3 api/app/edit_decision_engine.py "$JOB/meta/selected.json" --out "$JOB/meta/edit_plan.json"

echo
echo "== 6) quality gate =="
python3 api/app/shorts_quality_gate.py "$JOB/meta/edit_plan.json" --out "$JOB/meta/quality.json"

echo
echo "== 7) render actual shorts using existing local pipeline if available =="
if [ -x scripts/shorts_story_upgrade.py ]; then
  python3 scripts/shorts_story_upgrade.py || true
fi

echo
echo "== 8) build review page =="
if [ -f scripts/build_shorts_review.py ]; then
  python3 scripts/build_shorts_review.py || true
fi

echo
echo "== 9) open review page if present =="
if [ -f web/shorts_review/index.html ]; then
  PID="$(lsof -tiTCP:8788 -sTCP:LISTEN || true)"
  if [ -n "${PID:-}" ]; then kill -9 "$PID"; fi
  nohup python3 -m http.server 8788 --bind 127.0.0.1 >/tmp/mythiq_shorts_review.log 2>&1 &
  sleep 2
  open http://127.0.0.1:8788/web/shorts_review/index.html || true
fi

echo
echo "JOB=$JOB"
echo "SRC=$SRC"
echo "CANDIDATES=$JOB/meta/candidates.json"
echo "SELECTED=$JOB/meta/selected.json"
echo "EDIT_PLAN=$JOB/meta/edit_plan.json"
echo "QUALITY=$JOB/meta/quality.json"
