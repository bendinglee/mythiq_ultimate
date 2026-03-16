import json
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path.cwd()
WEB = ROOT / "web" / "shorts_review"
INDEX = WEB / "shorts_index.json"
DB = ROOT / "shortforge" / "db" / "shorts_eval.sqlite3"

rows = json.loads(INDEX.read_text(encoding="utf-8"))
conn = sqlite3.connect(DB)

feedback = {}
if DB.exists():
    for run_id, title, keep, rating in conn.execute("""
        SELECT run_id, title, keep, rating
        FROM clip_feedback
        ORDER BY id DESC
    """):
        feedback[(run_id, title)] = {
            "keep": int(keep or 0),
            "rating": float(rating or 0.0),
        }

# derive current run_id from media path
run_id = ""
if rows:
    media = rows[0].get("video_url", "")
    parts = media.split("/")
    if len(parts) >= 2:
        run_id = parts[1]

scored = []
for r in rows:
    title = r.get("title", "")
    meta = feedback.get((run_id, title), {"keep": 0, "rating": 0.0})
    score = float(r.get("score", 0.0) or 0.0)
    score += meta["rating"] * 0.25
    if meta["keep"]:
        score += 1.5
    scored.append((score, r, meta))

# prefer kept clips first; otherwise use top scored
kept = [(s, r, m) for s, r, m in scored if m["keep"] == 1]
chosen = kept if kept else sorted(scored, key=lambda x: x[0], reverse=True)

clips = []
for _, r, _ in chosen:
    rel = r.get("video_url", "").strip()
    if not rel:
        continue
    abs_path = (WEB / rel).resolve()
    if abs_path.exists():
        clips.append((r.get("title", "Untitled"), abs_path))

if not clips:
    raise SystemExit("❌ no valid clips found for best compilation")

list_file = ROOT / "shortforge" / "tmp" / "best_clip_list.txt"
list_file.parent.mkdir(parents=True, exist_ok=True)

with list_file.open("w", encoding="utf-8") as f:
    for _, clip in clips:
        f.write("file '{}'\n".format(str(clip).replace("'", "'\\''")))

out = ROOT / "shortforge" / "tmp" / "best_compilation.mp4"

cmd = [
    "ffmpeg",
    "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", str(list_file),
    "-vf", "format=yuv420p",
    "-c:v", "libx264",
    "-preset", "slow",
    "-crf", "19",
    "-c:a", "aac",
    "-b:a", "192k",
    str(out),
]

print("RUNNING:", " ".join(cmd))
res = subprocess.run(cmd, text=True)
if res.returncode != 0:
    raise SystemExit(f"❌ ffmpeg best compilation failed with code {res.returncode}")

print("✅ Best compilation built:", out)
print("CLIPS_USED:")
for title, clip in clips:
    print("-", title, "|", clip.name)
