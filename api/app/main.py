from __future__ import annotations

import os
import sqlite3
from pathlib import Path
import time
import json
import uuid
from typing import Any, Dict, Optional, List

import httpx
from fastapi import FastAPI, Body
from pydantic import BaseModel, Field

APP_START = time.time()


def route_request(prompt: str) -> dict:
    t = (prompt or "").lower()

    # very simple heuristic router v1 (replace later with embeddings/qdrant)
    scores = {
        "game": 0.0,
        "short": 0.0,
        "code": 0.0,
        "image": 0.0,
        "doc": 0.0,
        "animation": 0.0,
        "cartoon": 0.0,
        "text": 0.2,
    }

    def bump(key, v): scores[key] = max(scores[key], v)

    if any(k in t for k in ["phaser", "unity", "game", "level", "boss", "enemy", "loop"]): bump("game", 0.85)
    if any(k in t for k in ["tiktok", "reels", "shorts", "clip", "caption"]): bump("short", 0.85)
    if any(k in t for k in ["python", "typescript", "bug", "refactor", "api", "function", "tests"]): bump("code", 0.85)
    if any(k in t for k in ["image", "logo", "thumbnail", "sd", "comfyui"]): bump("image", 0.85)
    if any(k in t for k in ["doc", "documentation", "spec", "prd", "proposal"]): bump("doc", 0.8)
    if any(k in t for k in ["animate", "interpolate", "film", "keyframe"]): bump("animation", 0.8)
    if any(k in t for k in ["cartoon", "comic", "storyboard"]): bump("cartoon", 0.8)

    top = max(scores, key=scores.get)
    sorted_feats = sorted(scores, key=scores.get)
    second = sorted_feats[-2]
    conf = float(scores[top])
    secondary = second if float(scores[second]) >= 0.40 else None

    return {"feature": top, "confidence": conf, "secondary": secondary, "scores": scores}

OLLAMA_BASE = os.environ.get("OLLAMA_BASE", "http://127.0.0.1:11434")
DB_PATH = os.environ.get("MYTHIQ_DB_PATH", "mythiq.sqlite")

app = FastAPI(title="Mythiq Ultimate API", version="0.1.0")


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)

    # generations (logging)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS generations(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts INTEGER NOT NULL,
      feature TEXT NOT NULL,
      prompt TEXT NOT NULL,
      output TEXT NOT NULL,
      meta_json TEXT,
      pattern_id TEXT,
      user_rating REAL,
      implicit_score REAL,
      ab_winner INTEGER
    )
    """)

    # stored prompt patterns (system/prefix)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS patterns(
      pattern_id TEXT PRIMARY KEY,
      system_prompt TEXT,
      prefix TEXT,
      updated_ts INTEGER NOT NULL
    )
    """)

    # pattern library status table (promotion/demotion)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS library(
      pattern_id TEXT PRIMARY KEY,
      status TEXT NOT NULL,
      last_updated TEXT NOT NULL
    )
    """)

    # AB voting (one row per vote; optional voter_id for idempotency)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS ab_votes(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts INTEGER NOT NULL,
      ab_group TEXT NOT NULL,
      vote TEXT NOT NULL,            -- 'A' or 'B'
      user_rating REAL,
      voter_id TEXT
    )
    """)

    conn.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS ab_votes_unique_voter
    ON ab_votes(ab_group, voter_id)
    WHERE voter_id IS NOT NULL
    """)

    # AB decisions (frozen winner once decided)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS ab_decisions(
      ab_group TEXT PRIMARY KEY,
      winner TEXT NOT NULL,          -- 'A' or 'B'
      decided_ts INTEGER NOT NULL,
      votes_a INTEGER NOT NULL,
      votes_b INTEGER NOT NULL
    )
    """)

    return conn



def apply_ab_to_library(conn, ab_group: str) -> None:
    row = conn.execute("SELECT winner, votes_a, votes_b FROM ab_decisions WHERE ab_group=?", (ab_group,)).fetchone()
    if not row:
        return
    winner, a, b = row[0], int(row[1]), int(row[2])

    pat = conn.execute(
        "SELECT pattern_id FROM generations WHERE meta_json LIKE ? AND pattern_id IS NOT NULL LIMIT 1",
        (f'%\"ab_group\":\"{ab_group}\"%',),
    ).fetchone()
    if not pat:
        return
    pattern_id = pat[0]

    delta = (a - b) if winner == "A" else (b - a)
    promote_at = 3
    demote_at = -3

    if delta >= promote_at:
        status = "active"
    elif delta <= demote_at:
        status = "shadow"
    else:
        status = "candidate"

    conn.execute(
        "INSERT OR REPLACE INTO library(pattern_id, status, last_updated) VALUES(?,?,datetime('now'))",
        (pattern_id, status),
    )

