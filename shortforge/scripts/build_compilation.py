import json
import subprocess
from pathlib import Path

ROOT = Path.cwd()
WEB = ROOT / "web" / "shorts_review"
INDEX = WEB / "shorts_index.json"

rows = json.loads(INDEX.read_text(encoding="utf-8"))

clips = []
for r in rows:
    rel = r.get("video_url", "").strip()
    if not rel:
        continue
    abs_path = (WEB / rel).resolve()
    if abs_path.exists():
        clips.append(abs_path)
    else:
        print("WARN missing clip:", abs_path)

if not clips:
    raise SystemExit("❌ no valid clips found for compilation")

list_file = ROOT / "shortforge" / "tmp" / "clip_list.txt"
list_file.parent.mkdir(parents=True, exist_ok=True)

with list_file.open("w", encoding="utf-8") as f:
    for c in clips:
        # ffmpeg concat demuxer needs proper quoting
        f.write("file '{}'\n".format(str(c).replace("'", "'\\''")))

out = ROOT / "shortforge" / "tmp" / "compilation.mp4"

cmd = [
    "ffmpeg",
    "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", str(list_file),
    "-c", "copy",
    str(out),
]

print("RUNNING:", " ".join(cmd))
res = subprocess.run(cmd, text=True)
if res.returncode != 0:
    raise SystemExit(f"❌ ffmpeg concat failed with code {res.returncode}")

print("✅ Compilation built:", out)
