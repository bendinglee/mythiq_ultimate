#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PY:-$PWD/.venv/bin/python}"
test -x "$PY" || PY=python3

"$PY" - <<'PY'
import json
from api.app.shorts.service import build_shorts

x = build_shorts("https://youtu.be/La1zClF8jdY?si=sC-PL16XLbhI0GNt", target_count=10)

assert x["ok"] is True
assert x["feature"] == "shorts"
assert x["metrics"]["clips_generated"] == 10

arts = x["artifacts"]
short_videos = [a for a in arts if a["kind"] == "short_video"]
subtitles = [a for a in arts if a["kind"] == "subtitle"]
clip_meta = [a for a in arts if a["kind"] == "clip_metadata"]
manifests = [a for a in arts if a["kind"] == "package_manifest"]

assert len(short_videos) == 10, f"expected 10 short videos, got {len(short_videos)}"
assert len(subtitles) == 10, f"expected 10 subtitles, got {len(subtitles)}"
assert len(clip_meta) == 10, f"expected 10 clip metadata files, got {len(clip_meta)}"
assert len(manifests) == 1, f"expected 1 package manifest, got {len(manifests)}"

print("SMOKE_SHORTS_10PACK_OK")
PY
