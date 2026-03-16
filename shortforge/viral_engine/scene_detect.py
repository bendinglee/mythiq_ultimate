import json
import sys
from pathlib import Path

from scenedetect import detect, AdaptiveDetector

def detect_scenes(video_path: str):
    scene_list = detect(
        video_path,
        AdaptiveDetector(
            adaptive_threshold=5.2,
            min_scene_len=4.0,
        ),
    )

    rows = []
    for start, end in scene_list:
        s = start.get_seconds()
        e = end.get_seconds()
        dur = e - s

        if dur < 3.0:
            continue

        rows.append({
            "start": round(s, 2),
            "end": round(e, 2),
            "duration": round(dur, 2),
        })

    return rows


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python shortforge/viral_engine/scene_detect.py <video_file> [json_out]")
        sys.exit(1)

    video = Path(sys.argv[1])
    if not video.exists():
        raise SystemExit(f"❌ missing video: {video}")

    scenes = detect_scenes(str(video))

    print("SCENES FOUND:", len(scenes))
    for i, s in enumerate(scenes[:30], 1):
        print(i, s["start"], "->", s["end"], "dur", s["duration"])

    if len(sys.argv) >= 3:
        out = Path(sys.argv[2])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(scenes, indent=2), encoding="utf-8")
        print("✅ wrote", out)
