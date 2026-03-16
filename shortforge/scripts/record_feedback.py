import sqlite3
import sys

run_id = sys.argv[1]
title = sys.argv[2]
keep = int(sys.argv[3])
rating = float(sys.argv[4])

conn = sqlite3.connect("shortforge/db/shorts_eval.sqlite3")

conn.execute(
    "INSERT INTO clip_feedback (run_id,title,keep,rating) VALUES (?,?,?,?)",
    (run_id,title,keep,rating)
)

conn.commit()
print("feedback saved")
