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
    Export outcomes as CSV.

    Supports multiple schemas and falls back safely.
    """
    import csv
    import io

    cols = [r[1] for r in conn.execute("PRAGMA table_info(outcomes)").fetchall()]
    cset = set(cols)

    if {"ts", "kind", "ok", "detail"}.issubset(cset):
        sel = ["ts", "kind", "ok", "detail"]
        q = "SELECT ts, kind, ok, detail FROM outcomes ORDER BY ts DESC LIMIT ?"
    elif {"ts", "feature", "key", "reward", "meta_json"}.issubset(cset):
        sel = ["ts", "feature", "key", "reward", "meta_json"]
        q = "SELECT ts, feature, key, reward, meta_json FROM outcomes ORDER BY ts DESC LIMIT ?"
    else:
        sel = cols[:] if cols else []
        if cols:
            q = "SELECT * FROM outcomes ORDER BY 1 DESC LIMIT ?"
        else:
            q = "SELECT * FROM outcomes LIMIT ?"

    cur = conn.execute(q, (int(limit),))
    rows = cur.fetchall()

    buf = io.StringIO()
    w = csv.writer(buf)
    # header: real names if known, else generic
    if sel:
        w.writerow(sel)
    elif rows:
        w.writerow([f"col_{i}" for i in range(len(rows[0]))])
    else:
        w.writerow([])
    for r in rows:
        w.writerow(list(r))
    return buf.getvalue()


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

# -------------------------
# Schema-adaptive outcomes exporter (override-safe)
# -------------------------
def export_outcomes_csv(conn, limit: int = 100) -> str:
    """
    Export outcomes as CSV (schema-adaptive).

    Supports:
      A) outcomes(ts, kind, ok, detail, ...)
      B) outcomes(ts, feature, key, reward, meta_json, ...)
      C) outcomes(id, ts, feature, key_name, reward, meta_json, ...)  <-- your current schema
    Falls back to SELECT * if unknown.
    """
    import csv
    import io
    import sqlite3

    def _try(q: str, header: list[str]):
        try:
            cur = conn.execute(q, (int(limit),))
            return header, cur.fetchall()
        except sqlite3.OperationalError:
            return None, None

    # Try in a safe order (most specific first)
    for q, hdr in [
        ("SELECT ts, kind, ok, detail FROM outcomes ORDER BY ts DESC LIMIT ?", ["ts","kind","ok","detail"]),
        ("SELECT ts, feature, key, reward, meta_json FROM outcomes ORDER BY ts DESC LIMIT ?", ["ts","feature","key","reward","meta_json"]),
        ("SELECT ts, feature, key_name, reward, meta_json FROM outcomes ORDER BY ts DESC LIMIT ?", ["ts","feature","key_name","reward","meta_json"]),
        ("SELECT id, ts, feature, key_name, reward, meta_json FROM outcomes ORDER BY ts DESC LIMIT ?", ["id","ts","feature","key_name","reward","meta_json"]),
    ]:
        header, rows = _try(q, hdr)
        if header is not None:
            break
    else:
        # Fallback: export whatever exists
        cols = [r[1] for r in conn.execute("PRAGMA table_info(outcomes)").fetchall()]
        if cols:
            cur = conn.execute("SELECT * FROM outcomes ORDER BY 1 DESC LIMIT ?", (int(limit),))
            rows = cur.fetchall()
            header = cols
        else:
            header = ["error"]
            rows = [["outcomes table not found or has no columns"]]

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    for r in rows:
        w.writerow(list(r))
    return buf.getvalue()
