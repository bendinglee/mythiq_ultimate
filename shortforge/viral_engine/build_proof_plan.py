import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "shortforge" / "viral_engine" / "libraries"
TMP = ROOT / "shortforge" / "tmp"
OUT = ROOT / "shortforge" / "viral_engine" / "reports"

OUT.mkdir(parents=True, exist_ok=True)

timeline_path = TMP / "timeline.json"
if not timeline_path.exists():
    raise SystemExit(f"❌ missing timeline: {timeline_path}")

timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
clips = timeline.get("clips", [])
if not clips:
    raise SystemExit("❌ timeline has zero clips")

text_blob = " ".join(Path(c["file"]).name.lower() for c in clips)

rules = [
    ("gaming", ["pvp", "fight", "clutch", "minecraft", "hunter", "trap", "combat"]),
    ("podcast", ["podcast", "interview", "conversation", "guest", "host"]),
    ("education", ["explained", "how_to", "lesson", "history", "guide", "learn"])
]

sector = "gaming"
best_hits = -1

for name, kws in rules:
    hits = sum(1 for kw in kws if kw in text_blob)
    if hits > best_hits:
        best_hits = hits
        sector = name

lib_path = LIB / f"{sector}.json"
library = json.loads(lib_path.read_text(encoding="utf-8"))

def score_clip(name: str) -> dict:
    n = name.lower()
    hook = 0.55
    arc = 0.55
    pace = 0.55
    caps = 0.70
    sync = 0.60

    if any(x in n for x in ["fight", "clutch", "dead", "unkillable", "special", "wolves"]):
        hook += 0.20
    if any(x in n for x in ["turn", "changed", "however", "but", "instead"]):
        arc += 0.15
    if len(n) > 40:
        caps -= 0.05
    if any(x in n for x in ["all_right", "what_are_you", "like_where"]):
        pace += 0.08

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
        "viral_score": round(total, 3),
    }

rows = []
for c in clips:
    name = Path(c["file"]).name
    rows.append({
        "file": c["file"],
        "name": name,
        "sector": sector,
        "score": score_clip(name),
        "recommended_transitions": library["transition_rules"],
        "recommended_caption_style": library["caption_style"],
        "ideal_lengths": library["ideal_lengths"],
    })

rows.sort(key=lambda r: r["score"]["viral_score"], reverse=True)

report = {
    "generated_at": int(time.time()),
    "source_batch": timeline.get("source_batch"),
    "sector": sector,
    "library": library,
    "ranked_clips": rows
}

report_path = OUT / "latest_proof_report.json"
report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

print(f"✅ proof report written: {report_path}")
print(f"SECTOR={sector}")
print("RANKING:")
for i, row in enumerate(rows, 1):
    print(i, row["score"]["viral_score"], "|", row["name"])
