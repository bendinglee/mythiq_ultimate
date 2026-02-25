#!/usr/bin/env bash
set -euo pipefail

docker exec -i mythiq_api python - <<'PY'
import os, sqlite3

db=os.environ.get("MYTHIQ_DB_PATH","/app/state/mythiq.sqlite")
con=sqlite3.connect(db); cur=con.cursor()

sql = (
  "SELECT pattern_id, COUNT(*) uses, "
  "AVG(user_rating) avg_rating, "
  "AVG(implicit_score) avg_implicit, "
  "AVG(ab_winner) win_rate, "
  "SUM(CASE WHEN user_rating IS NOT NULL THEN 1 ELSE 0 END) n_r, "
  "SUM(CASE WHEN implicit_score IS NOT NULL THEN 1 ELSE 0 END) n_i, "
  "SUM(CASE WHEN ab_winner IS NOT NULL THEN 1 ELSE 0 END) n_a "
  "FROM generations "
  "WHERE pattern_id IS NOT NULL "
  "GROUP BY pattern_id "
  "HAVING uses >= 10"
)
rows = cur.execute(sql).fetchall()

SEED_TS = "1970-01-01 00:00:00"

def up(pid, status):
    cur.execute(
      "INSERT INTO library(pattern_id,status,last_updated) VALUES(?,?,?) "
      "ON CONFLICT(pattern_id) DO UPDATE SET status=excluded.status",
      (pid, status, SEED_TS),
    )

for pid, uses, ar, ai, wr, n_r, n_i, n_a in rows:
    # Require evidence for promotion; otherwise keep candidate
    if max(n_r, n_i, n_a) < 5:
        up(pid, "candidate")
        continue

    ar = ar or 0.0
    ai = ai or 0.0
    wr = wr or 0.0

    score = (ar * 0.60) + (ai * 0.20) + (wr * 5 * 0.20)

    if score >= 4.5:
        up(pid, "gold")
    elif score >= 4.0:
        up(pid, "standard")
    elif score < 2.0:
        up(pid, "deprecated")
    else:
        up(pid, "candidate")

cur.execute(
  "DELETE FROM library WHERE status=? AND (julianday('now') - julianday(last_updated)) > 30",
  ("deprecated",),
)

con.commit()
con.close()
print("OK evolve")
PY
