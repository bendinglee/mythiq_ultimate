from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path("data/mythiq.sqlite")

SCHEMA = """
CREATE TABLE IF NOT EXISTS game_builds (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  game_id TEXT NOT NULL,
  title TEXT NOT NULL,
  prompt TEXT NOT NULL,
  created_at TEXT NOT NULL,
  duration_ms INTEGER NOT NULL,
  status TEXT NOT NULL,
  error TEXT
);
CREATE INDEX IF NOT EXISTS idx_game_builds_created_at ON game_builds(created_at);
CREATE INDEX IF NOT EXISTS idx_game_builds_game_id ON game_builds(game_id);
"""

def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn

def log_game_build(
    *, game_id: str, title: str, prompt: str, created_at: str,
    duration_ms: int, status: str, error: Optional[str] = None
) -> None:
    conn = _conn()
    with conn:
        conn.execute(
            "INSERT INTO game_builds (game_id,title,prompt,created_at,duration_ms,status,error) "
            "VALUES (?,?,?,?,?,?,?)",
            (game_id, title, prompt, created_at, duration_ms, status, error),
        )
    conn.close()

def metrics() -> Dict[str, Any]:
    conn = _conn()
    total = conn.execute("SELECT COUNT(*) AS n FROM game_builds").fetchone()["n"]
    ok = conn.execute("SELECT COUNT(*) AS n FROM game_builds WHERE status='ok'").fetchone()["n"]
    conn.close()
    return {"total_builds": total, "success_rate": (ok / total) if total else 0.0}

def last_builds(limit: int = 20) -> List[Dict[str, Any]]:
    conn = _conn()
    rows = conn.execute(
        "SELECT game_id,title,prompt,created_at,duration_ms,status,error "
        "FROM game_builds ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
