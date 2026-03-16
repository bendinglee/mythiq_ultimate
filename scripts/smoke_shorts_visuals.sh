#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PY:-$PWD/.venv/bin/python}"
test -x "$PY" || PY=python3

"$PY" - <<'PY'
from api.app.shorts.service import build_shorts

x = build_shorts("https://youtu.be/La1zClF8jdY?si=sC-PL16XLbhI0GNt", target_count=10)
arts = x["artifacts"]

thumbs = [a for a in arts if a["kind"] == "thumbnail"]
zips = [a for a in arts if a["kind"] == "package_zip"]

assert len(thumbs) == 10, f"expected 10 thumbnails, got {len(thumbs)}"
assert len(zips) == 1, f"expected 1 package zip, got {len(zips)}"

print("SMOKE_SHORTS_VISUALS_OK")
PY
