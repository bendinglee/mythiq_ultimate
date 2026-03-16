import json
import os
from pathlib import Path
from faster_whisper import WhisperModel

root = Path(".").resolve()
run_id = os.environ["RUN_ID"]

project = root / "shortforge" / "projects" / run_id
scene_dir = project / "scene_renders"
moment_dir = project / "moment_renders"
out_dir = project / "moment_transcripts"

clips_dir = None
if scene_dir.exists() and any(scene_dir.glob("*.mp4")):
    clips_dir = scene_dir
elif moment_dir.exists() and any(moment_dir.glob("*.mp4")):
    clips_dir = moment_dir
else:
    raise SystemExit(f"❌ no clips found in {scene_dir} or {moment_dir}")

out_dir.mkdir(parents=True, exist_ok=True)
clips = sorted(clips_dir.glob("*.mp4"))
if not clips:
    raise SystemExit(f"❌ no clips found in {clips_dir}")

model = WhisperModel("small", device="cpu", compute_type="int8")

for clip in clips:
    try:
        segments, info = model.transcribe(str(clip), vad_filter=True)
    except Exception as e:
        print(f"skip failed transcript: {clip} | {e}")
        continue

    rows = []
    full_text = []
    for seg in segments:
        text = (seg.text or "").strip()
        if not text:
            continue
        rows.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": text
        })
        full_text.append(text)

    payload = {
        "clip": clip.name,
        "source_clip": clip.stem,
        "language": getattr(info, "language", None),
        "duration": getattr(info, "duration", None),
        "text": " ".join(full_text).strip(),
        "segments": rows
    }

    out = out_dir / f"{clip.stem}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("✅ transcript:", out)

print("DONE")
