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
meta = [a for a in arts if a["kind"] == "clip_metadata"]
assert len(meta) == 10, f"expected 10 clip metadata files, got {len(meta)}"

from pathlib import Path
for a in meta:
    p = Path(a["path"])
    assert p.exists(), f"missing metadata file: {p}"
    import json
    obj = json.loads(p.read_text(encoding="utf-8"))
    for k in [
        "story_role",
        "backstory_context",
        "hook_variants",
        "title_variants",
        "thumbnail_variants",
        "viral_title",
        "hook_line",
        "thumbnail_text",
    ]:
        assert k in obj, f"missing key {k} in {p}"
    assert len(obj["hook_variants"]) >= 1, f"empty hook_variants in {p}"
    assert len(obj["title_variants"]) >= 1, f"empty title_variants in {p}"
    assert len(obj["thumbnail_variants"]) >= 1, f"empty thumbnail_variants in {p}"

print("SMOKE_SHORTS_PACKAGING_BRAIN_OK")
PY
