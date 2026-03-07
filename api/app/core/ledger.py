from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional


DB_PATH = Path(os.getenv("MYTHIQ_CORE_DB", "data/mythiq_core.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            ts REAL NOT NULL,
            project_id TEXT NOT NULL,
            prompt TEXT NOT NULL,
            goal TEXT,
            mode TEXT NOT NULL,
            feature TEXT NOT NULL,
            confidence REAL NOT NULL,
            plan_json TEXT NOT NULL,
            result_json TEXT NOT NULL,
            quality_json TEXT NOT NULL,
            repaired INTEGER NOT NULL DEFAULT 0,
            latency_ms INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pattern_memory (
            id TEXT PRIMARY KEY,
            ts REAL NOT NULL,
            feature TEXT NOT NULL,
            prompt_hint TEXT NOT NULL,
            pattern_key TEXT NOT NULL,
            score REAL NOT NULL,
            uses INTEGER NOT NULL DEFAULT 1,
            last_run_id TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS project_state (
            project_id TEXT PRIMARY KEY,
            ts REAL NOT NULL,
            state_json TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def new_run_id() -> str:
    return f"r_{uuid.uuid4().hex[:12]}"


def new_project_id() -> str:
    return f"p_{uuid.uuid4().hex[:12]}"


def save_run(
    *,
    run_id: str,
    project_id: str,
    prompt: str,
    goal: Optional[str],
    mode: str,
    feature: str,
    confidence: float,
    plan_json: Dict[str, Any],
    result_json: Dict[str, Any],
    quality_json: Dict[str, Any],
    repaired: bool,
    latency_ms: int,
) -> None:
    conn = db()
    conn.execute(
        """
        INSERT OR REPLACE INTO runs
        (run_id, ts, project_id, prompt, goal, mode, feature, confidence, plan_json, result_json, quality_json, repaired, latency_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            time.time(),
            project_id,
            prompt,
            goal,
            mode,
            feature,
            confidence,
            json.dumps(plan_json, ensure_ascii=False),
            json.dumps(result_json, ensure_ascii=False),
            json.dumps(quality_json, ensure_ascii=False),
            1 if repaired else 0,
            latency_ms,
        ),
    )
    conn.commit()
    conn.close()


def save_project_state(project_id: str, state: Dict[str, Any]) -> None:
    conn = db()
    conn.execute(
        """
        INSERT OR REPLACE INTO project_state (project_id, ts, state_json)
        VALUES (?, ?, ?)
        """,
        (project_id, time.time(), json.dumps(state, ensure_ascii=False)),
    )
    conn.commit()
    conn.close()


def load_project_state(project_id: str) -> Optional[Dict[str, Any]]:
    conn = db()
    row = conn.execute(
        "SELECT state_json FROM project_state WHERE project_id = ?",
        (project_id,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return json.loads(row["state_json"])


def record_pattern(feature: str, prompt_hint: str, pattern_key: str, score: float, run_id: str) -> None:
    conn = db()
    row = conn.execute(
        """
        SELECT id, uses, score FROM pattern_memory
        WHERE feature = ? AND prompt_hint = ? AND pattern_key = ?
        """,
        (feature, prompt_hint, pattern_key),
    ).fetchone()

    if row:
        new_uses = int(row["uses"]) + 1
        new_score = ((float(row["score"]) * int(row["uses"])) + score) / new_uses
        conn.execute(
            """
            UPDATE pattern_memory
            SET ts = ?, uses = ?, score = ?, last_run_id = ?
            WHERE id = ?
            """,
            (time.time(), new_uses, new_score, run_id, row["id"]),
        )
    else:
        conn.execute(
            """
            INSERT INTO pattern_memory (id, ts, feature, prompt_hint, pattern_key, score, uses, last_run_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"pm_{uuid.uuid4().hex[:12]}",
                time.time(),
                feature,
                prompt_hint,
                pattern_key,
                score,
                1,
                run_id,
            ),
        )
    conn.commit()
    conn.close()


def best_pattern(feature: str, prompt_hint: str) -> Optional[Dict[str, Any]]:
    conn = db()
    row = conn.execute(
        """
        SELECT pattern_key, score, uses
        FROM pattern_memory
        WHERE feature = ? AND prompt_hint = ?
        ORDER BY score DESC, uses DESC, ts DESC
        LIMIT 1
        """,
        (feature, prompt_hint),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {"pattern_key": row["pattern_key"], "score": row["score"], "uses": row["uses"]}
