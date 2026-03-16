import json
import os
import shutil
import subprocess
from pathlib import Path

root = Path.cwd()
run_id = os.environ["RUN_ID"]
source_video = Path(os.environ["SOURCE_VIDEO"])

project = root / "shortforge" / "projects" / run_id
analysis_dir = project / "analysis"
out_dir = project / "scene_renders"
scene_candidates_file = analysis_dir / "scene_candidates.json"

if not source_video.exists():
    raise SystemExit(f"❌ missing source video: {source_video}")

if not scene_candidates_file.exists():
    raise SystemExit(f"❌ missing scene candidates: {scene_candidates_file}")

rows = json.loads(scene_candidates_file.read_text(encoding="utf-8"))
if not rows:
    raise SystemExit("❌ no scene candidates found")

if out_dir.exists():
    shutil.rmtree(out_dir)
out_dir.mkdir(parents=True, exist_ok=True)

top = rows[:10]

for i, row in enumerate(top, 1):
    dst = out_dir / f"{i:02d}_scene.mp4"

    vf = (
        "fps=30,"
        "crop=in_h*9/16:in_h:(in_w-in_h*9/16)/2:0,"
        "scale=1080:1920:flags=lanczos,"
        "eq=contrast=1.03:saturation=1.08:brightness=0.01,"
        "unsharp=5:5:0.8:3:3:0.4,"
        "format=yuv420p"
    )

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(row["start"]),
        "-i", str(source_video),
        "-t", str(row["duration"]),
        "-vf", vf,
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-movflags", "+faststart",
        "-c:a", "aac",
        "-b:a", "192k",
        str(dst),
    ]

    print("RUN:", " ".join(cmd))
    subprocess.run(cmd, check=True)

    if not dst.exists() or dst.stat().st_size < 50000:
        raise SystemExit(f"❌ bad render output: {dst}")

print("✅ rendered scene clips to", out_dir)
for p in sorted(out_dir.glob("*.mp4")):
    print("-", p.name)
