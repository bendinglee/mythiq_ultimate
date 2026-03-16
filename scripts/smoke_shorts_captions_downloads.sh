#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PY:-$PWD/.venv/bin/python}"
test -x "$PY" || PY=python3

"$PY" - <<'PY'
from api.app.shorts.service import build_shorts

x = build_shorts(
    "https://youtu.be/La1zClF8jdY?si=sC-PL16XLbhI0GNt",
    target_count=10,
    prompt="minecraft betrayal survival twist ending base raid"
)

arts = x["artifacts"]
shorts = [a for a in arts if a["kind"] == "short_video"]
captioned = [a for a in arts if a["kind"] == "short_video_captioned"]
srt = [a for a in arts if a["kind"] == "subtitle"]
vtt = [a for a in arts if a["kind"] == "subtitle_vtt"]

assert len(shorts) == 10, f"expected 10 short videos, got {len(shorts)}"
assert len(srt) == 10, f"expected 10 srt files, got {len(srt)}"
assert len(vtt) == 10, f"expected 10 vtt files, got {len(vtt)}"
assert len(captioned) == 10, f"expected 10 captioned videos, got {len(captioned)}"

print("SMOKE_SHORTS_CAPTIONS_DOWNLOADS_OK")
PY
