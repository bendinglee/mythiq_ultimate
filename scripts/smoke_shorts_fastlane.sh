#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

test -x scripts/shorts_fastlane.py
python3 scripts/shorts_fastlane.py

LATEST="$(python3 - <<'PY'
from pathlib import Path
roots = sorted((Path("artifacts")).glob("shorts_*/fastlane/meta/ranking.json"))
print(roots[-1] if roots else "")
PY
)"
test -n "$LATEST"
python3 - <<PY
import json, pathlib
p = pathlib.Path("$LATEST")
data = json.loads(p.read_text())
assert data and isinstance(data, list), "ranking empty"
assert "title" in data[0], "missing title"
assert "fast_video" in data[0], "missing fast_video"
print("SMOKE_SHORTS_FASTLANE_OK", len(data), data[0]["title"])
PY