class RunIn(BaseModel):
    prompt: str = Field(..., min_length=1)
    feature: str = Field("text")  # game|short|code|image|doc|animation|cartoon|text
    model: str = Field("llama3.2:3b")
    system: Optional[str] = None
    pattern_id: str | None = None
    user_rating: float | None = None
    implicit_score: float | None = None
    ab_winner: int | None = None


class RunOut(BaseModel):
    ok: bool
    feature: str
    model: str
    output: str
    ms: int


@app.get("/readyz")
def readyz() -> Dict[str, Any]:
    return {"ok": True, "uptime_s": int(time.time() - APP_START)}


# --- stable chat contract (v1) + metrics ---
LOG_DIR = Path("/app/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
METRICS_PATH = LOG_DIR / "metrics.jsonl"

class ChatIn(BaseModel):
    prompt: str = Field(..., min_length=1)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(256, ge=1, le=4096)
    seed: int | None = None

class ChatOut(BaseModel):
    ok: bool
    output: str
    ms: int
    model: str | None = None
    prompt_chars: int
    output_chars: int

def _append_metric(obj: dict) -> None:
    # best-effort: never break requests due to logging
    try:
        METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with METRICS_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    except Exception:
        pass

@app.post("/v1/chat", response_model=ChatOut)
def v1_chat(inp: ChatIn):
    t0 = time.time()


    # Call Ollama directly (stable wiring)
    model = os.environ.get("MYTHIQ_MODEL", "llama3.2:3b")

    payload = {
        "model": model,
        "prompt": inp.prompt,
        "stream": False,
        "options": {
            "temperature": float(inp.temperature),
            "num_predict": int(inp.max_tokens),
        }
    }
    if inp.seed is not None:
        payload["options"]["seed"] = int(inp.seed)

    out = ""
    err = None
    try:
        # inside compose network: service name "ollama"
        with httpx.Client(timeout=60.0) as client:
            r = client.post("http://ollama:11434/api/generate", json=payload)
            r.raise_for_status()
            data = r.json()
            out = str(data.get("response", ""))
    except Exception as e:
        err = str(e)
        out = f"OLLAMA_ERROR: {err}"


    ms = int((time.time() - t0) * 1000)

    resp = {
        "ok": True,
        "output": str(out),
        "ms": ms,
        "model": model,
        "prompt_chars": len(inp.prompt),
        "output_chars": len(str(out)),
    }

    _append_metric({
        "ts": int(time.time()),
        "route": "/v1/chat",
        "ms": ms,
        "prompt_chars": resp["prompt_chars"],
        "output_chars": resp["output_chars"],
        "model": model,
        "error": err,

    })

    return resp





@app.get("/v1/metrics/tail")
def metrics_tail(n: int = 50):
    n = max(1, min(int(n), 500))
    try:
        if not METRICS_PATH.exists():
            return {"ok": True, "lines": []}
        lines = METRICS_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()
        return {"ok": True, "lines": lines[-n:]}
    except Exception as e:
        return {"ok": False, "error": str(e), "lines": []}
@app.get("/health")
def health() -> Dict[str, Any]:
    conn = db()
    conn.execute("CREATE TABLE IF NOT EXISTS healthcheck(x INTEGER)")
    conn.close()
    return {"ok": True}


@app.post("/v1/route")
def route(inp: RunIn) -> Dict[str, Any]:
    r = route_request(inp.prompt)
    return {"ok": True, **r}



@app.get("/v1/library")
def library() -> Dict[str, Any]:
    conn = db()
    try:
        rows = conn.execute(
            "SELECT pattern_id, status, last_updated FROM library ORDER BY status, pattern_id"
        ).fetchall()
    except Exception:
        rows = []
    conn.close()
    return {
        "ok": True,
        "rows": [{"pattern_id": r[0], "status": r[1], "last_updated": r[2]} for r in rows],
    }



class PatternIn(BaseModel):
    system_prompt: str | None = None
    prefix: str | None = None





class RunABOut(BaseModel):
    ok: bool
    feature: str
    model: str
    ab_group: str
    output_a: str
    output_b: str
    ms_a: int
    ms_b: int


class ABPickIn(BaseModel):
    ab_group: str = Field(..., min_length=1)
    winner: str = Field(..., pattern="^(A|B)$")
    user_rating: float | None = None


def _ollama_generate(model: str, prompt: str, system: str | None) -> tuple[str, int]:
    t0 = time.time()
    payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    if system:
        payload["system"] = system
    # Inside container, OLLAMA_BASE defaults to http://127.0.0.1:11434; in compose it may be overridden.
    with httpx.Client(timeout=180.0) as client:
        r = client.post(f"{OLLAMA_BASE}/api/generate", json=payload)
        r.raise_for_status()
        j = r.json()
    out = j.get("response") or ""
    ms = int((time.time() - t0) * 1000)
    return out, ms


def _log_generation(conn: sqlite3.Connection, *, feature: str, prompt: str, output: str, meta: dict,
                    pattern_id: str | None, user_rating: float | None, implicit_score: float | None, ab_winner: int | None) -> None:
    conn.execute(
        "INSERT INTO generations(ts, feature, prompt, output, meta_json, pattern_id, user_rating, implicit_score, ab_winner) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        (
            int(time.time()),
            feature,
            prompt,
            output,
            json.dumps(meta, separators=(",", ":")),
            pattern_id,
            user_rating,
            implicit_score,
            ab_winner,
        ),
    )








