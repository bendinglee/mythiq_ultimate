from __future__ import annotations

import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # repo root
DATA_DIR = ROOT / "data"
DB_PATH = Path(os.environ.get("MYTHIQ_DB_PATH", str(DATA_DIR / "mythiq.db")))
SCHEMA_PATH = Path(os.environ.get("MYTHIQ_SCHEMA_PATH", str(Path(__file__).with_name("schema.sql"))))

def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db() -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    conn = connect()
    try:
        conn.executescript(schema)
        conn.commit()
    finally:
        conn.close()
