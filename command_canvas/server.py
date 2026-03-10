#!/usr/bin/env python3
from __future__ import annotations

import json
import mimetypes
import os
import re
import time
import uuid
from collections import Counter
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DATA = ROOT / "data"
RUNS = DATA / "runs"
RUNS.mkdir(parents=True, exist_ok=True)

PORT = int(os.environ.get("MYTHIQ_CANVAS_PORT", "8099"))
QUALITY_THRESHOLD = int(os.environ.get("MYTHIQ_QUALITY_THRESHOLD", "78"))
MAX_RETRIES = int(os.environ.get("MYTHIQ_MAX_RETRIES", "2"))


def now_ms() -> int:
    return int(time.time() * 1000)


def slug(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()
    return s[:64] or "artifact"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def read_json(path: Path, default=None):
    if default is None:
        default = {}
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def route_mode(prompt: str, mode: str, source_url: str = "") -> str:
    if mode and mode != "auto":
        return mode
    low = f"{prompt} {source_url}".lower()
    if any(k in low for k in ["youtu", "youtube", "shorts", "clips", "tiktok", "reels", "long video", "video link"]):
        return "shorts"
    if any(k in low for k in ["game", "phaser", "football", "slot", "pack opening", "platformer", "runner"]):
        return "game"
    if any(k in low for k in ["fastapi", "python", "javascript", "typescript", "html", "css", "api", "backend", "frontend", "code"]):
        return "code"
    if any(k in low for k in ["document", "essay", "article", "report", "explain", "summary", "doc", "tesla"]):
        return "docs"
    return "text"


def artifact_rel(job_id: str, filename: str) -> str:
    return f"/artifact/{job_id}/artifacts/{filename}"


def top_terms(text: str, n: int = 12) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9_'-]+", text.lower())
    stop = {
        "the", "and", "for", "that", "this", "with", "from", "into", "your", "have", "will",
        "what", "when", "where", "which", "they", "them", "then", "than", "just", "make",
        "build", "about", "there", "their", "been", "were", "would", "could", "should",
        "video", "long", "short", "shorts", "prompt"
    }
    counts = Counter(w for w in words if w not in stop and len(w) > 2)
    return [w for w, _ in counts.most_common(n)]


def extract_requirements(prompt: str) -> dict:
    low = prompt.lower()
    return {
        "wants_api": any(k in low for k in ["api", "fastapi", "backend"]),
        "wants_ui": any(k in low for k in ["ui", "frontend", "page", "website", "landing page", "html"]),
        "wants_game": "game" in low,
        "wants_shorts": any(k in low for k in ["shorts", "clips", "tiktok", "reels"]),
        "football_theme": any(k in low for k in ["football", "soccer"]),
        "pack_theme": any(k in low for k in ["pack", "pack opening", "card"]),
        "tesla_theme": "tesla" in low,
    }


def sentence_split(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    parts = re.split(r'(?<=[.!?])\s+', text)
    return [p.strip() for p in parts if p.strip()] or [text]


def chunk_sentences(sentences: list[str], target_count: int) -> list[str]:
    if not sentences:
        return []
    target_count = max(1, min(10, target_count))
    chunk_size = max(1, round(len(sentences) / target_count))
    return [" ".join(sentences[i:i + chunk_size]).strip() for i in range(0, len(sentences), chunk_size)][:target_count]


def hook_score(text: str) -> int:
    low = text.lower()
    score = 60
    triggers = [
        "biggest", "craziest", "chaos", "revealed", "suddenly", "overwhelmed",
        "legendary", "unexpected", "insane", "massive", "finally", "worst", "best"
    ]
    score += sum(4 for t in triggers if t in low)
    score += min(12, len(text.split()) // 4)
    return min(98, score)


def quality_score(feature: str, artifact_count: int, preview: str) -> int:
    base = {"text": 78, "docs": 82, "code": 80, "game": 81, "shorts": 84}.get(feature, 75)
    base += min(8, artifact_count * 2)
    if len(preview or "") > 180:
        base += 3
    return min(98, base)


def make_text_result(prompt: str, job_dir: Path, job_id: str) -> tuple[list[dict], str]:
    artifacts_dir = job_dir / "artifacts"
    req = extract_requirements(prompt)
    terms = top_terms(prompt)
    md = f"""# Mythiq Text Response

## Prompt
{prompt}

## Interpreted Goal
Mythiq detected a text-first request and generated a structured response focused on the prompt.

## Key Intent Signals
- API requested: {req['wants_api']}
- UI requested: {req['wants_ui']}
- Game requested: {req['wants_game']}
- Shorts requested: {req['wants_shorts']}

## High-Value Terms
{", ".join(terms) if terms else "none"}

## Suggested Execution Path
1. Clarify the main deliverable
2. Generate the first artifact
3. Validate
4. Iterate with user feedback
"""
    out = artifacts_dir / "response.md"
    write_text(out, md)
    return ([{"kind": "markdown", "path": artifact_rel(job_id, out.name)}], md[:500])


def make_docs_result(prompt: str, job_dir: Path, job_id: str) -> tuple[list[dict], str]:
    artifacts_dir = job_dir / "artifacts"
    req = extract_requirements(prompt)
    if req["tesla_theme"]:
        title = "Tesla Free Energy: Myth vs Reality"
        summary = (
            "Tesla explored radiant energy ideas and wireless power transmission, but these should not be confused "
            "with a proven limitless-energy machine. The strongest practical side of Tesla's legacy is grounded "
            "electrical engineering: AC systems, resonance, high-frequency experimentation, and transmission."
        )
        sections = [
            "What Tesla actually explored",
            "Why people call it free energy",
            "What is historically grounded",
            "What remains speculative",
            "What this means in practice today"
        ]
    else:
        title = "Mythiq Generated Document"
        summary = "This is a prompt-specific structured document draft generated by the Mythiq docs engine."
        sections = ["Goal", "Context", "Key Points", "Execution Plan", "Next Steps"]

    md = f"""# {title}

## Prompt
{prompt}

## Summary
{summary}

## Sections
""" + "\n".join(f"- {s}" for s in sections) + """

## Draft Body
This artifact is prompt-specific, saved, replayable, and ready to evolve into stronger model-backed document generation.
"""
    outline = {"title": title, "prompt": prompt, "summary": summary, "sections": sections}
    md_out = artifacts_dir / "document.md"
    json_out = artifacts_dir / "outline.json"
    write_text(md_out, md)
    write_json(json_out, outline)
    return (
        [
            {"kind": "markdown", "path": artifact_rel(job_id, md_out.name)},
            {"kind": "json", "path": artifact_rel(job_id, json_out.name)},
        ],
        md[:500]
    )


def make_code_result(prompt: str, job_dir: Path, job_id: str) -> tuple[list[dict], str]:
    artifacts_dir = job_dir / "artifacts"
    req = extract_requirements(prompt)
    low = prompt.lower()
    files = []

    if req["wants_api"]:
        app_py = artifacts_dir / "app.py"
        app_code = """from fastapi import FastAPI

app = FastAPI(title="Mythiq Generated API")

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/")
def root():
    return {"message": "Hello from Mythiq"}
"""
        write_text(app_py, app_code)
        files.append({"kind": "code", "path": artifact_rel(job_id, app_py.name)})

    if req["wants_ui"] or "html" in low or "landing page" in low or not files:
        index_html = artifacts_dir / "index.html"
        html = """<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Mythiq Generated UI</title>
  <style>
    body { font-family: Arial, sans-serif; padding: 40px; background: #111; color: #fff; }
    .card { max-width: 720px; margin: 0 auto; padding: 24px; background: #1b1b1b; border-radius: 16px; }
  </style>
</head>
<body>
  <div class="card">
    <h1>Mythiq Generated UI</h1>
    <p>This HTML file was generated from a prompt-specific code request.</p>
  </div>
</body>
</html>
"""
        write_text(index_html, html)
        files.append({"kind": "code", "path": artifact_rel(job_id, index_html.name)})

    readme = artifacts_dir / "README.md"
    write_text(readme, f"# Mythiq Code Output\n\n## Prompt\n{prompt}\n")
    files.append({"kind": "markdown", "path": artifact_rel(job_id, readme.name)})
    preview = f"Generated {len(files)-1} code artifact(s) for prompt: {prompt}"
    return (files, preview[:500])


def make_game_result(prompt: str, job_dir: Path, job_id: str) -> tuple[list[dict], str]:
    artifacts_dir = job_dir / "artifacts"
    req = extract_requirements(prompt)
    game_name = "Mythiq Game Prototype"
    if req["football_theme"] and req["pack_theme"]:
        game_name = "Mythiq Football Pack Clash"
    design = {
        "game_name": game_name,
        "prompt": prompt,
        "genre": "collection/pack-opening" if req["pack_theme"] else "arcade",
        "core_loop": ["Earn currency", "Open packs or interact", "Collect or progress", "Unlock stronger outcomes"],
        "systems": {"inventory": "local save storage", "progression": "earn and spend loop", "theme": "football pack opening" if req["football_theme"] else "general"},
        "next_files": ["src/scenes/HomeScene.js", "src/scenes/MainScene.js", "src/data/config.json"]
    }
    md = f"""# {game_name}

## Prompt
{prompt}

## Game Loop
- Earn currency
- Open packs or trigger the main game mechanic
- Reveal results
- Progress your collection or rank
"""
    json_out = artifacts_dir / "game_design.json"
    md_out = artifacts_dir / "game_brief.md"
    write_json(json_out, design)
    write_text(md_out, md)
    return (
        [
            {"kind": "json", "path": artifact_rel(job_id, json_out.name)},
            {"kind": "markdown", "path": artifact_rel(job_id, md_out.name)},
        ],
        md[:500]
    )


def make_shorts_result(prompt: str, source_url: str, transcript: str, target_count: int, job_dir: Path, job_id: str) -> tuple[list[dict], str]:
    artifacts_dir = job_dir / "artifacts"
    target_count = max(1, min(10, int(target_count or 5)))
    if not transcript.strip():
        transcript = (
            "This is a fallback transcript. The creator enters a huge server. Chaos starts immediately. "
            "Then tension rises. A reveal changes the situation. Finally there is a payoff and reflection."
        )
    sentences = sentence_split(transcript)
    windows = chunk_sentences(sentences, target_count)
    clips = []
    for i, text in enumerate(windows, start=1):
        first_line = sentence_split(text)[0] if sentence_split(text) else text
        hook = first_line.strip()
        hook = hook[:110] + ("..." if len(hook) > 110 else "")
        score = hook_score(text)
        start_s = (i - 1) * 20
        end_s = start_s + 20
        clips.append({
            "rank": i,
            "clip_id": f"clip_{i:02d}",
            "hook": hook,
            "start_hint": f"00:{start_s:02d}",
            "end_hint": f"00:{end_s:02d}",
            "why_it_works": "Strong hook, standalone moment, and visible escalation/payoff.",
            "title": f"Clip {i}: {hook[:48]}",
            "caption": f"{hook} #shorts #viral #mythiq",
            "thumbnail_concept": f"High-contrast frame focused on: {hook}",
            "edit_notes": ["Open with strongest line", "Use captions throughout", "Keep cuts fast"],
            "retention_score": score
        })
    clips = sorted(clips, key=lambda x: x["retention_score"], reverse=True)
    for idx, clip in enumerate(clips, start=1):
        clip["rank"] = idx

    pack = {"flow_id": "flow.shorts_from_video", "prompt": prompt, "source_url": source_url, "target_count": target_count, "clips": clips}
    md_parts = ["# Mythiq Shorts Pack", "", "## Prompt", prompt, "", "## Source URL", source_url or "none", "", "## Ranked Clips"]
    for c in clips:
        md_parts.extend([
            "",
            f"### {c['rank']}. {c['title']}",
            f"- Hook: {c['hook']}",
            f"- Window: {c['start_hint']} - {c['end_hint']}",
            f"- Why it works: {c['why_it_works']}",
            f"- Caption: {c['caption']}",
            f"- Thumbnail: {c['thumbnail_concept']}",
            f"- Score: {c['retention_score']}",
        ])
    md = "\n".join(md_parts)
    csv_lines = ["rank,clip_id,start_hint,end_hint,retention_score,title"]
    for c in clips:
        title = c["title"].replace('"', '""')
        csv_lines.append(f'{c["rank"]},{c["clip_id"]},{c["start_hint"]},{c["end_hint"]},{c["retention_score"]},"{title}"')
    json_out = artifacts_dir / "shorts_pack.json"
    md_out = artifacts_dir / "shorts_pack.md"
    csv_out = artifacts_dir / "shorts_pack.csv"
    write_json(json_out, pack)
    write_text(md_out, md)
    write_text(csv_out, "\n".join(csv_lines) + "\n")
    return (
        [
            {"kind": "json", "path": artifact_rel(job_id, json_out.name)},
            {"kind": "markdown", "path": artifact_rel(job_id, md_out.name)},
            {"kind": "csv", "path": artifact_rel(job_id, csv_out.name)},
        ],
        md[:700]
    )


def validate_result(feature: str, prompt: str, artifacts: list[dict], preview: str, job_dir: Path) -> dict:
    errors = []
    warnings = []
    generic_phrases = [
        "this is a prompt-specific",
        "ready to evolve",
        "generated by mythiq",
        "artifact is prompt-specific",
        "this artifact is"
    ]

    if not artifacts:
        errors.append("no_artifacts")
    for a in artifacts:
        p = job_dir / a["path"].split("/artifacts/", 1)[1]
        if not p.exists():
            errors.append(f"missing_artifact:{p.name}")
        elif p.stat().st_size == 0:
            errors.append(f"empty_artifact:{p.name}")

    preview_low = (preview or "").lower()
    prompt_terms = set(top_terms(prompt, 10))
    overlap = sum(1 for t in prompt_terms if t in preview_low)
    if prompt_terms and overlap == 0:
        warnings.append("low_prompt_overlap")

    generic_hits = sum(1 for g in generic_phrases if g in preview_low)
    if generic_hits >= 2:
        warnings.append("generic_language")

    if feature == "shorts":
        json_files = [a for a in artifacts if a["kind"] == "json"]
        if not json_files:
            errors.append("missing_shorts_json")
        else:
            pack_path = job_dir / json_files[0]["path"].split("/artifacts/", 1)[1]
            pack = read_json(pack_path, {})
            clips = pack.get("clips", [])
            if len(clips) < 3:
                errors.append("too_few_clips")
            hooks = [c.get("hook", "").strip().lower() for c in clips]
            if len(set(hooks)) != len(hooks):
                warnings.append("duplicate_hooks")

    if feature == "code":
        code_files = [a for a in artifacts if a["kind"] == "code"]
        if not code_files:
            errors.append("missing_code_artifact")

    if feature == "game":
        json_files = [a for a in artifacts if a["kind"] == "json"]
        if not json_files:
            errors.append("missing_game_json")

    if feature == "docs":
        md_files = [a for a in artifacts if a["kind"] == "markdown"]
        if not md_files:
            errors.append("missing_docs_markdown")

    validation_passed = len(errors) == 0
    return {
        "passed": validation_passed,
        "errors": errors,
        "warnings": warnings,
        "prompt_overlap_terms": overlap,
    }


def critic_report(feature: str, prompt: str, preview: str, validation: dict, artifacts: list[dict]) -> dict:
    issues = []
    strengths = []
    suggestions = []

    if validation["errors"]:
        issues.extend(validation["errors"])
    if validation["warnings"]:
        issues.extend(validation["warnings"])

    if len(artifacts) >= 2:
        strengths.append("multiple_artifacts_generated")
    if len(preview or "") > 220:
        strengths.append("non_trivial_preview")

    preview_low = (preview or "").lower()
    if "prompt-specific" in preview_low or "ready to evolve" in preview_low:
        suggestions.append("remove_placeholder_language")
    if feature == "shorts" and "hook" not in preview_low:
        suggestions.append("strengthen_hook_specificity")
    if feature == "game":
        suggestions.append("promote_design_json_into_real_scaffold_next")
    if feature == "code":
        suggestions.append("add tests or runnable scaffold next")
    if feature == "docs":
        suggestions.append("expand section depth and reduce boilerplate")

    score = 100
    score -= len(validation["errors"]) * 25
    score -= len(validation["warnings"]) * 8
    if "remove_placeholder_language" in suggestions:
        score -= 10
    critique_score = max(0, min(100, score))

    return {
        "critique_score": critique_score,
        "issues": issues,
        "strengths": strengths,
        "suggestions": suggestions,
        "usable": critique_score >= QUALITY_THRESHOLD and validation["passed"],
    }


def save_common(job_dir: Path, payload: dict, result: dict, logs: list[str], validation: dict, critic: dict) -> None:
    write_json(job_dir / "input.json", payload)
    write_json(job_dir / "result.json", result)
    write_json(job_dir / "validation.json", validation)
    write_json(job_dir / "critic_report.json", critic)
    write_text(job_dir / "logs.txt", "\n".join(logs) + "\n")


def execute_once(payload: dict) -> tuple[dict, dict, dict, list[str], Path]:
    t0 = now_ms()
    prompt = str(payload.get("prompt", "")).strip()
    mode = str(payload.get("mode", "auto")).strip().lower()
    source_url = str(payload.get("source_url", "")).strip()
    transcript = str(payload.get("transcript", "")).strip()
    target_count = int(payload.get("target_count", 5) or 5)

    final_prompt = prompt or f"Create artifacts from {source_url}"
    feature = route_mode(final_prompt, mode, source_url=source_url)

    job_id = f"job_{uuid.uuid4().hex[:10]}"
    job_dir = RUNS / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    logs = ["received prompt", f"selected feature={feature}", "creating artifacts"]

    if feature == "text":
        artifacts, preview = make_text_result(final_prompt, job_dir, job_id)
    elif feature == "docs":
        artifacts, preview = make_docs_result(final_prompt, job_dir, job_id)
    elif feature == "code":
        artifacts, preview = make_code_result(final_prompt, job_dir, job_id)
    elif feature == "game":
        artifacts, preview = make_game_result(final_prompt, job_dir, job_id)
    elif feature == "shorts":
        artifacts, preview = make_shorts_result(final_prompt, source_url, transcript, target_count, job_dir, job_id)
    else:
        artifacts, preview = make_text_result(final_prompt, job_dir, job_id)

    logs.append("artifacts saved")
    validation = validate_result(feature, final_prompt, artifacts, preview, job_dir)
    critic = critic_report(feature, final_prompt, preview, validation, artifacts)

    result = {
        "ok": validation["passed"],
        "job_id": job_id,
        "feature": feature,
        "status": "done" if validation["passed"] else "failed_validation",
        "artifacts": artifacts,
        "metrics": {
            "latency_ms": max(1, now_ms() - t0),
            "quality_score": quality_score(feature, len(artifacts), preview),
            "critique_score": critic["critique_score"],
            "validation_passed": validation["passed"],
        },
        "logs": logs,
        "preview": preview,
        "critic_report": critic,
    }

    save_common(
        job_dir,
        {
            "prompt": prompt,
            "mode": mode,
            "source_url": source_url,
            "transcript": transcript,
            "target_count": target_count,
            "feature": feature,
        },
        result,
        logs,
        validation,
        critic,
    )
    return result, validation, critic, logs, job_dir


def execute(payload: dict) -> dict:
    attempts = []
    for attempt in range(1, MAX_RETRIES + 2):
        result, validation, critic, logs, job_dir = execute_once(payload)
        result["attempt"] = attempt
        attempts.append({"job_id": result["job_id"], "attempt": attempt, "critique_score": critic["critique_score"]})
        if validation["passed"] and critic["critique_score"] >= QUALITY_THRESHOLD:
            result["attempts"] = attempts
            write_json(job_dir / "attempts.json", {"attempts": attempts})
            return result
    result["attempts"] = attempts
    result["ok"] = False
    result["status"] = "draft_below_quality_threshold"
    return result


def load_history(limit: int = 50) -> dict:
    items = []
    for d in sorted(RUNS.glob("job_*"), key=lambda x: x.stat().st_mtime, reverse=True):
        result = read_json(d / "result.json", {})
        inp = read_json(d / "input.json", {})
        if not result:
            continue
        items.append({
            "job_id": result.get("job_id"),
            "feature": result.get("feature"),
            "status": result.get("status"),
            "quality_score": (result.get("metrics") or {}).get("quality_score"),
            "critique_score": (result.get("metrics") or {}).get("critique_score"),
            "prompt": inp.get("prompt", ""),
            "source_url": inp.get("source_url", ""),
            "artifacts": result.get("artifacts", []),
        })
    return {"ok": True, "items": items[:limit]}


def rerun_job(job_id: str) -> dict:
    source = RUNS / job_id
    inp = read_json(source / "input.json", None)
    if not inp:
        return {"ok": False, "error": "missing_input"}
    payload = {
        "prompt": inp.get("prompt", ""),
        "mode": inp.get("feature", inp.get("mode", "auto")),
        "source_url": inp.get("source_url", ""),
        "transcript": inp.get("transcript", ""),
        "target_count": inp.get("target_count", 5),
    }
    return execute(payload)


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: bytes, content_type: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/history":
            self._send(200, json.dumps(load_history()).encode("utf-8"))
            return

        if path == "/" or path == "/index.html":
            file_path = STATIC / "index.html"
        elif path.startswith("/artifact/"):
            rel = path[len("/artifact/"):]
            file_path = RUNS / rel
        else:
            file_path = STATIC / path.lstrip("/")

        if not file_path.exists() or not file_path.is_file():
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return

        mime, _ = mimetypes.guess_type(str(file_path))
        body = file_path.read_bytes()
        self._send(200, body, mime or "application/octet-stream")

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            data = json.loads(raw.decode("utf-8") or "{}")
        except Exception as e:
            self._send(400, json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
            return

        if self.path == "/api/command":
            prompt = str(data.get("prompt", "")).strip()
            source_url = str(data.get("source_url", "")).strip()
            if not prompt and not source_url:
                self._send(400, b'{"ok":false,"error":"missing_prompt_or_source"}')
                return
            result = execute(data)
            code = 200 if result.get("ok") else 422
            self._send(code, json.dumps(result).encode("utf-8"))
            return

        if self.path == "/api/rerun":
            job_id = str(data.get("job_id", "")).strip()
            if not job_id:
                self._send(400, b'{"ok":false,"error":"missing_job_id"}')
                return
            result = rerun_job(job_id)
            code = 200 if result.get("ok") else 400
            self._send(code, json.dumps(result).encode("utf-8"))
            return

        if self.path == "/api/feedback":
            job_id = str(data.get("job_id", "")).strip()
            if not job_id:
                self._send(400, b'{"ok":false,"error":"missing_job_id"}')
                return
            job_dir = RUNS / job_id
            if not job_dir.exists():
                self._send(404, b'{"ok":false,"error":"job_not_found"}')
                return
            feedback = {
                "job_id": job_id,
                "rating": data.get("rating"),
                "notes": data.get("notes", ""),
                "saved_at_ms": now_ms(),
            }
            write_json(job_dir / "feedback.json", feedback)
            self._send(200, b'{"ok":true}')
            return

        self._send(404, b'{"ok":false,"error":"not_found"}')


def main() -> None:
    httpd = HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"MYTHIQ_COMMAND_CANVAS=http://127.0.0.1:{PORT}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
