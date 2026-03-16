#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PY:-$PWD/.venv/bin/python}"
test -x "$PY" || PY=python3

"$PY" - <<'PY'
import zipfile
from pathlib import Path
from api.app.shorts.service import build_shorts

x = build_shorts(
    "https://youtu.be/La1zClF8jdY?si=sC-PL16XLbhI0GNt",
    target_count=10,
    prompt="football comeback rivalry story"
)

zips = [a for a in x["artifacts"] if a["kind"] == "package_zip"]
assert len(zips) == 1, f"expected 1 zip, got {len(zips)}"

zp = Path(zips[0]["path"])
assert zp.exists(), f"zip missing: {zp}"

with zipfile.ZipFile(zp) as zf:
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
    "thumbnails/clip_01.png",
    "thumbnails/clip_10.png",
}
missing = sorted(must - names)
assert not missing, f"zip missing files: {missing}"

print("SMOKE_SHORTS_ZIP_CONTENTS_OK")
PY
