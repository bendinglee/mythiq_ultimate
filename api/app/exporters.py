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

def export_outcomes_csv(conn, limit: int = 100) -> str:
    """
    Export recent outcomes to CSV.

    Hard rule: never raise just because the DB is empty/uninitialized.
    If the outcomes table does not exist yet, return a valid empty CSV.
    """
    header = "ts,kind,ok,detail\n"
    try:
        cur = conn.execute(
            "SELECT ts, kind, ok, detail FROM outcomes ORDER BY ts DESC LIMIT ?",
            (int(limit),),
        )
        rows = cur.fetchall()
    except sqlite3.OperationalError as e:
        if "no such table: outcomes" in str(e):
            return header
        raise

    out = [header]
    for ts, kind, ok, detail in rows:
        def esc(x):
            if x is None:
                return ""
            x = str(x)
            if any(c in x for c in [",", "\n", "\r", '"']):
                x = '"' + x.replace('"', '""') + '"'
            return x
        out.append(f"{esc(ts)},{esc(kind)},{esc(ok)},{esc(detail)}\n")
    return "".join(out)
def export_generations_csv(conn, limit: int = 100) -> str:
    """Export recent generations to CSV.

    Rule: never 500 due to empty/uninitialized DB or schema drift.
    Prefer the current Mythiq schema if present; otherwise fall back to introspection.
    """
    prefer = [
        "ts","feature","prompt","output","meta_json",
        "pattern_id","user_rating","implicit_score","ab_winner","id",
    ]

    try:
        info = conn.execute("PRAGMA table_info(generations)").fetchall()
    except sqlite3.OperationalError:
        return ",".join(prefer) + "\n"

    existing = {row[1] for row in info}
    if not existing:
        return ",".join(prefer) + "\n"

    cols = [c for c in prefer if c in existing]
    if not cols:
        cols = sorted(existing)

    header = ",".join(cols) + "\n"
    q = "SELECT " + ", ".join(cols) + " FROM generations"
    if "ts" in cols:
        q += " ORDER BY ts DESC"
    q += " LIMIT ?"

    try:
        rows = conn.execute(q, (int(limit),)).fetchall()
    except sqlite3.OperationalError as e:
        msg = str(e)
        if ("no such table" in msg) or ("no such column" in msg):
            return header
        raise

    def esc(x):
        if x is None:
            return ""
        x = str(x)
        if any(c in x for c in [",", "\n", "\r", '"']):
            x = '"' + x.replace('"', '""') + '"'
        return x

    out = [header]
    for r in rows:
        out.append(",".join(esc(v) for v in r) + "\n")
    return "".join(out)
