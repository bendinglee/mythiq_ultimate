#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PROJECT_ID="${1:-580e34fb}"
CLIP_NAME="${2:-clip_3}"
MODE="${3:-tiktok_4k}"
BASE="${BASE:-http://127.0.0.1:8789}"

TMP_DIR="$ROOT/artifacts/_quality_tmp"
mkdir -p "$TMP_DIR"

JSON_OUT="$TMP_DIR/final_render_quality.json"
SCORE_OUT="$TMP_DIR/final_render_score.json"

echo "== health =="
curl -fsS "$BASE/health" >/dev/null
echo "OK"

echo
echo "== final render request =="
curl -fsS -X POST "$BASE/final-render" \
  -H "Content-Type: application/json" \
  -d "{\"project_id\":\"$PROJECT_ID\",\"clip_name\":\"$CLIP_NAME\",\"mode\":\"$MODE\",\"burn_captions\":true}" \
  | tee "$JSON_OUT"

FINAL_PATH="$(python3 - <<'PY'
import json
from pathlib import Path
p = Path("artifacts/_quality_tmp/final_render_quality.json")
d = json.loads(p.read_text())
print(d["final_path"])
PY
)"

echo
echo "== file exists =="
test -f "$FINAL_PATH"
test -s "$FINAL_PATH"
echo "OK $FINAL_PATH"

echo
echo "== ffprobe dimensions =="
WIDTH="$(ffprobe -v error -select_streams v:0 -show_entries stream=width -of csv=p=0 "$FINAL_PATH")"
HEIGHT="$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=p=0 "$FINAL_PATH")"
echo "WIDTH=$WIDTH HEIGHT=$HEIGHT"

if [[ "$MODE" == "tiktok_4k" ]]; then
  [[ "$WIDTH" == "2160" ]] || { echo "FAIL: width not 2160"; exit 1; }
  [[ "$HEIGHT" == "3840" ]] || { echo "FAIL: height not 3840"; exit 1; }
else
  [[ "$WIDTH" == "1080" ]] || { echo "FAIL: width not 1080"; exit 1; }
  [[ "$HEIGHT" == "1920" ]] || { echo "FAIL: height not 1920"; exit 1; }
fi

echo
echo "== bitrate floor =="
BITRATE="$(ffprobe -v error -show_entries format=bit_rate -of csv=p=0 "$FINAL_PATH")"
echo "BITRATE=$BITRATE"
if [[ "$MODE" == "tiktok_4k" ]]; then
  [[ "${BITRATE:-0}" -ge 8000000 ]] || { echo "FAIL: 4k bitrate below floor"; exit 1; }
else
  [[ "${BITRATE:-0}" -ge 2000000 ]] || { echo "FAIL: 1080p bitrate below floor"; exit 1; }
fi

echo
echo "== truthful caption fallback flags =="
python3 - <<'PY'
import json
from pathlib import Path
d = json.loads(Path("artifacts/_quality_tmp/final_render_quality.json").read_text())
assert "burn_captions_requested" in d, "missing burn_captions_requested"
assert "burn_captions_applied" in d, "missing burn_captions_applied"
assert "warning" in d, "missing warning"
if d["burn_captions_requested"] and not d["burn_captions_applied"]:
    assert d["warning"], "missing fallback warning"
print("OK")
PY

echo
echo "== git cleanliness =="
if ! git diff --quiet -- shortforge/projects 2>/dev/null; then
  echo "FAIL: tracked shortforge project dirtiness detected"
  exit 1
fi
echo "OK"

echo
echo "== machine quality score =="
python3 shortforge/eval/short_quality_score.py "$FINAL_PATH" | tee "$SCORE_OUT"

echo
echo "== overall threshold =="
python3 - <<'PY'
import json
from pathlib import Path
d = json.loads(Path("artifacts/_quality_tmp/final_render_score.json").read_text())
overall = float(d["overall"])
print("OVERALL=", overall)
assert overall >= 7.0, f"overall score too low: {overall}"
PY

echo
echo "SMOKE_SHORTS_QUALITY_CONTRACT_OK"
