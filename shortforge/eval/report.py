from __future__ import annotations
import sqlite3
from pathlib import Path

DB = Path("shortforge/data/quality.db")
conn = sqlite3.connect(DB)

print("== last 20 clip reviews ==")
for row in conn.execute("""
SELECT run_id, clip_index, variant, title, overall_score, chosen, exported
FROM clip_reviews
ORDER BY id DESC
LIMIT 20
"""):
    print(row)

print()
print("== aggregate averages ==")
for row in conn.execute("""
SELECT
  ROUND(AVG(hook_strength),2),
  ROUND(AVG(source_relevance),2),
  ROUND(AVG(story_clarity),2),
  ROUND(AVG(pacing_smoothness),2),
  ROUND(AVG(visual_framing),2),
  ROUND(AVG(caption_readability),2),
  ROUND(AVG(emotional_payoff),2),
  ROUND(AVG(replayability),2),
  ROUND(AVG(professional_polish),2),
  ROUND(AVG(overall_score),2)
FROM clip_reviews
"""):
    print(row)

conn.close()
