from __future__ import annotations
import shutil
import time
from datetime import datetime, timezone
from api.app import db as mythiq_db

import zipfile

import threading

import os
import sqlite3
from pathlib import Path
import time
START_TS = time.time()

import json
import uuid
from typing import Any, Dict, Optional, List

import httpx
from fastapi import FastAPI, Body, Response
from .db import init_db, connect
from .exporters import export_outcomes_csv, export_generations_csv
from fastapi.responses import FileResponse
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
DB_PATH = Path(os.environ.get("MYTHIQ_DB_PATH", str(Path("data/mythiq.db"))))
app = FastAPI(title="Mythiq Ultimate API", version="0.1.0")


def _pydantic_rebuild_all_models() -> None:
    """
    Fail fast if any Pydantic models have unresolved ForwardRefs.
    Rebuild ONLY concrete Pydantic BaseModel subclasses (avoid false positives).
    """
    bad: list[str] = []
    for name, obj in list(globals().items()):
        if not isinstance(obj, type):
            continue
        # Must be a pydantic model class (concrete)
        try:
            if not issubclass(obj, BaseModel):
                continue
        except TypeError:
            continue
        # Skip base classes / generics / partials
        if obj is BaseModel:
            continue
        if not hasattr(obj, "__pydantic_fields__"):
            continue
        if hasattr(obj, "__pydantic_generic_metadata__"):
            continue

        try:
            obj.model_rebuild(force=True)
        except Exception as e:
            bad.append(f"{name}: {e}")

    if bad:
        raise RuntimeError("Pydantic model rebuild failed: " + " | ".join(bad))

