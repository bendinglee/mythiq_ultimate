import json
import os
import re
from pathlib import Path

root = Path(".").resolve()
run_id = os.environ["RUN_ID"]

project = root / "shortforge" / "projects" / run_id
transcripts_dir = project / "transcripts"
moments_dir = project / "moments"

moments_dir.mkdir(parents=True, exist_ok=True)

if not transcripts_dir.exists():
    raise SystemExit(f"❌ missing transcripts dir: {transcripts_dir}")

TRIGGERS = [
    "100k", "100000", "money", "party", "challenge", "win", "wins", "lose", "loser",
    "out", "caught", "secret", "surprise", "penalty", "score", "room", "build",
    "ready", "party", "what have you got", "pick", "higher", "lower"
]

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower()).strip()

rows = []

for tfile in sorted(transcripts_dir.glob("*.json")):
    data = json.loads(tfile.read_text(encoding="utf-8"))
    clip_name = data["clip"]
    segments = data.get("segments", [])

    seen = set()

    for seg in segments:
        text_raw = seg.get("text", "")
        text = norm(text_raw)
        if not text:
            continue

        hits = sum(text.count(word) for word in TRIGGERS)
        if hits <= 0:
            continue

        start = max(0, float(seg["start"]) - 2.5)
        end = float(seg["end"]) + 4.5

        key = (clip_name, round(start, 1), round(end, 1), text[:80])
        if key in seen:
            continue
        seen.add(key)

        rows.append({
            "clip": clip_name,
            "segment_text": text_raw,
            "trigger_hits": hits,
            "start": round(start, 2),
            "end": round(end, 2),
            "duration": round(end - start, 2)
        })

rows.sort(key=lambda r: (r["trigger_hits"], r["duration"]), reverse=True)

deduped = []
used_clip_windows = {}

for row in rows:
    clip = row["clip"]
    start = row["start"]
    end = row["end"]

    prev_windows = used_clip_windows.setdefault(clip, [])
    overlap = False
    for a, b in prev_windows:
        if max(a, start) < min(b, end):
            overlap = True
            break
    if overlap:
        continue

    prev_windows.append((start, end))
    deduped.append(row)

out = moments_dir / "moment_candidates.json"
out.write_text(json.dumps(deduped, indent=2), encoding="utf-8")

print("✅ wrote", out)
print("COUNT", len(deduped))
for i, row in enumerate(deduped[:20], 1):
    print(
        i,
        "| hits:", row["trigger_hits"],
        "|", row["clip"],
        "|", f'{row["start"]}->{row["end"]}',
        "|", row["segment_text"][:120]
    )
