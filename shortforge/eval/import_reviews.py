from __future__ import annotations
import csv
import sqlite3
from pathlib import Path

DB = Path("shortforge/data/quality.db")
CSV_PATH = Path("shortforge/eval/review_template.csv")

conn = sqlite3.connect(DB)

with CSV_PATH.open("r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

for r in rows:
    if not (r.get("run_id") and r.get("clip_index")):
        continue
    conn.execute("""
    INSERT INTO clip_reviews (
        run_id, clip_index, variant, title, anchor_text, transcript,
        hook_strength, source_relevance, story_clarity, pacing_smoothness,
        visual_framing, caption_readability, emotional_payoff, replayability,
        professional_polish, overall_score, chosen, exported, notes
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        r.get("run_id"),
        int(r.get("clip_index") or 0),
        r.get("variant"),
        r.get("title"),
        r.get("anchor_text"),
        r.get("transcript"),
        int(r.get("hook_strength") or 0),
        int(r.get("source_relevance") or 0),
        int(r.get("story_clarity") or 0),
        int(r.get("pacing_smoothness") or 0),
        int(r.get("visual_framing") or 0),
        int(r.get("caption_readability") or 0),
        int(r.get("emotional_payoff") or 0),
        int(r.get("replayability") or 0),
        int(r.get("professional_polish") or 0),
        float(r.get("overall_score") or 0),
        int(r.get("chosen") or 0),
        int(r.get("exported") or 0),
        r.get("notes"),
    ))

conn.commit()
print(f"OK: imported {len(rows)} review rows")
conn.close()
