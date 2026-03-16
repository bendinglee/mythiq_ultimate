#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PY:-$PWD/.venv/bin/python}"
test -x "$PY" || PY=python3

"$PY" - <<'PY'
from pathlib import Path
import json
import zipfile
from api.app.shorts.service import build_shorts

x = build_shorts("https://youtu.be/La1zClF8jdY?si=sC-PL16XLbhI0GNt", target_count=10)
arts = x["artifacts"]

zips = [a for a in arts if a["kind"] == "package_zip"]
assert len(zips) == 1, f"expected 1 package zip, got {len(zips)}"

zip_path = Path(zips[0]["path"])
assert zip_path.exists(), f"zip missing: {zip_path}"

with zipfile.ZipFile(zip_path) as zf:
    names = set(zf.namelist())

must = {
    "brief/package_manifest.json",
    "brief/shorts_package.json",
    "brief/shorts_package.md",
    "moments/ranked.json",
    "transcript/transcript.json",
    "renders/short_01.mp4",
    "renders/short_10.mp4",
    "captions/short_01.srt",
    "captions/short_10.srt",
    "clips_meta/clip_01.json",
    "clips_meta/clip_10.json",
}
missing = sorted(must - names)
assert not missing, f"zip missing files: {missing}"

print("SMOKE_SHORTS_EXPORT_ZIP_OK")
PY
