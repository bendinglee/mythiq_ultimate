#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

OUT="$(.venv/bin/python - <<'PY'
import json
from api.app.shorts.service import build_shorts
x = build_shorts("https://youtu.be/La1zClF8jdY?si=sC-PL16XLbhI0GNt", target_count=1)
print(json.dumps(x))
PY
)"

python3 - <<'PY' "$OUT"
import json, sys
x = json.loads(sys.argv[1])
assert x["ok"] is True
assert x["feature"] == "shorts"
assert x["metrics"]["clips_generated"] >= 1
kinds = [a["kind"] for a in x["artifacts"]]
assert "short_video" in kinds
assert "subtitle" in kinds
print("SMOKE_SHORTS_SIDECAR_OK")
PY