class AbPickIn(BaseModel):
    ab_group: str = Field(..., min_length=4)
    winner: str = Field(..., pattern="^[AB]$")
    user_rating: float | None = None
    voter_id: str | None = None   # optional idempotency key


@app.post("/v1/ab_pick")
def ab_pick(inp: AbPickIn = Body(...)) -> Dict[str, Any]:
    conn = db()
    now = int(time.time())
    try:
        # If already decided, return frozen result
        dec = conn.execute(
            "SELECT winner, votes_a, votes_b FROM ab_decisions WHERE ab_group=?",
            (inp.ab_group,),
        ).fetchone()
        if dec:
            return {
                "ok": True,
                "ab_group": inp.ab_group,
                "winner": dec[0],
                "votes": {"A": dec[1], "B": dec[2]},
                "idempotent": True,
                "decided": True,
            }

        # Insert vote (if voter_id provided, unique index prevents duplicates)
        try:
            conn.execute(
                "INSERT INTO ab_votes(ts, ab_group, vote, user_rating, voter_id) VALUES(?,?,?,?,?)",
                (now, inp.ab_group, inp.winner, inp.user_rating, inp.voter_id),
            )
            conn.commit()
            inserted = True
        except Exception:
            inserted = False

        # Tally votes
        a = conn.execute(
            "SELECT COUNT(1) FROM ab_votes WHERE ab_group=? AND vote='A'",
            (inp.ab_group,),
        ).fetchone()[0]
        b = conn.execute(
            "SELECT COUNT(1) FROM ab_votes WHERE ab_group=? AND vote='B'",
            (inp.ab_group,),
        ).fetchone()[0]
        total = a + b

        # Decide rule:
        # - decide at 5 total votes, OR
        # - early stop if lead >= 3 with at least 3 votes total
        decided = False
        winner = None
        if total >= 5 or (total >= 3 and abs(a - b) >= 3):
            winner = "A" if a >= b else "B"
            conn.execute(
                "INSERT OR REPLACE INTO ab_decisions(ab_group, winner, decided_ts, votes_a, votes_b) VALUES(?,?,?,?,?)",
                (inp.ab_group, winner, now, a, b),
            )
            conn.commit()
            
            apply_ab_to_library(conn, inp.ab_group)
            decided = True

        return {
            "ok": True,
            "ab_group": inp.ab_group,
            "winner": winner if decided else None,
            "votes": {"A": a, "B": b},
            "inserted": inserted,
            "decided": decided,
        }
    finally:
        conn.close()

@app.post("/v1/run_ab", response_model=RunABOut)
def run_ab(inp: RunIn) -> RunABOut:
    # Pull pattern (optional)
    p_system = None
    p_prefix = None
    if inp.pattern_id:
        conn = db()
        row = conn.execute(
            "SELECT system_prompt, prefix FROM patterns WHERE pattern_id=?",
            (inp.pattern_id,),
        ).fetchone()
        conn.close()
        if row:
            p_system, p_prefix = row[0], row[1]

    system = inp.system or p_system
    effective_prompt = "\n\n".join([x for x in [(p_prefix or "").strip(), (inp.prompt or "").strip()] if x])

    # Two deterministic-ish variants (same prompt/system; variation comes from model randomness)
    ab_group = uuid.uuid4().hex[:12]

    out_a, ms_a = _ollama_generate(inp.model, effective_prompt, system)
    out_b, ms_b = _ollama_generate(inp.model, effective_prompt, system)

    conn = db()
    try:
        _log_generation(
            conn,
            feature=inp.feature,
            prompt=inp.prompt,
            output=out_a,
            meta={
                "pattern_id": inp.pattern_id,
                "ab_group": ab_group,
                "variant": "A",
            },
            pattern_id=inp.pattern_id,
            user_rating=None,
            implicit_score=None,
            ab_winner=None,
        )
        _log_generation(
            conn,
            feature=inp.feature,
            prompt=inp.prompt,
            output=out_b,
            meta={
                "pattern_id": inp.pattern_id,
                "ab_group": ab_group,
                "variant": "B",
            },
            pattern_id=inp.pattern_id,
            user_rating=None,
            implicit_score=None,
            ab_winner=None,
        )
        conn.commit()
    finally:
        conn.close()

    return RunABOut(
        ok=True,
        feature=inp.feature,
        model=inp.model,
        ab_group=ab_group,
        output_a=out_a,
        output_b=out_b,
        ms_a=ms_a,
        ms_b=ms_b,
    )



    return {"ok": True, "ab_group": inp.ab_group, "winner": inp.winner}

