#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

.venv/bin/python - <<'PY'
import json
import shutil
from pathlib import Path

from api.app.shorts.service import (
    ROOT,
    job_dir,
    render_vertical_clip,
    write_json,
    write_srt_for_clip,
    rank_moments_from_transcript,
)

fixture_mp4 = Path("tests/fixtures/shorts/sample.mp4")
fixture_tx = Path("tests/fixtures/shorts/sample_transcript.json")

tx = json.loads(fixture_tx.read_text())
job = job_dir("shorts_test")
src = job / "source" / "original.mp4"
ranked = job / "moments" / "ranked.json"
srt = job / "captions" / "short_01.srt"
out = job / "renders" / "short_01.mp4"

src.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(fixture_mp4, src)

moments = rank_moments_from_transcript(tx, 12.0, 1)
assert moments, "no ranked moments"
assert "reason" in moments[0], "reason missing"
assert "matched_keywords" in moments[0], "matched_keywords missing"
assert "speech_density" in moments[0], "speech_density missing"
assert "segment_count" in moments[0], "segment_count missing"
assert "transcript_preview" in moments[0], "transcript_preview missing"
write_json(ranked, moments)

m = moments[0]
render_vertical_clip(src, out, float(m["start_sec"]), float(m["end_sec"]))
count = write_srt_for_clip(tx, float(m["start_sec"]), float(m["end_sec"]), srt)

assert out.exists(), "short mp4 missing"
assert ranked.exists(), "ranked.json missing"
assert srt.exists(), "srt missing"
assert count >= 1, "subtitle count invalid"

print("SMOKE_SHORTS_LOCAL_OK")
PY
