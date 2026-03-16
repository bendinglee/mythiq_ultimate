import json
import os
import shutil
import subprocess
from pathlib import Path

root = Path(".").resolve()
run_id = os.environ["RUN_ID"]

project = root / "shortforge" / "projects" / run_id
clips_dir = project / "clips"
moments_dir = project / "moments"
out_dir = project / "moment_renders"
transcripts_dir = project / "moment_transcripts"

if out_dir.exists():
    shutil.rmtree(out_dir)
if transcripts_dir.exists():
    shutil.rmtree(transcripts_dir)

out_dir.mkdir(parents=True, exist_ok=True)
transcripts_dir.mkdir(parents=True, exist_ok=True)

moment_file = moments_dir / "moment_candidates.json"
if not moment_file.exists():
    raise SystemExit(f"❌ missing {moment_file}")

rows = json.loads(moment_file.read_text(encoding="utf-8"))
if not rows:
    raise SystemExit("❌ no moment candidates found")

top = rows[:10]

for i, row in enumerate(top, 1):
    src = clips_dir / row["clip"]
    if not src.exists():
        print("skip missing:", src)
        continue

    dst = out_dir / f"{i:02d}_moment_{src.stem}.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(row["start"]),
        "-i", str(src),
        "-t", str(row["duration"]),
        "-vf", "fps=30,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,format=yuv420p",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "19",
        "-c:a", "aac",
        "-b:a", "160k",
        str(dst)
    ]
    print("RUN:", " ".join(cmd))
    subprocess.run(cmd, check=True)

print("✅ rendered moment clips to", out_dir)
for p in sorted(out_dir.glob("*.mp4")):
    print("-", p.name)