@app.get("/v1/patterns")
def list_patterns() -> Dict[str, Any]:
    conn = db()
    rows = conn.execute(
        "SELECT pattern_id, system_prompt, prefix, updated_ts FROM patterns ORDER BY pattern_id"
    ).fetchall()
    conn.close()
    return {
        "ok": True,
        "rows": [
            {"pattern_id": r[0], "system_prompt": r[1], "prefix": r[2], "updated_ts": r[3]}
            for r in rows
        ],
    }


@app.get("/v1/patterns/{pattern_id}")
def get_pattern(pattern_id: str) -> Dict[str, Any]:
    conn = db()
    r = conn.execute(
        "SELECT pattern_id, system_prompt, prefix, updated_ts FROM patterns WHERE pattern_id=?",
        (pattern_id,),
    ).fetchone()
    conn.close()
    if not r:
        return {"ok": False, "detail": "not found"}
    return {"ok": True, "row": {"pattern_id": r[0], "system_prompt": r[1], "prefix": r[2], "updated_ts": r[3]}}


@app.put("/v1/patterns/{pattern_id}")
def put_pattern(pattern_id: str, inp: PatternIn) -> Dict[str, Any]:
    conn = db()
    conn.execute(
        "INSERT INTO patterns(pattern_id, system_prompt, prefix, updated_ts) VALUES(?,?,?,?) "
        "ON CONFLICT(pattern_id) DO UPDATE SET "
        "system_prompt=excluded.system_prompt, prefix=excluded.prefix, updated_ts=excluded.updated_ts",
        (pattern_id, inp.system_prompt, inp.prefix, int(time.time())),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "pattern_id": pattern_id}

@app.post("/v1/run", response_model=RunOut)
async def run(inp: RunIn) -> RunOut:
    t0 = time.time()

    # Apply pattern library (system/prefix) if present
    p_system = None
    p_prefix = None
    if inp.pattern_id:
        conn0 = db()
        try:
            r0 = conn0.execute(
                "SELECT system_prompt, prefix FROM patterns WHERE pattern_id=?",
                (inp.pattern_id,),
            ).fetchone()
            if r0:
                p_system, p_prefix = r0[0], r0[1]
        finally:
            conn0.close()

    effective_prompt = "\n\n".join(
        [x for x in [(p_prefix or "").strip(), (inp.prompt or "").strip()] if x]
    )
    payload: Dict[str, Any] = {
        "model": inp.model,
        "prompt": effective_prompt,
        "stream": False,
        "options": {
            "num_predict": int(os.environ.get("OLLAMA_NUM_PREDICT", "256")),
        },
    }

    if inp.system:
        payload["system"] = inp.system
    elif p_system:
        payload["system"] = p_system

    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0, read=120.0, write=120.0)) as client:
        r = await client.post(f"{OLLAMA_BASE}/api/generate", json=payload)
        r.raise_for_status()
        data = r.json()

    out = (data.get("response") or "").strip()

    conn = db()
    conn.execute(
        "INSERT INTO generations(ts, feature, prompt, output, meta_json, pattern_id, user_rating, implicit_score, ab_winner) VALUES(?,?,?,?,?,?,?,?,?)",
        (
            int(time.time()),
            inp.feature,
            inp.prompt,
            out,
            json.dumps({
                "pattern_id": inp.pattern_id,
                "user_rating": inp.user_rating,
                "implicit_score": inp.implicit_score,
                "ab_winner": inp.ab_winner,
            }, separators=(",", ":")),
            inp.pattern_id,
            inp.user_rating,
            inp.implicit_score,
            inp.ab_winner,
        ),
    )
    conn.commit()
    conn.close()

    return RunOut(ok=True, feature=inp.feature, model=inp.model, output=out, ms=int((time.time() - t0) * 1000))