@app.on_event("startup")
def _startup_warmup():
    # Enable with: MYTHIQ_WARMUP=1
    if os.environ.get("MYTHIQ_WARMUP") != "1":
        return

    # Ensure DB schema is created at boot (migrations)
    try:
        c = db()
        c.close()
    except Exception:
        # DB boot should not take the whole server down; endpoints will surface errors if any
        pass
    _warmup_ollama_async()

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

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS outcomes (
          ts INTEGER NOT NULL,
          feature TEXT NOT NULL,
          key TEXT NOT NULL,
          reward REAL NOT NULL,
          meta_json TEXT
        );
        """
    )
    # stored prompt patterns (system/prefix)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS patterns(
      pattern_id TEXT PRIMARY KEY,
      system_prompt TEXT,
      prefix TEXT,
      updated_ts INTEGER NOT NULL
    )
    """)

    # pattern variants for A/B tests
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pattern_variants(
          pattern_id TEXT NOT NULL,
          variant TEXT NOT NULL,
          system_prompt TEXT,
          prefix TEXT,
          updated_ts INTEGER NOT NULL,
          PRIMARY KEY(pattern_id, variant)
        );
        """
    )
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



    # Guard: older schemas may not have generations.pattern_id yet



    try:



        cols = [r[1] for r in conn.execute("PRAGMA table_info(generations)").fetchall()]



    except sqlite3.OperationalError:



        return



    if "pattern_id" not in cols:



        return

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





@app.get("/v1/schema/health")
def schema_health():
    _pydantic_rebuild_all_models()
    return {"ok": True}

@app.get("/v1/debug/paths")
def debug_paths():
    return {
        "DB_PATH": str(DB_PATH),
        "LOG_DIR": str(LOG_DIR),
        "EXPORTS_DIR": str(EXPORTS_DIR),
    }

# --- stable chat contract (v1) + metrics ---
LOG_DIR = Path(os.environ.get("MYTHIQ_LOG_DIR", str(Path("data/logs"))))
LOG_DIR.mkdir(parents=True, exist_ok=True)
METRICS_PATH = LOG_DIR / "metrics.jsonl"



def _warmup_ollama_async() -> None:
    if os.environ.get("MYTHIQ_WARMUP", "1") not in ("1", "true", "TRUE", "yes", "YES"):
        return

    def run():
        t0 = time.time()
        err = None
        model = os.environ.get("MYTHIQ_MODEL", "llama3.2:3b")
        try:
            payload = {
                "model": model,
                "prompt": "warmup",
                "stream": False,
                "options": {"temperature": 0.0, "num_predict": 1},
            }
            with httpx.Client(timeout=60.0) as client:
                r = client.post("http://ollama:11434/api/generate", json=payload)
                r.raise_for_status()
        except Exception as e:
            err = str(e)

        ms = int((time.time() - t0) * 1000)
        _append_metric({
            "ts": int(time.time()),
            "route": "warmup",
            "ms": ms,
            "model": model,
            "error": err,
        })

    threading.Thread(target=run, daemon=True).start()
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



# =========================
# Router v3 + Pipeline Core
# =========================
from typing import Optional, List


def _infer_game_download_url(output: str):
    try:
        out = str(output or "")
        if not out.startswith("GAME_BUNDLE_ZIP:"):
            return None
        import os
        bn = os.path.basename(out.split(":", 1)[1].strip())
        parts = bn.split("_")
        # expected: g_<ts>_<hex>_...
        if len(parts) < 3 or parts[0] != "g":
            return None
        game_id = "_".join(parts[:3])
        return f"/v1/game/download/{game_id}"
    except Exception:
        return None

class RouteV3In(BaseModel):
    prompt: str
    # optional hints
    want: Optional[str] = None  # user-provided feature hint
    max_secondary: int = 1

class RouteV3Out(BaseModel):
    ok: bool = True
    feature: str
    confidence: float
    secondary: List[str] = []
    scores: Dict[str, float] = {}

class ExecuteIn(BaseModel):
    prompt: str
    want: Optional[str] = None
    # shared generation knobs
    temperature: float = 0.2
    max_tokens: int = 256
    # optional metadata
    pattern_id: Optional[str] = None

def _score_router(prompt: str) -> Dict[str, float]:
    t = (prompt or "").lower()
    scores: Dict[str, float] = {
        "text": 0.10,
        "games": 0.00,
        "shorts": 0.00,
        "images": 0.00,
        "docs": 0.00,
        "code": 0.00,
        "animation": 0.00,
    }

    def bump(k: str, v: float):
        scores[k] = max(scores.get(k, 0.0), v)

    # crude keyword router (upgrade later to learned router)
    if any(w in t for w in ["game", "phaser", "arcade", "level", "mechanic", "boss", "sprites", "tilemap"]):
        bump("games", 0.85)
    if any(w in t for w in ["short", "tiktok", "reels", "clip", "viral", "caption", "hook", "montage"]):
        bump("shorts", 0.85)
    if any(w in t for w in ["image", "thumbnail", "cover", "prompt", "sd", "comfy", "style", "cartoon", "anime"]):
        bump("images", 0.85)
    if any(w in t for w in ["document", "essay", "script", "outline", "report", "citations", "bibliography", "plagiarism"]):
        bump("docs", 0.80)
    if any(w in t for w in ["code", "bug", "python", "typescript", "fastapi", "docker", "api", "fix", "error", "stacktrace"]):
        bump("code", 0.80)
    if any(w in t for w in ["animate", "animation", "storyboard", "shot", "scene", "comfyui svd", "frames"]):
        bump("animation", 0.80)

    # default text if nothing else is strong
    if max(scores.values()) < 0.50:
        bump("text", 0.75)

    return scores

def route_v3_core(prompt: str, want: Optional[str] = None, max_secondary: int = 1) -> Dict[str, Any]:
    scores = _score_router(prompt)
    if want:
        w = want.strip().lower()
        if w in scores:
            scores[w] = max(scores[w], 0.95)

    top = max(scores, key=lambda k: scores[k])
    conf = float(scores[top])

    # secondary suggestions (exclude top)
    rest = sorted([k for k in scores.keys() if k != top], key=lambda k: scores[k], reverse=True)
    secondary = [k for k in rest if scores[k] >= 0.60][: max(0, int(max_secondary))]

    return {"feature": top, "confidence": conf, "secondary": secondary, "scores": scores}

@app.post("/v1/route_v3", response_model=RouteV3Out)
def route_v3(inp: RouteV3In):
    r = route_v3_core(inp.prompt, want=inp.want, max_secondary=inp.max_secondary)
    return {"ok": True, **r}

# -------------------------
# Universal pipeline wrapper
# -------------------------


# -------------------------
# Game builder (Phaser 3)
# -------------------------
EXPORTS_DIR = Path(os.environ.get("MYTHIQ_EXPORTS_DIR", str(Path("data/exports"))))
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

def _safe_slug(x: str) -> str:
    import re
    x = (x or "game").strip().lower()
    x = re.sub(r'[^a-z0-9]+', '-', x).strip('-')
    return x[:50] or "game"

def build_phaser_game_bundle(title: str, prompt: str) -> dict:
    """
    Generates a minimal Phaser game bundle:
      - index.html
      - game.js
      - style.css
    Then zips it to /app/state/exports/<id>.zip
    """
    gid = _new_id("g")
    slug = _safe_slug(title or "mythiq-game")
    outdir = EXPORTS_DIR / f"{gid}_{slug}"
    outdir.mkdir(parents=True, exist_ok=True)

    (outdir / "style.css").write_text("""html,body{margin:0;padding:0;background:#0b0f14;color:#e6edf3;font-family:system-ui}
#game{width:100vw;height:100vh} .hud{position:fixed;left:12px;top:12px;font-size:14px;opacity:.9}
""", encoding="utf-8")

    (outdir / "index.html").write_text(f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{title}</title>
  <link rel="stylesheet" href="style.css"/>
  <script src="https://cdn.jsdelivr.net/npm/phaser@3/dist/phaser.min.js"></script>
</head>
<body>
  <div class="hud"><b>{title}</b><div id="score">score: 0</div></div>
  <div id="game"></div>
  <script src="game.js"></script>
</body>
</html>
""", encoding="utf-8")

    # Simple endless “dodge + collect” loop. Upgrade later via LLM-to-spec.
    (outdir / "game.js").write_text(r"""(() => {
  const W = 800, H = 600;

  let score = 0;
  const setScore = (v) => { score = v; document.getElementById("score").textContent = "score: " + score; };

  class MainScene extends Phaser.Scene {
    constructor(){ super("main"); 

CREATE TABLE IF NOT EXISTS outcomes (
  ts INTEGER NOT NULL,
  feature TEXT NOT NULL,
  key TEXT NOT NULL,
  reward REAL NOT NULL,
  meta_json TEXT
);

}
    preload(){}

    create(){
      this.cameras.main.setBackgroundColor("#0b0f14");

      this.player = this.add.rectangle(W/2, H-80, 40, 40, 0x4cc9f0);
      this.physics.add.existing(this.player);
      this.player.body.setCollideWorldBounds(true);

      this.cursors = this.input.keyboard.createCursorKeys();

      this.orbs = this.physics.add.group();
      this.haz = this.physics.add.group();

      this.spawnTimer = 0;
      this.hazTimer = 0;

      setScore(0);

      this.physics.add.overlap(this.player, this.orbs, (p, o) => {
        o.destroy();
        setScore(score + 10);
      });

      this.physics.add.overlap(this.player, this.haz, () => {
        this.scene.restart();
      });
    }

    update(t, dt){
      const speed = 420;
      const body = this.player.body;
      body.setVelocity(0);

      if (this.cursors.left.isDown) body.setVelocityX(-speed);
      if (this.cursors.right.isDown) body.setVelocityX(speed);
      if (this.cursors.up.isDown) body.setVelocityY(-speed);
      if (this.cursors.down.isDown) body.setVelocityY(speed);

      this.spawnTimer += dt;
      this.hazTimer += dt;

      if (this.spawnTimer > 700){
        this.spawnTimer = 0;
        const x = Phaser.Math.Between(30, W-30);
        const orb = this.add.circle(x, -10, 10, 0x80ff72);
        this.physics.add.existing(orb);
        orb.body.setVelocityY(220);
        orb.body.setCircle(10);
        this.orbs.add(orb);
      }

      if (this.hazTimer > 900){
        this.hazTimer = 0;
        const x = Phaser.Math.Between(30, W-30);
        const r = Phaser.Math.Between(14, 24);
        const hz = this.add.circle(x, -20, r, 0xff4d6d);
        this.physics.add.existing(hz);
        hz.body.setVelocityY(320);
        hz.body.setCircle(r);
        this.haz.add(hz);
      }

      // cleanup
      for (const g of [this.orbs, this.haz]){
        g.getChildren().forEach(o => {
          if (o.y > H + 80) o.destroy();
        });
      }
    }
  }

  const config = {
    type: Phaser.AUTO,
    parent: "game",
    width: W,
    height: H,
    physics: { default: "arcade", arcade: { debug: false } },
    scene: [MainScene],
    scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH }
  };

  new Phaser.Game(config);
})();
""", encoding="utf-8")

    zip_path = EXPORTS_DIR / f"{gid}_{slug}.zip"
    if zip_path.exists():
      zip_path.unlink()

    import zipfile
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
      for fp in outdir.rglob("*"):
        if fp.is_file():
          z.write(fp, arcname=fp.relative_to(outdir))

    return {"game_id": gid, "dir": str(outdir), "zip": str(zip_path), "title": title, "prompt": prompt}

