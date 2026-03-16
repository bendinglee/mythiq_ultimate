import json
import os
import time
from collections import defaultdict
from pathlib import Path

root = Path(".").resolve()
run_id = os.environ["RUN_ID"]
sector = os.environ.get("SECTOR", "general")
source_name = os.environ.get("SOURCE_NAME", run_id)

project = root / "shortforge" / "projects" / run_id
transcripts_dir = project / "moment_transcripts"

renders_dir = project / "scene_renders"
report_dir = project / "reports"
library_file = root / "shortforge" / "library" / "sector_rules.json"

if not library_file.exists():
    raise SystemExit(f"❌ missing library file: {library_file}")
if not transcripts_dir.exists():
    raise SystemExit(f"❌ missing transcripts dir: {transcripts_dir}")

library_all = json.loads(library_file.read_text(encoding="utf-8"))
library = library_all.get(sector) or library_all.get("general")
if not library:
    raise SystemExit(f"❌ no library rules for sector: {sector}")

report_dir.mkdir(parents=True, exist_ok=True)

hook_words = [w.lower() for w in library["hook_words"]]
arc_words = [w.lower() for w in library["arc_words"]]

rows = []

strong_openers = {
    "what", "wait", "welcome", "today", "who", "how", "why",
    "when", "win", "wins", "loser", "secret", "surprise",
    "money", "score", "party", "caught", "higher", "lower"
}

question_phrases = {
    "what", "who", "why", "how", "when", "where", "are you",
    "did you", "can you", "do you", "is this"
}

for clip in sorted(renders_dir.glob("*.mp4")):
    tfile = transcripts_dir / f"{clip.stem}.json"
    if not tfile.exists():
        continue

    data = json.loads(tfile.read_text(encoding="utf-8"))
    text = (data.get("text") or "").strip()
    seg_list = data.get("segments") or []

    text_l = text.lower()
    words = len(text.split())
    segs = len(seg_list)

    hook_hits = sum(text_l.count(w) for w in library["hook_words"])
    arc_hits = sum(text_l.count(w) for w in library["arc_words"])

    duration = float(data.get("duration") or 0.0)
    if duration <= 0:
        duration = 15.0

    first_three = " ".join(
        (seg.get("text") or "").strip()
        for seg in seg_list
        if float(seg.get("start", 999)) <= 3.0
    ).lower()

    opener_hits = sum(first_three.count(w) for w in strong_openers)
    question_hits = sum(text_l.count(q) for q in question_phrases)

    dialogue_density = words / max(duration, 1.0)
    duration_center = max(0.0, 1.0 - (abs(duration - 15.0) / 10.0))

    hook = min(0.22 + hook_hits / 8.0 + opener_hits / 6.0 + question_hits / 10.0, 1.0)
    arc = min(0.16 + arc_hits / 7.0, 1.0)
    pace = min(0.25 + dialogue_density / 3.8, 1.0)
    caps = 0.84 if 45 <= words <= 110 else 0.72 if 30 <= words <= 140 else 0.55
    sync = min(0.28 + segs / 14.0, 0.95)
    length_fit = duration_center

    filler_penalty = 0.0
    if dialogue_density < 1.6:
        filler_penalty += 0.10
    if words < 24:
        filler_penalty += 0.10
    if segs < 4:
        filler_penalty += 0.06

    w = library["scoring_weights"]
    total = (
        hook * w["hook_strength"] +
        arc * w["emotional_arc"] +
        pace * w["pacing_score"] +
        caps * w["caption_clarity"] +
        sync * w["sound_sync"] +
        length_fit * 0.16
    ) - filler_penalty

    source_clip = clip.stem
    if source_clip.endswith("_scene"):
        source_clip = clip.stem
    elif "_moment_" in clip.stem:
        source_clip = clip.stem.split("_moment_", 1)[1]

    rows.append({
        "file": str(clip.resolve()),
        "name": clip.name,
        "source_clip": source_clip,
        "sector": sector,
        "transcript_text": text[:1200],
        "score": {
            "hook_strength": round(hook, 3),
            "emotional_arc": round(arc, 3),
            "pacing_score": round(pace, 3),
            "caption_clarity": round(caps, 3),
            "sound_sync": round(sync, 3),
            "length_fit": round(length_fit, 3),
            "hook_hits": hook_hits,
            "arc_hits": arc_hits,
            "opener_hits": opener_hits,
            "question_hits": question_hits,
            "word_count": words,
            "segment_count": segs,
            "dialogue_density": round(dialogue_density, 3),
            "filler_penalty": round(filler_penalty, 3),
            "viral_score": round(total, 3),
        },
        "recommended_transitions": library["transition_rules"]
    })

rows.sort(key=lambda r: r["score"]["viral_score"], reverse=True)

used_sources = defaultdict(int)
reranked = []

for row in rows:
    src = row["source_clip"]
    penalty = 0.0
    if used_sources[src] == 1:
        penalty = 0.05
    elif used_sources[src] >= 2:
        penalty = 0.12

    row["score"]["viral_score"] = round(row["score"]["viral_score"] - penalty, 3)
    reranked.append(row)
    used_sources[src] += 1

reranked.sort(key=lambda r: r["score"]["viral_score"], reverse=True)

final_rows = []
source_counts = defaultdict(int)

for row in reranked:
    src = row["source_clip"]

    if len(final_rows) < 5 and source_counts[src] >= 1:
        continue
    if len(final_rows) < 10 and source_counts[src] >= 2:
        continue

    final_rows.append(row)
    source_counts[src] += 1

target_n = min(10, len(reranked))
if len(final_rows) < target_n:
    for row in reranked:
        if row in final_rows:
            continue
        final_rows.append(row)
        if len(final_rows) >= target_n:
            break
report = {
    "generated_at": int(time.time()),
    "run_id": run_id,
    "source_name": source_name,
    "sector": sector,
    "ranked_clips": final_rows
}

out = report_dir / "moment_proof_report.json"
out.write_text(json.dumps(report, indent=2), encoding="utf-8")

print("✅ wrote", out)
for i, row in enumerate(final_rows[:10], 1):
    print(i, row["name"], row["score"]["viral_score"])
