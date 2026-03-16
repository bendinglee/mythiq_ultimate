from __future__ import annotations
import csv
import sqlite3
from pathlib import Path

DB = Path("shortforge/data/quality.db")
CSV_PATH = Path("shortforge/eval/review_template.csv")

conn = sqlite3.connect(DB)

with CSV_PATH.open("r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

inserted = 0

for r in rows:
    run_id = (r.get("run_id") or r.get(" run_id") or "").strip()
    clip_index = (r.get("clip_index") or "").strip()

    if not run_id or not clip_index:
        continue

    conn.execute("""
    INSERT INTO clip_reviews (
        run_id, clip_index, variant, title, anchor_text, transcript,
        hook_strength, source_relevance, story_clarity, pacing_smoothness,
        visual_framing, caption_readability, emotional_payoff, replayability,
        professional_polish, overall_score, chosen, exported, notes
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        int(clip_index),
        (r.get("variant") or "").strip(),
        (r.get("title") or "").strip(),
        (r.get("anchor_text") or "").strip(),
        (r.get("transcript") or "").strip(),
        int(float((r.get("hook_strength") or "0").strip() or 0)),
        int(float((r.get("source_relevance") or "0").strip() or 0)),
        int(float((r.get("story_clarity") or "0").strip() or 0)),
        int(float((r.get("pacing_smoothness") or "0").strip() or 0)),
        int(float((r.get("visual_framing") or "0").strip() or 0)),
        int(float((r.get("caption_readability") or "0").strip() or 0)),
        int(float((r.get("emotional_payoff") or "0").strip() or 0)),
        int(float((r.get("replayability") or "0").strip() or 0)),
        int(float((r.get("professional_polish") or "0").strip() or 0)),
        float((r.get("overall_score") or "0").strip() or 0),
        int(float((r.get("chosen") or "0").strip() or 0)),
        int(float((r.get("exported") or "0").strip() or 0)),
        (r.get("notes") or "").strip(),
    ))
    inserted += 1

conn.commit()
print(f"OK: inserted {inserted} review rows into {DB}")
conn.close()