def run_pipeline(feature: str, prompt: str, temperature: float, max_tokens: int) -> Dict[str, Any]:
    """
    Option A foundation:
      - retries + timing + structured result
      - stub implementations for non-text features (wire later)
    """
    t0 = time.time()
    attempts = 0
    last_err = None
    out = ""

    # retry policy (upgrade per-feature later)
    max_attempts = 2 if feature in ("shorts", "games") else 1

    while attempts < max_attempts:
        attempts += 1
        try:
            if feature == "text":
                # direct ollama generate
                model = os.environ.get("MYTHIQ_MODEL") or "llama3.2:3b"
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": float(temperature),
                        "num_predict": int(max_tokens),
                    },
                }
                with httpx.Client(timeout=120.0) as client:
                    r = client.post("http://ollama:11434/api/generate", json=payload)
                    r.raise_for_status()
                    data = r.json()
                    out = str(data.get("response", ""))
                return {
                    "ok": True,
                    "feature": feature,
                    "output": out,
                    "ms": int((time.time() - t0) * 1000),
                    "attempts": attempts,
                    "error": None,
                }

            # stubs (wire these next)
            if feature == "games":
                b = build_phaser_game_bundle(title="Mythiq Game", prompt=prompt)
                out = "GAME_BUNDLE_ZIP: " + b["zip"]

            elif feature == "shorts":
                out = "NOT_IMPLEMENTED: shorts pipeline (SceneDetect + Whisper + scorer + FFmpeg + captions)."
            elif feature == "images":
                out = "NOT_IMPLEMENTED: images pipeline (ComfyUI/SD + copyright checks)."
            elif feature == "docs":
                out = "NOT_IMPLEMENTED: docs pipeline (citations + plagiarism checks)."
            elif feature == "code":
                out = "NOT_IMPLEMENTED: code pipeline (gen + tests + sandbox execution)."
            elif feature == "animation":
                out = "NOT_IMPLEMENTED: animation pipeline (storyboard/shot/render workflow)."
            else:
                out = f"NOT_IMPLEMENTED: unknown feature={feature}"

            return {
                "ok": True,
                "feature": feature,
                "output": out,
                "ms": int((time.time() - t0) * 1000),
                "attempts": attempts,
                "error": None,
            }

        except Exception as e:
            last_err = repr(e)

    return {
        "ok": False,
        "feature": feature,
        "output": "",
        "ms": int((time.time() - t0) * 1000),
        "attempts": attempts,
        "error": last_err,
    }

