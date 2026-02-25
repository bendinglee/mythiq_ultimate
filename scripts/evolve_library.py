#!/usr/bin/env python3
import os
import sqlite3

DB = os.environ.get("MYTHIQ_DB_PATH", os.environ.get("MYTHIQ_DB", "state/mythiq.sqlite"))

def table_exists(cur, name: str) -> bool:
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (name,))
    return cur.fetchone() is not None

def evolve_library():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    # Hard stop if schema not present yet
    if not table_exists(cursor, "generations"):
        print(f"SKIP: table 'generations' not found in DB: {DB}")
        conn.close()
        return

    if not table_exists(cursor, "library"):
        print(f"SKIP: table 'library' not found in DB: {DB}")
        conn.close()
        return

    candidates = cursor.execute("""
        SELECT
            pattern_id,
            COUNT(*) as uses,
            AVG(user_rating) as avg_rating,
            AVG(implicit_score) as avg_implicit,
            SUM(CASE WHEN ab_winner=1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as win_rate
        FROM generations
        WHERE pattern_id IS NOT NULL
        GROUP BY pattern_id
        HAVING uses >= 10
    """).fetchall()

    def update_status(cur, pattern_id, status):
        cur.execute("""
            UPDATE library
            SET status=?, last_updated=datetime('now')
            WHERE pattern_id=?
        """, (status, pattern_id))

    for pattern_id, uses, avg_rating, avg_implicit, win_rate in candidates:
        score = (avg_rating * 0.60) + (avg_implicit * 0.20) + (win_rate * 5 * 0.20)

        if score >= 4.5:
            update_status(cursor, pattern_id, "gold")
        elif score >= 4.0:
            update_status(cursor, pattern_id, "standard")
        elif score < 2.0:
            update_status(cursor, pattern_id, "deprecated")

    cursor.execute("""
        DELETE FROM library
        WHERE status='deprecated'
        AND julianday('now') - julianday(last_updated) > 30
    """)

    conn.commit()
    conn.close()
    print("OK: evolve_library ran")

if __name__ == "__main__":
    evolve_library()
