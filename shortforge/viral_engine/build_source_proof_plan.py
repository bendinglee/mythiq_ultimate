import json
import os
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "shortforge" / "viral_engine" / "libraries"
PROJECTS = ROOT / "shortforge" / "projects"

run_id = os.environ["RUN_ID"]
sector = os.environ["SECTOR"]
source_name = os.environ["SOURCE_NAME"]

project = PROJECTS / run_id
clips_dir = project / "clips"
transcripts_dir = project / "transcripts"
report_dir = project / "reports"
report_dir.mkdir(parents=True, exist_ok=True)

library_path = LIB / f"{sector}.json"
if not library_path.exists():
    raise SystemExit(f"❌ missing sector library: {library_path}")

library = json.loads(library_path.read_text(encoding="utf-8"))
clips = sorted(clips_dir.glob("*.mp4"))
if not clips:
    raise SystemExit(f"❌ no clips found in {clips_dir}")

HOOK_WORDS = {
    "entertainment": [
        "crazy", "insane", "no way", "what", "wait", "bro",
        "100000", "money", "party", "house", "secret",
        "caught", "surprise", "challenge", "win", "lose"
    ],
    "gaming": [
        "clutch", "fight", "dead", "trap", "pvp", "hunter",
        "kill", "unkillable", "combat", "bounty"
    ],
    "podcast": [
        "truth", "admit", "believe", "controversial", "story",
        "crazy", "important", "secret", "never"
    ],
    "education": [
        "how", "why", "mistake", "truth", "myth", "explained",
        "learn", "important", "reason"
    ]
}

ARC_WORDS = [
    "but", "then", "however", "suddenly", "instead", "until",
    "finally", "after", "before", "because"
]

def norm_text(s: str) -> str:
    s = s.lower()
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def count_hits(text: str, words: list[str]) -> int:
    total = 0
    for w in words:
        total += text.count(w)
    return total

def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))

def score_clip(clip_name: str, transcript_text: str, segment_count: int) -> dict:
    t = norm_text(transcript_text)
    hook_hits = count_hits(t, HOOK_WORDS.get(sector, []))
    arc_hits = count_hits(t, ARC_WORDS)
    word_count = len([x for x in t.split(" ") if x])
    uniq_count = len(set(t.split())) if t else 0

    hook = 0.35 + min(hook_hits * 0.08, 0.4)
    arc = 0.30 + min(arc_hits * 0.07, 0.35)
    pace = 0.25 + min(word_count / 120.0, 0.45)

    clarity_base = 0.75
    if word_count > 110:
        clarity_base -= 0.10
    if uniq_count < 20:
        clarity_base -= 0.10
    if len(clip_name) > 55:
        clarity_base -= 0.05
    caps = clamp(clarity_base)

    sync = clamp(0.35 + min(segment_count / 12.0, 0.35))

    weights = library["scoring_weights"]
    total = (
        hook * weights["hook_strength"] +
        arc * weights["emotional_arc"] +
        pace * weights["pacing_score"] +
        caps * weights["caption_clarity"] +
        sync * weights["sound_sync"]
    )

    return {
        "hook_strength": round(hook, 3),
        "emotional_arc": round(arc, 3),
        "pacing_score": round(pace, 3),
        "caption_clarity": round(caps, 3),
        "sound_sync": round(sync, 3),
        "hook_hits": hook_hits,
        "arc_hits": arc_hits,
        "word_count": word_count,
        "segment_count": segment_count,
        "viral_score": round(total, 3),
    }

rows = []

for clip in clips:
    tfile = transcripts_dir / f"{clip.stem}.json"
    transcript_text = ""
    segment_count = 0

    if tfile.exists():
        tdata = json.loads(tfile.read_text(encoding="utf-8"))
        transcript_text = tdata.get("text", "")
        segment_count = len(tdata.get("segments", []))

    rows.append({
        "file": str(clip.resolve()),
        "name": clip.name,
        "sector": sector,
        "transcript_text": transcript_text[:800],
        "score": score_clip(clip.name, transcript_text, segment_count),
        "recommended_transitions": library["transition_rules"],
        "recommended_caption_style": library["caption_style"],
        "ideal_lengths": library["ideal_lengths"]
    })

rows.sort(key=lambda r: r["score"]["viral_score"], reverse=True)

report = {
    "generated_at": int(time.time()),
    "run_id": run_id,
    "source_name": source_name,
    "sector": sector,
    "library": library,
    "ranked_clips": rows
}

out = report_dir / "proof_report.json"
out.write_text(json.dumps(report, indent=2), encoding="utf-8")

print("✅ wrote", out)
print("SOURCE:", source_name)
print("SECTOR:", sector)
print("COUNT:", len(rows))
for i, row in enumerate(rows[:12], 1):
    s = row["score"]
    print(
        i,
        s["viral_score"],
        "| hooks:", s["hook_hits"],
        "| arc:", s["arc_hits"],
        "| words:", s["word_count"],
        "| segs:", s["segment_count"],
        "|", row["name"]
    )