@app.post("/v1/execute")
def execute(inp: ExecuteIn):
    # Route
    r = route_v3_core(inp.prompt, want=inp.want, max_secondary=1)
    feature = r["feature"]
    confidence = float(r["confidence"])

    # Run
    res = run_pipeline(
        feature=feature,
        prompt=inp.prompt,
        temperature=float(inp.temperature),
        max_tokens=int(inp.max_tokens),
    )

    # Persist via existing logger endpoint logic (re-use DB functions directly here)
    db_path = str(DB_PATH) if "DB_PATH" in globals() else None
    db_changes = None
    db_count = None
    db_err = None
    run_id = _new_id("r")

    try:
        con = db_conn()
        try:
            con.execute(
                """INSERT INTO runs
                   (run_id, ts, feature, pattern_id, prompt, output, ms, model, user_rating, implicit_score, ab_winner)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    _now_ts(),
                    feature,
                    inp.pattern_id,
                    str(inp.prompt or ""),
                    str(res.get("output") or ""),
                    int(res.get("ms") or 0),
                    os.environ.get("MYTHIQ_MODEL") or "llama3.2:3b",
                    None,
                    confidence,   # store confidence in implicit_score for now
                    None,
                ),
            )
            con.commit()
            db_changes = con.execute("select changes()").fetchone()[0]
            db_count = con.execute("select count(*) from runs").fetchone()[0]
        finally:
            con.close()
    except Exception as e:
        db_err = repr(e)
        print("DB_INSERT_ERROR", db_err)

    # metric best-effort
    try:
        _append_metric({
            "ts": _now_ts(),
            "route": "/v1/execute",
            "feature": feature,
            "confidence": confidence,
            "ms": int(res.get("ms") or 0),
            "ok": bool(res.get("ok")),
            "error": res.get("error"),
        })
    except Exception:
        pass

    return {
        "ok": True,
        "route": {"feature": feature, "confidence": confidence, "secondary": r.get("secondary", []), "scores": r.get("scores", {})},
        "run": {"ok": res.get("ok"), "output": res.get("output"), "ms": res.get("ms"), "attempts": res.get("attempts"), "error": res.get("error")},
        "run_id": run_id,
        "download_url": _infer_game_download_url(res.get("output")),
        "db_debug": {"db_path": db_path, "db_changes": db_changes, "db_count": db_count, "db_err": db_err},
    }

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


@app.get("/v1/status")
def status():
    """
    Minimal runtime status snapshot for local ops/UI.
    """
    try:
        lines = []
        if METRICS_PATH.exists():
            lines = METRICS_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()

        # scan last occurrences (cheap; file is small locally)
        last_chat = None
        last_warm = None
        for raw in reversed(lines):
            if last_chat is None and '"route": "/v1/chat"' in raw:
                last_chat = raw
            if last_warm is None and '"route": "warmup"' in raw:
                last_warm = raw
            if last_chat and last_warm:
                break

        return {
            "ok": True,
            "uptime_s": int(time.time() - START_TS),
            "model": os.environ.get("MYTHIQ_MODEL") or "llama3.2:3b",
            "metrics_lines": len(lines),
            "last_chat": last_chat,
            "last_warmup": last_warm,
            "warmup_enabled": (os.environ.get("MYTHIQ_WARMUP") == "1"),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}



@app.get("/v1/db_debug")
def db_debug():
    out = {"ok": True}
    try:
        out["DB_PATH"] = str(DB_PATH) if "DB_PATH" in globals() else None
    except Exception as e:
        out["DB_PATH_err"] = repr(e)

    try:
        con = db_conn() if "db_conn" in globals() else None
        if con is None:
            out["db_conn"] = None
            return out
        try:
            out["runs_count"] = con.execute("select count(*) from runs").fetchone()[0]
            out["last_run"] = con.execute(
                "select run_id, ts, feature, pattern_id, ms, model from runs order by ts desc limit 1"
            ).fetchone()
        finally:
            con.close()
    except Exception as e:
        out["query_err"] = repr(e)
    return out
@app.post("/v1/warmup")
def warmup():
    _warmup_ollama_async()
    return {"ok": True, "started": True}

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




class AbPickIn(BaseModel):
    ab_group: str = Field(..., min_length=1)
    winner: str = Field(..., pattern="^(A|B)$")  # vote for A or B
    user_rating: float | None = Field(None, ge=0.0, le=5.0)
    voter_id: str | None = Field(None, min_length=1)







class OutcomeIn(BaseModel):
    feature: str
    key: str
    reward: float
    meta: dict = {}

class OutcomeOut(BaseModel):
    ok: bool
    inserted: bool



class PatternVariantIn(BaseModel):
    pattern_id: str
    variant: str  # e.g. "A" or "B"
    system_prompt: str | None = None
    prefix: str | None = None

class PatternVariantOut(BaseModel):
    ok: bool
    inserted: bool

class PatternVariantGetOut(BaseModel):
    ok: bool
    pattern_id: str
    variant: str
    system_prompt: str | None = None
    prefix: str | None = None

class PatternRenderIn(BaseModel):
    pattern_id: str
    ab_group: str  # group used by ab_pick (typically same as pattern_id)
    prompt: str
    voter_id: str | None = None  # used for voting/decision process
    winner: str | None = None    # optional vote signal, forwarded to ab_pick if provided
    user_rating: float | None = None

class PatternRenderOut(BaseModel):
    ok: bool
    pattern_id: str
    variant: str
    decided: bool
    rendered: str

class AbPickOut(BaseModel):
    ok: bool
    ab_group: str
    winner: str | None
    picked: str
    votes: dict[str, int]
    inserted: bool
    decided: bool
    idempotent: bool = False
class PatternIn(BaseModel):
    pattern_id: str = Field(..., min_length=1)
    system_prompt: str | None = None
    prefix: str | None = None



class GameBuildOut(BaseModel):
    ok: bool
    game_id: str
    dir: str
    zip: str
    title: str
    prompt: str

class MetricsLastRow(BaseModel):
    ts: int
    feature: str
    prompt: str
    out_chars: int

class MetricsOut(BaseModel):
    total_generations: int
    by_feature: dict[str, int]
    last_20: list[MetricsLastRow]

@app.post("/v1/ab_pick", response_model=AbPickOut)
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
                "picked": dec[0],
                "winner": dec[0],
                "votes": {"A": dec[1], "B": dec[2]},
                "inserted": False,
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
        # --- log ab_pick into generations (for metrics/learning loop) ---
        try:
            conn2 = db()
            with conn2:
                conn2.execute(
                    "INSERT INTO generations(ts, feature, prompt, output, meta_json) VALUES(?,?,?,?,?)",
                    (
                        int(time.time()),
                        "ab_pick",
                        str(inp.ab_group),
                        str(inp.winner),
                        json.dumps({"inserted": bool(inserted), "decided": bool(decided)}, ensure_ascii=False),
                    ),
                )
            conn2.close()
        except Exception:
            pass


        return {
            "ok": True,
            "ab_group": inp.ab_group,
            "winner": winner if decided else None,
            "picked": inp.winner,
            "votes": {"A": a, "B": b},
            "inserted": inserted,
            "decided": decided,            "idempotent": False,

        }
    finally:
        conn.close()

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
def put_pattern(pattern_id: str, inp: 

PatternIn) -> Dict[str, Any]:
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


# ---------------------------
# SQLite (runs + pattern stats)
# ---------------------------

def db_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    return con

def db_init() -> None:
    con = db_conn()
    try:
        cur = con.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS runs (
          run_id TEXT PRIMARY KEY,
          ts INTEGER NOT NULL,
          feature TEXT NOT NULL,
          pattern_id TEXT,
          prompt TEXT NOT NULL,
          output TEXT NOT NULL,
          ms INTEGER NOT NULL,
          model TEXT,
          user_rating INTEGER,
          implicit_score REAL,
          ab_winner INTEGER
        )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_runs_ts ON runs(ts DESC)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_runs_pattern ON runs(pattern_id)")
        con.commit()
    finally:
        con.close()

@app.on_event("startup")
def _startup_db():
    # cheap, safe
    db_init()

def _now_ts() -> int:
    return int(time.time())

def _new_id(prefix: str = "r") -> str:
    # no external deps
    return f"{prefix}_{_now_ts()}_{os.urandom(6).hex()}"

@app.post("/v1/run_log")
def run(inp: dict):
    """
    Minimal run logger:
      - calls /v1/chat (ollama)
      - stores a run row in sqlite
    """
    feature = str(inp.get("feature") or "text")
    prompt = str(inp.get("prompt") or "")
    pattern_id = inp.get("pattern_id")
    pattern_id = None if pattern_id in ("", "null", "None") else (str(pattern_id) if pattern_id is not None else None)

    user_rating = inp.get("user_rating")
    implicit_score = inp.get("implicit_score")
    ab_winner = inp.get("ab_winner")

    try:
        user_rating = int(user_rating) if user_rating is not None else None
    except Exception:
        user_rating = None
    try:
        implicit_score = float(implicit_score) if implicit_score is not None else None
    except Exception:
        implicit_score = None
    try:
        ab_winner = int(ab_winner) if ab_winner is not None else None
    except Exception:
        ab_winner = None

    # call local python function for chat if available (avoid HTTP self-call)
    t0 = time.time()
    model = os.environ.get("MYTHIQ_MODEL") or "llama3.2:3b"
    out = ""
    err = None
    try:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": float(inp.get("temperature") or 0.2),
                "num_predict": int(inp.get("max_tokens") or 256),
            },
        }
        with httpx.Client(timeout=120.0) as client:
            r = client.post("http://ollama:11434/api/generate", json=payload)
            r.raise_for_status()
            data = r.json()
            out = str(data.get("response", ""))
    except Exception as e:
        err = str(e)
        out = f"OLLAMA_ERROR: {err}"

    ms = int((time.time() - t0) * 1000)
    run_id = _new_id("r")

    # persist

    db_changes = None

    db_count = None

    db_err = None

    db_path = str(DB_PATH) if "DB_PATH" in globals() else None

    try:
        con = db_conn()
        try:
            con.execute(
                """INSERT INTO runs
                   (run_id, ts, feature, pattern_id, prompt, output, ms, model, user_rating, implicit_score, ab_winner)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (run_id, _now_ts(), feature, pattern_id, prompt, str(out), ms, model, user_rating, implicit_score, ab_winner),
            )
            con.commit()
            db_changes = con.execute("select changes()").fetchone()[0]
            db_count = con.execute("select count(*) from runs").fetchone()[0]
        finally:
            con.close()
    except Exception as e:
        db_err = repr(e)
    # metric (best effort)
    try:
        _append_metric({
            "ts": _now_ts(),
            "route": "/v1/run",
            "ms": ms,
            "model": model,
            "error": err,
            "prompt_chars": len(prompt),
            "output_chars": len(out),
        })
    except Exception as e:
        print('DB_INSERT_ERROR', repr(e))

    return {

        "ok": True,

        "run_id": run_id,

        "output": out,

        "ms": ms,

        "model": model,

        "error": err,

        "db_debug": {

            "db_path": db_path,

            "db_changes": db_changes,

            "db_count": db_count,

            "db_err": db_err,

        },

    }
