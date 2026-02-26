from __future__ import annotations

import csv
import io
import sqlite3
from typing import Iterable, Sequence

CSV_VERSION = "v1"

def _rows_to_csv(headers: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(headers)
    for r in rows:
        w.writerow(list(r))
    return buf.getvalue()

def export_outcomes_csv(conn: sqlite3.Connection, limit: int = 100) -> str:
    limit = max(1, min(int(limit), 10000))
    headers = ["ts", "feature", "key", "reward", "meta_json"]
    cur = conn.execute(
        """
        SELECT ts, feature, key_name, reward, meta_json
        FROM outcomes
        ORDER BY ts DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    )
    return _rows_to_csv(headers, cur.fetchall())

def export_generations_csv(conn: sqlite3.Connection, limit: int = 100) -> str:
    limit = max(1, min(int(limit), 10000))
    headers = ["ts", "feature", "key", "prompt", "output", "meta_json"]
    cur = conn.execute(
        """
        SELECT ts, feature, key_name, prompt, output, meta_json
        FROM generations
        ORDER BY ts DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    )
    return _rows_to_csv(headers, cur.fetchall())
