#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PY:-$PWD/.venv/bin/python}"
test -x "$PY" || PY=python3

"$PY" - <<'PY'
import json
from pathlib import Path
from api.app.shorts.service import build_shorts

prompt = "minecraft betrayal survival base raid twist ending"
x = build_shorts("https://youtu.be/La1zClF8jdY?si=sC-PL16XLbhI0GNt", target_count=10, prompt=prompt)

arts = x["artifacts"]
thumbs = [a for a in arts if a["kind"] == "thumbnail"]
zips = [a for a in arts if a["kind"] == "package_zip"]
meta = [a for a in arts if a["kind"] == "clip_metadata"]

assert len(thumbs) == 10, f"expected 10 thumbnails, got {len(thumbs)}"
assert len(zips) == 1, f"expected 1 zip, got {len(zips)}"
assert len(meta) == 10, f"expected 10 clip metadata files, got {len(meta)}"

metrics = x["metrics"]
assert metrics.get("prompt") == prompt, "prompt missing in metrics"
assert isinstance(metrics.get("prompt_keywords"), list), "prompt keywords missing"
assert len(metrics.get("prompt_keywords")) >= 1, "prompt keywords empty"

for a in thumbs:
    assert Path(a["path"]).exists(), f"thumbnail missing: {a['path']}"

print("SMOKE_SHORTS_PROMPT_QUALITY_OK")
PY