@app.get("/v1/library")
def library(limit: int = 50):
    limit = max(1, min(int(limit), 500))
    con = db_conn()
    try:
        rows = con.execute(
            """SELECT run_id, ts, feature, pattern_id, ms, model, user_rating, implicit_score, ab_winner
               FROM runs
               ORDER BY ts DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        out = []
        for r in rows:
            out.append({
                "run_id": r["run_id"],
                "ts": r["ts"],
                "feature": r["feature"],
                "pattern_id": r["pattern_id"],
                "ms": r["ms"],
                "model": r["model"],
                "user_rating": r["user_rating"],
                "implicit_score": r["implicit_score"],
                "ab_winner": r["ab_winner"],
                "status": "ok",
                "last_updated": r["ts"],
            })
        return {"ok": True, "rows": out}
    finally:
        con.close()

@app.get("/v1/runs/{run_id}")
def run_get(run_id: str):
    con = db_conn()
    try:
        r = con.execute(
            """SELECT * FROM runs WHERE run_id = ?""",
            (run_id,),
        ).fetchone()
        if not r:
            return {"ok": False, "error": "not_found"}
        d = dict(r)
        return {"ok": True, "run": d}
    finally:
        con.close()


@app.post("/v1/game/build", response_model=GameBuildOut)
def game_build(inp: dict):
    prompt = str(inp.get("prompt") or "Make a tiny arcade loop.")
    title = str(inp.get("title") or "Mythiq Game")
    b = build_phaser_game_bundle(title=title, prompt=prompt)

    # --- log this build into generations (for metrics/learning loop) ---
    try:
        _gid = str(locals().get("game_id", "unknown"))
        _title = str(inp.get("title", ""))
        _prompt = str(inp.get("prompt", ""))
        _dir = str(locals().get("out_dir", locals().get("dir", "")))
        _zip = str(locals().get("zip_path", locals().get("zip", "")))

        conn = db()
        with conn:
            conn.execute(
                "INSERT INTO generations(ts, feature, prompt, output, meta_json) VALUES(?,?,?,?,?)",
                (
                    int(time.time()),
                    "game",
                    _prompt,
                    _gid,
                    json.dumps({"title": _title, "dir": _dir, "zip": _zip}, ensure_ascii=False),
                ),
            )
        conn.close()
    except Exception as e:
        # keep a minimal breadcrumb in metrics.jsonl so failures are visible
        try:
            _append_metric({"ts": int(time.time()), "route": "game_build_log", "error": str(e)})
        except Exception:
            pass


    return {"ok": True, **b}


@app.get("/v1/game/download/{game_id}")
def game_download(game_id: str):
    # Find matching zip in EXPORTS_DIR
    try:
        d = EXPORTS_DIR
    except Exception:
        return {"ok": False, "error": "EXPORTS_DIR_missing"}

    zips = sorted(d.glob(f"{game_id}_*.zip"))
    if not zips:
        return {"ok": False, "error": "not_found"}

    fp = zips[-1]
    return FileResponse(
        path=str(fp),
        filename=fp.name,
        media_type="application/zip",
    )


@app.get("/v1/metrics", response_model=MetricsOut)
def v1_metrics():
    conn = db()
    try:
        total = int(conn.execute("SELECT COUNT(*) FROM generations").fetchone()[0])
        # if you want: count by feature
        rows = conn.execute(
            "SELECT feature, COUNT(*) AS n FROM generations GROUP BY feature ORDER BY n DESC"
        ).fetchall()
        by_feature = {r[0]: int(r[1]) for r in rows}
        # last 20
        last = conn.execute(
            "SELECT ts, feature, substr(prompt,1,200) AS prompt, length(output) AS out_chars "
            "FROM generations ORDER BY id DESC LIMIT 20"
        ).fetchall()
        last_20 = [
            {"ts": int(r[0]), "feature": r[1], "prompt": r[2], "out_chars": int(r[3])}
            for r in last
        ]
    finally:
        conn.close()

    return {
        "total_generations": total,
        "by_feature": by_feature,
        "last_20": last_20,
    }


def _log_game_build(game_id: str, title: str, prompt: str, started: float, status: str, error: str | None = None) -> None:
    try:
        created_at = datetime.now(timezone.utc).isoformat()
        duration_ms = int((time.time() - started) * 1000)
        mythiq_db.log_game_build(
            game_id=game_id,
            title=title,
            prompt=prompt,
            created_at=created_at,
            duration_ms=duration_ms,
            status=status,
            error=error,
        )
    except Exception:
        # logging must never break the pipeline
        pass







@app.post("/v1/pattern/variant/set", response_model=PatternVariantOut)
def pattern_variant_set(inp: PatternVariantIn):
    conn = db()
    try:
        with conn:
            conn.execute(
                "INSERT INTO pattern_variants(pattern_id, variant, system_prompt, prefix, created_ts, updated_ts) VALUES(?,?,?,?,?,?) ON CONFLICT(pattern_id, variant) DO UPDATE SET system_prompt=excluded.system_prompt, prefix=excluded.prefix, updated_ts=excluded.updated_ts",
                (str(inp.pattern_id), str(inp.variant), inp.system_prompt, inp.prefix, int(time.time()), int(time.time())),
            )
        return {"ok": True, "inserted": True}
    finally:
        conn.close()


@app.get("/v1/pattern/variant/get", response_model=PatternVariantGetOut)
def pattern_variant_get(pattern_id: str, variant: str):
    conn = db()
    try:
        row = conn.execute(
            "SELECT pattern_id, variant, system_prompt, prefix FROM pattern_variants WHERE pattern_id=? AND variant=?",
            (str(pattern_id), str(variant)),
        ).fetchone()
        if not row:
            return {"ok": False, "pattern_id": pattern_id, "variant": variant, "system_prompt": None, "prefix": None}
        return {"ok": True, "pattern_id": row[0], "variant": row[1], "system_prompt": row[2], "prefix": row[3]}
    finally:
        conn.close()


@app.get("/v1/ab_decision/get")
def ab_decision_get(ab_group: str):
    conn = db()
    try:
        row = conn.execute(
            "SELECT winner, decided_ts, votes_a, votes_b FROM ab_decisions WHERE ab_group=?",
            (str(ab_group),),
        ).fetchone()
        if not row:
            return {"ok": False, "ab_group": ab_group, "winner": None, "decided_ts": None, "votes": None}
        return {
            "ok": True,
            "ab_group": ab_group,
            "winner": row[0],
            "decided_ts": int(row[1]),
            "votes": {"A": int(row[2]), "B": int(row[3])},
        }
    finally:
        conn.close()


@app.get("/v1/pattern/variant/list")
def pattern_variant_list(pattern_id: str):
    conn = db()
    try:
        rows = conn.execute(
            "SELECT variant, updated_ts FROM pattern_variants WHERE pattern_id=? ORDER BY variant",
            (str(pattern_id),),
        ).fetchall()
        return {
            "ok": True,
            "pattern_id": str(pattern_id),
            "variants": [{"variant": r[0], "updated_ts": int(r[1])} for r in rows],
        }
    finally:
        conn.close()



@app.post("/v1/pattern/render", response_model=PatternRenderOut)
def pattern_render(inp: PatternRenderIn):
    # Choose a variant based on AB decision once decided. Otherwise pick A by default.
    # Also optionally forward a vote signal to /v1/ab_pick by calling the function directly (no HTTP).
    ab_group = str(inp.ab_group)
    decided = False
    chosen = "A"

    # If caller provided a vote, register it via ab_pick logic
    if inp.winner is not None:
        # ab_pick is an in-process function in this file; call it directly for atomicity + speed.
        res = ab_pick(
            AbPickIn(
                ab_group=ab_group,
                winner=str(inp.winner),
                user_rating=float(inp.user_rating) if inp.user_rating is not None else None,
                voter_id=str(inp.voter_id) if inp.voter_id is not None else "pattern_render",
            )
        )
        decided = bool(res.get("decided"))
        if decided and res.get("winner") in ("A", "B"):
            chosen = str(res.get("winner"))
    else:
        # no vote: if we already have a decision stored, query it from ab_decisions table
        conn = db()
        try:
            row = conn.execute(
                "SELECT winner FROM ab_decisions WHERE ab_group=?",
                (ab_group,),
            ).fetchone()
            if row and row[0] in ("A", "B"):
                decided = True
                chosen = str(row[0])
        finally:
            conn.close()

    # Load variant content; fallback to patterns table if variant missing; final fallback is empty strings.
    conn = db()
    try:
        v = conn.execute(
            "SELECT system_prompt, prefix FROM pattern_variants WHERE pattern_id=? AND variant=?",
            (str(inp.pattern_id), chosen),
        ).fetchone()
        if v:
            system_prompt, prefix = v[0] or "", v[1] or ""
        else:
            base = conn.execute(
                "SELECT system_prompt, prefix FROM patterns WHERE pattern_id=?",
                (str(inp.pattern_id),),
            ).fetchone()
            system_prompt, prefix = (base[0] if base and base[0] else ""), (base[1] if base and base[1] else "")

        rendered = ""
        if system_prompt:
            rendered += system_prompt.strip() + "\n\n"
        if prefix:
            rendered += prefix.strip() + "\n\n"
        rendered += str(inp.prompt)

        # log to generations for learning
        try:
            with conn:
                conn.execute(
                    "INSERT INTO generations(ts, feature, prompt, output, meta_json, pattern_id) VALUES(?,?,?,?,?,?)",
                    (
                        int(time.time()),
                        "pattern_render",
                        f"{inp.pattern_id}:{chosen}",
                        rendered,
                        json.dumps({"pattern_id": inp.pattern_id, "variant": chosen, "decided": decided, "ab_group": ab_group}, ensure_ascii=False),
                        str(inp.pattern_id),
                    ),
                )
        except Exception:
            pass

        return {
            "ok": True,
            "pattern_id": str(inp.pattern_id),
            "variant": chosen,
            "decided": decided,
            "rendered": rendered,
        }
    finally:
        conn.close()

@app.post("/v1/outcome", response_model=OutcomeOut)
def outcome(inp: OutcomeIn):
    # Record a scalar reward signal for learning loops.
    conn = db()
    try:
        with conn:
            conn.execute(
                "INSERT INTO outcomes(ts, feature, key_name, reward, meta_json) VALUES(?,?,?,?,?)",
                (int(time.time()), str(inp.feature), str(inp.key), float(inp.reward), json.dumps(inp.meta, ensure_ascii=False)),
            )
        return {"ok": True, "inserted": True}
    finally:
        conn.close()

@app.get("/v1/generations/export")
def generations_export(limit: int = 100):
    conn = connect()
    try:
        csv_text = export_generations_csv(conn, limit=limit)
    finally:
        conn.close()
    from fastapi.responses import Response
    return Response(content=csv_text, media_type="text/csv; charset=utf-8")



@app.post("/v1/outcomes/seed")
def outcomes_seed(feature: str = "ab_pick", key: str = "smoke", reward: float = 1.0, meta_json: str = '{"smoke":true}'):
    import time
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO outcomes (ts, feature, key_name, reward, meta_json) VALUES (?,?,?,?,?)",
            (int(time.time()), feature, key, float(reward), str(meta_json)),
        )
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}

@app.post("/v1/generations/seed")
def generations_seed(feature: str = "gen", key: str = "smoke", prompt: str = "p", output: str = "o", meta_json: str = '{"smoke":true}'):
    import time
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO generations (ts, feature, key_name, prompt, output, meta_json) VALUES (?,?,?,?,?,?)",
            (int(time.time()), feature, key, str(prompt), str(output), str(meta_json)),
        )
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}


@app.get("/v1/outcomes/export")
def outcomes_export(limit: int = 100):
    conn = connect()
    try:
        csv_text = export_outcomes_csv(conn, limit=limit)
    finally:
        conn.close()
    from fastapi.responses import Response
    return Response(content=csv_text, media_type="text/csv; charset=utf-8")

