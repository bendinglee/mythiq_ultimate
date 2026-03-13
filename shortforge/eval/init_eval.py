from __future__ import annotations
import sqlite3
from pathlib import Path

DB = Path("shortforge/data/quality.db")
DB.parent.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(DB)

conn.execute("""
CREATE TABLE IF NOT EXISTS clip_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    clip_index INTEGER NOT NULL,
    variant TEXT,
    title TEXT,
    anchor_text TEXT,
    transcript TEXT,
    hook_strength INTEGER,
    source_relevance INTEGER,
    story_clarity INTEGER,
    pacing_smoothness INTEGER,
    visual_framing INTEGER,
    caption_readability INTEGER,
    emotional_payoff INTEGER,
    replayability INTEGER,
    professional_polish INTEGER,
    overall_score REAL,
    chosen INTEGER DEFAULT 0,
    exported INTEGER DEFAULT 0,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

conn.execute("""
CREATE TABLE IF NOT EXISTS pattern_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_id TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    sample_size INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

conn.execute("""
CREATE TABLE IF NOT EXISTS run_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    source_id TEXT,
    clip_count INTEGER,
    avg_score REAL,
    chosen_count INTEGER DEFAULT 0,
    exported_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
conn.close()
print("OK: shortforge/data/quality.db initialized")
