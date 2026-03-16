import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "shortforge" / "tmp"
REPORT = ROOT / "shortforge" / "viral_engine" / "reports" / "latest_proof_report.json"
OUTDIR = ROOT / "shortforge" / "viral_engine" / "projects" / "latest_ranked"

OUTDIR.mkdir(parents=True, exist_ok=True)

if not REPORT.exists():
    raise SystemExit(f"❌ missing report: {REPORT}")

data = json.loads(REPORT.read_text(encoding="utf-8"))
ranked = data.get("ranked_clips", [])
if not ranked:
    raise SystemExit("❌ no ranked clips in report")

top = ranked[:3]

for i, row in enumerate(top, 1):
    src = Path(row["file"])
    dst = OUTDIR / f"{i:02d}_{src.name}"
    vf = "fps=30,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,format=yuv420p"
    cmd = [
        "ffmpeg", "-y",
        "-i", str(src),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "19",
        "-c:a", "aac",
        "-b:a", "160k",
        str(dst)
    ]
    print("RUN:", " ".join(cmd))
    subprocess.run(cmd, check=True)

print(f"✅ rendered top {len(top)} ranked clips into: {OUTDIR}")
for p in sorted(OUTDIR.glob("*.mp4")):
    print("-", p.name)
