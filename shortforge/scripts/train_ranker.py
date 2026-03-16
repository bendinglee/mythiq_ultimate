import sqlite3
import json

conn = sqlite3.connect("shortforge/db/shorts_eval.sqlite3")

rows = conn.execute("""
SELECT r.title, r.transcript, f.keep, f.rating
FROM clip_runs r
LEFT JOIN clip_feedback f
ON r.run_id=f.run_id AND r.title=f.title
""").fetchall()

scores = []

for title, transcript, keep, rating in rows:
    score = 0
    if keep:
        score += 2
    if rating:
        score += rating

    scores.append((title, score))

weights = {}

for title, score in scores:
    words = title.lower().split()
    for w in words:
        weights[w] = weights.get(w,0)+score

Path="shortforge/db/learned_weights.json"

import json, pathlib
pathlib.Path(Path).write_text(json.dumps(weights,indent=2))

print("✅ ranking model updated")
