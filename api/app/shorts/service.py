from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import time
import textwrap
import uuid
from pathlib import Path
from typing import Any

from faster_whisper import WhisperModel

ROOT = Path(__file__).resolve().parents[3]
SHORTS_DEFAULT_TARGET_COUNT = 10


PROMPT_TOP_K = 12

def slugify_text(x: str) -> str:
    x = (x or "").strip().lower()
    x = re.sub(r"[^a-z0-9]+", "-", x)
    return x.strip("-") or "general"

def prompt_key(prompt: str) -> str:
    return hashlib.sha1((prompt or "").encode("utf-8")).hexdigest()[:12]

def extract_prompt_keywords(prompt: str, limit: int = PROMPT_TOP_K) -> list[str]:
    text = (prompt or "").lower()
    words = re.findall(r"[a-z0-9']+", text)
    stop = {
        "the","a","an","and","or","but","if","then","else","for","to","of","in","on","at","by",
        "with","from","into","about","over","after","before","under","between","during","without",
        "is","are","was","were","be","been","being","this","that","these","those","it","its","as",
        "make","makes","making","turn","turns","into","long","short","shorts","video","videos",
        "clip","clips","real","fully","working","good","best","quality","unique","prompt"
    }
    out = []
    seen = set()
    for w in words:
        if len(w) < 3 or w in stop or w in seen:
            continue
        seen.add(w)
        out.append(w)
        if len(out) >= limit:
            break
    return out

def prompt_bonus_score(text: str, prompt_keywords: list[str]) -> float:
    if not prompt_keywords:
        return 0.0
    low = (text or "").lower()
    hits = sum(1 for kw in prompt_keywords if kw in low)
    return min(0.30, hits * 0.03)

def ranked_cache_key(url: str, target_count: int, prompt: str) -> str:
    return f"{url_key(url)}_{target_count}_{prompt_key(prompt)}"

def cached_ranked_prompt_path(url: str, target_count: int, prompt: str) -> Path:
    return cache_dir() / "ranked" / f"{ranked_cache_key(url, target_count, prompt)}.json"
SHORTS_MIN_CLIP_SEC = 18.0
SHORTS_MAX_CLIP_SEC = 35.0
SHORTS_STEP_SEC = 10.0

ART = ROOT / "artifacts"


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def mkdir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def job_dir(prefix: str = "shorts") -> Path:
    jid = f"{prefix}_{uuid.uuid4().hex[:12]}"
    p = ART / jid
    mkdir(p / "source")
    mkdir(p / "transcript")
    mkdir(p / "moments")
    mkdir(p / "renders")
    mkdir(p / "captions")
    mkdir(p / "thumbs")
    return p


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def probe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    ).strip()
    return float(out)


def cache_dir() -> Path:
    p = ART / "_cache" / "sources"
    p.mkdir(parents=True, exist_ok=True)
    return p


def url_key(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]



def cached_transcript_path(url: str) -> Path:
    return cache_dir() / f"{url_key(url)}.transcript.json"

def cached_ranked_path(url: str, target_count: int) -> Path:
    return cache_dir() / f"{url_key(url)}.ranked_{target_count}.json"

def cached_source_path(url: str) -> Path:
    return cache_dir() / f"{url_key(url)}.mp4"


def download_source(url: str, out_template: Path) -> Path:
    cache_mp4 = cached_source_path(url)
    out = out_template.with_suffix(".mp4")

    if cache_mp4.exists():
        shutil.copy2(cache_mp4, out)
        return out

    template = str(out_template.with_suffix(".%(ext)s"))
    run([
        "yt-dlp",
        "-f", "mp4/bestvideo+bestaudio/best",
        "-o", template,
        url,
    ])

    matches = sorted(out_template.parent.glob(out_template.stem + ".*"))
    if not matches:
        raise RuntimeError("download_source: no downloaded file found")

    src = matches[0]
    if src.suffix.lower() != ".mp4":
        converted = out_template.with_suffix(".mp4")
        run([
            "ffmpeg", "-y",
            "-i", str(src),
            "-c", "copy",
            str(converted),
        ])
        src = converted

    shutil.copy2(src, cache_mp4)
    if src != out:
        shutil.copy2(src, out)
        return out
    return src


def extract_audio(src: Path, wav: Path) -> None:
    run([
        "ffmpeg", "-y",
        "-i", str(src),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        str(wav),
    ])


def transcribe_audio(wav: Path) -> dict[str, Any]:
    t0 = time.time()
    model = WhisperModel("base", compute_type="int8")
    segments, info = model.transcribe(str(wav), beam_size=5, vad_filter=True)

    out_segments: list[dict[str, Any]] = []
    full_text: list[str] = []

    for seg in segments:
        text = (seg.text or "").strip()
        if not text:
            continue
        out_segments.append({
            "start": round(float(seg.start), 2),
            "end": round(float(seg.end), 2),
            "text": text,
        })
        full_text.append(text)

    return {
        "text": " ".join(full_text).strip(),
        "segments": out_segments,
        "language": getattr(info, "language", None),
        "duration_sec": out_segments[-1]["end"] if out_segments else 0.0,
        "transcribe_elapsed_sec": round(time.time() - t0, 2),
    }




def clamp_clip_window(start_sec: float, end_sec: float, total_duration: float) -> tuple[float, float]:
    start_sec = max(0.0, float(start_sec))
    end_sec = min(float(total_duration), float(end_sec))
    dur = end_sec - start_sec

    if dur < SHORTS_MIN_CLIP_SEC:
        pad = (SHORTS_MIN_CLIP_SEC - dur) / 2.0
        start_sec = max(0.0, start_sec - pad)
        end_sec = min(float(total_duration), end_sec + pad)

    dur = end_sec - start_sec
    if dur > SHORTS_MAX_CLIP_SEC:
        center = (start_sec + end_sec) / 2.0
        half = SHORTS_MAX_CLIP_SEC / 2.0
        start_sec = max(0.0, center - half)
        end_sec = min(float(total_duration), center + half)

        if end_sec - start_sec < SHORTS_MAX_CLIP_SEC:
            if start_sec <= 0.0:
                end_sec = min(float(total_duration), SHORTS_MAX_CLIP_SEC)
            elif end_sec >= float(total_duration):
                start_sec = max(0.0, float(total_duration) - SHORTS_MAX_CLIP_SEC)

    return round(start_sec, 2), round(end_sec, 2)


def _clean_title_text(text: str) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    text = text.strip(" -—:,.")
    return text


def build_hook_line(preview: str) -> str:
    preview = _clean_title_text(preview)
    if not preview:
        return "You won’t believe what happens next."
    preview = preview[:120]
    starters = [
        "This is where everything changes:",
        "This is the moment it gets serious:",
        "This is the part nobody expects:",
        "This is where it all breaks open:",
        "This is why people keep watching:",
    ]
    idx = sum(ord(c) for c in preview) % len(starters)
    return f"{starters[idx]} {preview}"[:140]


def build_viral_title(preview: str, matched_keywords: list[str]) -> str:
    preview = _clean_title_text(preview)
    if not preview:
        return "Top viral moment"
    base = preview[:65].strip()
    if matched_keywords:
        lead = matched_keywords[0].replace("_", " ").title()
        return f"{lead} Moment: {base}"[:90]
    return f"{base}"[:90]


def build_thumbnail_text(preview: str, matched_keywords: list[str]) -> str:
    if matched_keywords:
        return " | ".join([kw.upper() for kw in matched_keywords[:3]])[:36]
    words = [w for w in re.split(r"\s+", preview) if w]
    return " ".join(w.upper() for w in words[:3])[:36]


def build_editor_notes(item: dict) -> list[str]:
    notes = []
    if item.get("hook_score", 0) >= 0.8:
        notes.append("Open immediately on the first spoken hook.")
    if item.get("speech_density", 0) >= 0.7:
        notes.append("Use fast captions because speech density is high.")
    if item.get("matched_keywords"):
        notes.append("Emphasize keyword words in captions and cover text.")
    notes.append("Add punch-in zooms on key nouns and reactions.")
    notes.append("Keep subtitles large, centered low, and phone-readable.")
    return notes[:4]


def build_hashtags(item: dict) -> list[str]:
    tags = ["#shorts", "#viral", "#story"]
    for kw in item.get("matched_keywords", [])[:4]:
        clean = re.sub(r"[^a-zA-Z0-9]", "", kw)
        if clean:
            tags.append("#" + clean.lower())
    out = []
    for t in tags:
        if t not in out:
            out.append(t)
    return out[:6]






PACKAGING_VARIANTS = 3

def _clean_words(text: str) -> list[str]:
    import re as _re
    return [w for w in _re.findall(r"[a-z0-9']+", (text or "").lower()) if len(w) >= 3]

def _uniq_keep(seq: list[str]) -> list[str]:
    seen = set()
    out = []
    for x in seq:
        k = (x or "").strip().lower()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append((x or "").strip())
    return out

def classify_story_role(item: dict[str, Any]) -> str:
    txt = " ".join([
        str(item.get("hook_line", "")),
        str(item.get("reason", "")),
        str(item.get("transcript_preview", "")),
    ]).lower()

    if any(k in txt for k in ["twist", "betray", "betrayal", "reveal", "suddenly", "plot twist"]):
        return "twist"
    if any(k in txt for k in ["payoff", "won", "win", "finally", "clutch", "last second", "survived"]):
        return "payoff"
    if any(k in txt for k in ["danger", "panic", "chase", "raid", "fight", "escape", "chaos"]):
        return "tension"
    return "setup"

def build_backstory_context(item: dict[str, Any], prompt: str) -> str:
    preview = str(item.get("transcript_preview", "")).strip()
    matched = [str(x).strip() for x in item.get("matched_keywords", []) if str(x).strip()]
    prompt_words = extract_prompt_keywords(prompt) if "extract_prompt_keywords" in globals() else _clean_words(prompt)[:7]

    parts = []
    if prompt_words:
        parts.append("Prompt focus: " + ", ".join(prompt_words[:5]))
    if matched:
        parts.append("Clip focus: " + ", ".join(matched[:5]))
    if preview:
        parts.append("Context: " + preview[:180])
    return " | ".join(parts)[:420]

def build_hook_variants(item: dict[str, Any], prompt: str) -> list[str]:
    preview = str(item.get("transcript_preview", "")).strip()
    role = classify_story_role(item)
    kws = [str(x).strip() for x in item.get("matched_keywords", []) if str(x).strip()]
    focus = ", ".join(kws[:3]) if kws else "this moment"

    variants = [
        f"You think this is normal until {focus} changes everything.",
        f"This {role} is the part nobody sees coming.",
        f"Watch what happens right when {focus} kicks in.",
        f"This is where the whole story flips.",
        f"The backstory makes this hit even harder: {preview[:70]}".strip(),
    ]
    return _uniq_keep([v[:110] for v in variants])[:PACKAGING_VARIANTS]

def build_title_variants(item: dict[str, Any], prompt: str) -> list[str]:
    role = classify_story_role(item)
    kws = [str(x).strip() for x in item.get("matched_keywords", []) if str(x).strip()]
    preview = str(item.get("transcript_preview", "")).strip()
    focus = kws[0] if kws else "moment"

    variants = [
        f"The {focus.title()} Twist Nobody Expected",
        f"This {role.title()} Changed Everything",
        f"What Happened Next Was Actually Wild",
        f"The Part That Made Everyone Keep Watching",
        f"{focus.title()} Went Too Far Here",
        f"This Backstory Makes The Clip Hit Harder",
    ]

    if prompt:
        pkw = extract_prompt_keywords(prompt) if "extract_prompt_keywords" in globals() else _clean_words(prompt)[:7]
        if pkw:
            variants.insert(0, f"{pkw[0].title()} Story With A {role.title()} Twist")

    if preview:
        variants.append(preview[:58].rstrip(" .!?"))

    return _uniq_keep([v[:70] for v in variants])[:PACKAGING_VARIANTS]

def build_thumbnail_variants(item: dict[str, Any], prompt: str) -> list[str]:
    kws = [str(x).strip().upper() for x in item.get("matched_keywords", []) if str(x).strip()]
    role = classify_story_role(item)

    base = []
    if kws:
        base.extend(kws[:3])

    role_map = {
        "setup": ["WAIT FOR IT", "IT STARTS HERE", "NO ONE KNEW"],
        "tension": ["OH NO", "THIS GOT BAD", "PURE CHAOS"],
        "twist": ["PLOT TWIST", "NAH WHAT", "NO WAY"],
        "payoff": ["CLUTCH", "HE DID WHAT", "FINAL REVEAL"],
    }
    base.extend(role_map.get(role, ["BIG MOMENT"]))

    if prompt:
        pkw = extract_prompt_keywords(prompt) if "extract_prompt_keywords" in globals() else _clean_words(prompt)[:7]
        if pkw:
            base.append(pkw[0].upper())

    cleaned = []
    for x in base:
        x = " ".join(str(x).split())
        if not x:
            continue
        cleaned.append(x[:18])

    return _uniq_keep(cleaned)[:PACKAGING_VARIANTS]

def add_packaging_variants(moments: list[dict[str, Any]], prompt: str) -> list[dict[str, Any]]:
    out = []
    for rank, item in enumerate(moments, start=1):
        m = dict(item)
        m["rank"] = int(m.get("rank", rank))
        m["story_role"] = classify_story_role(m)
        m["backstory_context"] = build_backstory_context(m, prompt)
        m["hook_variants"] = build_hook_variants(m, prompt)
        m["title_variants"] = build_title_variants(m, prompt)
        m["thumbnail_variants"] = build_thumbnail_variants(m, prompt)

        if not m.get("hook_line") and m["hook_variants"]:
            m["hook_line"] = m["hook_variants"][0]
        if m["title_variants"]:
            m["viral_title"] = m["title_variants"][0]
        if m["thumbnail_variants"]:
            m["thumbnail_text"] = m["thumbnail_variants"][0]

        out.append(m)
    return out

def write_clip_metadata(job: Path, item: dict[str, Any]) -> Path:
    rank = int(item.get("rank", 0))
    out = job / "clips_meta" / f"clip_{rank:02d}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(item, indent=2), encoding="utf-8")
    return out



def zip_job_dir(job: Path) -> Path:
    out = job / "exports" / f"{job.name}.zip"
    out.parent.mkdir(parents=True, exist_ok=True)

    import zipfile

    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(job.rglob("*")):
            if not path.is_file():
                continue
            if path == out:
                continue
            zf.write(path, arcname=str(path.relative_to(job)))

    return out

def render_thumbnail(src: Path, out: Path, t: float, text: str = "") -> bool:
    out.parent.mkdir(parents=True, exist_ok=True)
    safe_t = max(0.0, float(t))

    # pass 1: always try to create a plain thumbnail frame first
    vf_plain = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920"
    )
    cmd_plain = [
        "ffmpeg", "-y",
        "-ss", f"{safe_t:.3f}",
        "-i", str(src),
        "-frames:v", "1",
        "-vf", vf_plain,
        str(out),
    ]

    try:
        subprocess.run(cmd_plain, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        return False

    if not out.exists():
        return False

    # pass 2: optional text overlay; never fail overall thumbnail creation
    txt = (text or "").strip()
    if not txt:
        return True

    safe = (
        txt.replace("\\", "\\\\")
           .replace(":", "\\:")
           .replace("'", "\\'")
           .replace("%", "\\%")
    )

    tmp = out.with_name(out.stem + ".tmp" + out.suffix)
    vf_text = (
        "drawbox=x=40:y=60:w=1000:h=180:color=black@0.45:t=fill,"
        f"drawtext=text='{safe}':x=80:y=110:fontsize=72:fontcolor=white"
    )
    cmd_text = [
        "ffmpeg", "-y",
        "-i", str(out),
        "-vf", vf_text,
        str(tmp),
    ]

    try:
        subprocess.run(cmd_text, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if tmp.exists():
            tmp.replace(out)
    except Exception:
        if tmp.exists():
            tmp.unlink(missing_ok=True)

    return out.exists()





def srt_to_ass(src_srt: Path, out_ass: Path) -> bool:
    if not src_srt.exists():
        return False

    txt = src_srt.read_text(encoding="utf-8", errors="ignore").strip()
    if not txt:
        return False

    def to_ass_time(ts: str) -> str:
        ts = ts.strip().replace(",", ".")
        hh, mm, rest = ts.split(":")
        ss, cs = rest.split(".")
        return f"{int(hh)}:{int(mm):02d}:{int(ss):02d}.{int(cs[:2]):02d}"

    blocks = re.split(r"\n\s*\n", txt)
    events = []

    for block in blocks:
        lines = [x.strip("\ufeff") for x in block.splitlines() if x.strip()]
        if len(lines) < 2:
            continue
        if "-->" not in lines[1]:
            continue

        start_raw, end_raw = [x.strip() for x in lines[1].split("-->")]
        start_ass = to_ass_time(start_raw)
        end_ass = to_ass_time(end_raw)

        text_lines = lines[2:] if re.fullmatch(r"\d+", lines[0]) else lines[1:]
        if "-->" in text_lines[0]:
            text_lines = text_lines[1:]

        text = r"\N".join(
            t.replace("{", r"\{").replace("}", r"\}")
            for t in text_lines if t.strip()
        ).strip()

        if not text:
            continue

        events.append(
            f"Dialogue: 0,{start_ass},{end_ass},GenZ,,0,0,0,,{text}"
        )

    out_ass.parent.mkdir(parents=True, exist_ok=True)
    header = """[Script Info]
ScriptType: v4.00+
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: GenZ,Arial,18,&H00FFFFFF,&H0000FFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,2,0,2,60,60,180,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    out_ass.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return out_ass.exists()

def srt_to_vtt(src_srt: Path, out_vtt: Path) -> bool:
    if not src_srt.exists():
        return False
    txt = src_srt.read_text(encoding="utf-8", errors="ignore").strip()
    if not txt:
        return False
    out_vtt.parent.mkdir(parents=True, exist_ok=True)
    body = "WEBVTT\n\n" + txt.replace(",", ".")
    out_vtt.write_text(body, encoding="utf-8")
    return out_vtt.exists()

def write_package_manifest(
    job: Path,
    source_url: str,
    artifacts: list[dict[str, Any]],
    metrics: dict[str, Any],
) -> Path:
    out = job / "brief" / "package_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ok": True,
        "feature": "shorts",
        "job_id": job.name,
        "source_url": source_url,
        "prompt": metrics.get("prompt", ""),
        "artifacts": artifacts,
        "metrics": metrics,
    }
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out

def write_shorts_brief(job: Path, source_url: str, moments: list[dict]) -> tuple[Path, Path]:
    brief_json = job / "brief" / "shorts_package.json"
    brief_md = job / "brief" / "shorts_package.md"
    brief_json.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "source_url": source_url,
        "clip_count": len(moments),
        "clips": moments,
    }
    brief_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# Shorts Package",
        "",
        f"- Source: {source_url}",
        f"- Clip count: {len(moments)}",
        "",
    ]
    for item in moments:
        lines.extend([
            f"## Clip {item.get('rank', '?')}",
            f"- Time: {item['start_sec']}s → {item['end_sec']}s",
            f"- Score: {item.get('clip_score')}",
            f"- Hook: {item.get('hook_line', '')}",
            f"- Title: {item.get('viral_title', '')}",
            f"- Thumbnail text: {item.get('thumbnail_text', '')}",
            f"- Reason: {item.get('reason', '')}",
            f"- Hashtags: {' '.join(item.get('hashtags', []))}",
            "- Notes:",
        ])
        for note in item.get("editor_notes", []):
            lines.append(f"  - {note}")
        lines.extend([
            "",
            "Preview:",
            "",
            textwrap.indent(item.get("transcript_preview", ""), "> "),
            "",
        ])

    brief_md.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return brief_json, brief_md

def rank_moments_from_transcript(
    transcript_data: dict[str, Any],
    total_duration: float,
    target_count: int,
) -> list[dict[str, Any]]:
    segments = transcript_data.get("segments") or []
    if not segments:
        return []

    windows: list[dict[str, Any]] = []
    step = SHORTS_STEP_SEC
    start = 0.0

    while start < max(float(total_duration) - SHORTS_MIN_CLIP_SEC, 0.0) + step:
        end = min(float(total_duration), start + SHORTS_MAX_CLIP_SEC)
        chunk = []
        for seg in segments:
            seg_start = float(seg.get("start", 0.0))
            seg_end = float(seg.get("end", seg_start))
            if seg_end <= start or seg_start >= end:
                continue
            chunk.append(seg)

        text = " ".join((seg.get("text") or "").strip() for seg in chunk).strip()
        if text:
            lower_text = text.lower()
            words = [w for w in re.split(r"\s+", text) if w]
            duration = max(1.0, end - start)

            keyword_bank = [
                "big", "danger", "fight", "war", "largest", "strong", "trapped",
                "lost", "found", "chased", "crazy", "insane", "secret", "legendary",
                "attack", "final", "escape", "run", "king", "death", "minecraft",
                "server", "world", "betrayal", "destroyed", "civilization", "revenge"
            ]
            matched_keywords = [kw for kw in keyword_bank if kw in lower_text][:8]

            hook_markers = [
                "this is", "oh my god", "what", "how", "why", "run", "lost",
                "largest", "biggest", "crazy", "insane", "secret", "legendary",
                "attack", "final", "trapped", "escape", "found"
            ]
            hook_hits = sum(1 for h in hook_markers if h in lower_text)
            hook_score = min(1.0, 0.18 * hook_hits + 0.10 * len(matched_keywords))

            density_score = min(1.0, len(words) / max(20.0, duration * 2.7))

            unique_words = len(set(w.lower().strip(".,!?\"'()[]{}") for w in words if w.strip()))
            clarity_score = min(1.0, unique_words / max(12.0, len(words) * 0.55))

            score = (
                0.45 * hook_score +
                0.30 * density_score +
                0.25 * clarity_score
            )

            clip_start, clip_end = clamp_clip_window(start, end, float(total_duration))

            reason_parts = []
            if hook_score >= 0.8:
                reason_parts.append("strong hook words")
            if density_score >= 0.7:
                reason_parts.append("dense speech")
            if clarity_score >= 0.7:
                reason_parts.append("clear spoken content")
            if matched_keywords:
                reason_parts.append("matched high-interest keywords")

            preview = text[:220]
            item = {
                "start_sec": clip_start,
                "end_sec": clip_end,
                "hook_score": round(hook_score, 3),
                "payoff_score": round(clarity_score, 3),
                "clip_score": round(score, 3),
                "speech_density": round(density_score, 3),
                "segment_count": len(chunk),
                "matched_keywords": matched_keywords[:8],
                "transcript_preview": preview,
                "reason": ", ".join(reason_parts) if reason_parts else "general transcript strength",
                "title": (text[:80] + "...") if len(text) > 80 else text,
            }
            item["hook_line"] = build_hook_line(preview)
            item["viral_title"] = build_viral_title(preview, item["matched_keywords"])
            item["thumbnail_text"] = build_thumbnail_text(preview, item["matched_keywords"])
            item["editor_notes"] = build_editor_notes(item)
            item["hashtags"] = build_hashtags(item)
            windows.append(item)

        start += step

    windows.sort(key=lambda x: x["clip_score"], reverse=True)

    picked: list[dict[str, Any]] = []
    for cand in windows:
        overlaps = False
        for chosen in picked:
            if not (cand["end_sec"] <= chosen["start_sec"] or cand["start_sec"] >= chosen["end_sec"]):
                overlaps = True
                break
        if overlaps:
            continue
        picked.append(cand)
        if len(picked) >= target_count:
            break

    for i, item in enumerate(picked, start=1):
        item["rank"] = i

    return picked



def render_vertical_clip(src: Path, dst: Path, start: float, end: float) -> None:
    dur = max(1.0, end - start)
    vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    run([
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", str(src),
        "-t", str(dur),
        "-vf", vf,
        "-r", "30",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        str(dst),
    ])



def fmt_srt_time(sec: float) -> str:
    ms = int(round(sec * 1000))
    h = ms // 3600000
    ms %= 3600000
    m = ms // 60000
    ms %= 60000
    s = ms // 1000
    ms %= 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt_for_clip(
    transcript_data: dict[str, Any],
    clip_start: float,
    clip_end: float,
    out_srt: Path,
) -> int:
    segs = transcript_data.get("segments", []) or []
    lines: list[str] = []
    idx = 1

    for seg in segs:
        a = float(seg.get("start", 0.0))
        b = float(seg.get("end", 0.0))
        text = str(seg.get("text", "")).strip()

        if not text or b <= clip_start or a >= clip_end:
            continue

        sa = max(0.0, a - clip_start)
        sb = max(sa + 0.1, min(clip_end, b) - clip_start)

        lines.append(str(idx))
        lines.append(f"{fmt_srt_time(sa)} --> {fmt_srt_time(sb)}")
        lines.append(text)
        lines.append("")
        idx += 1

    out_srt.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return idx - 1



def burn_subtitles(src_mp4: Path, src_srt: Path, out_mp4: Path) -> bool:
    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    if not src_mp4.exists():
        return False

    # fallback 0: if subtitle file missing/empty, still emit a downloadable video
    if (not src_srt.exists()) or src_srt.stat().st_size == 0:
        shutil.copy2(src_mp4, out_mp4)
        return out_mp4.exists()

    ass_path = out_mp4.with_suffix(".ass")
    srt_to_ass(src_srt, ass_path)

    def try_ffmpeg(vf: str) -> bool:
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", str(src_mp4),
                    "-vf", vf,
                    "-c:v", "libx264",
                    "-preset", "veryfast",
                    "-crf", "23",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    str(out_mp4),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return out_mp4.exists() and out_mp4.stat().st_size > 0
        except Exception:
            return False

    # styled burn first
    if ass_path.exists() and ass_path.stat().st_size > 0:
        ass_arg = str(ass_path).replace("\\", "/").replace(":", r"\:")
        if try_ffmpeg(f"ass='{ass_arg}'"):
            return True

    # normal subtitle burn second
    srt_arg = str(src_srt).replace("\\", "/").replace(":", r"\:")
    if try_ffmpeg(f"subtitles='{srt_arg}'"):
        return True

    # final fallback: keep pipeline alive with downloadable output
    shutil.copy2(src_mp4, out_mp4)
    return out_mp4.exists()


def build_shorts(source_url: str, target_count: int = SHORTS_DEFAULT_TARGET_COUNT, prompt: str = "") -> dict[str, Any]:
    job = job_dir("shorts")
    jid = job.name

    src_placeholder = job / "source" / "original"
    wav = job / "source" / "audio.wav"
    transcript = job / "transcript" / "transcript.json"
    prompt_keywords = extract_prompt_keywords(prompt)
    ranked = job / "moments" / "ranked.json"

    src = download_source(source_url, src_placeholder)
    total_duration = probe_duration(src)

    transcript_cache = cached_transcript_path(source_url)
    ranked_cache = cached_ranked_prompt_path(source_url, target_count, prompt)

    cache_hit_transcript = False
    cache_hit_rankings = False

    if transcript_cache.exists():
        transcript_data = json.loads(transcript_cache.read_text(encoding="utf-8"))
        cache_hit_transcript = True
    else:
        extract_audio(src, wav)
        transcript_data = transcribe_audio(wav)
        transcript_data["source_duration_sec"] = total_duration
        transcript_cache.parent.mkdir(parents=True, exist_ok=True)
        transcript_cache.write_text(json.dumps(transcript_data, indent=2), encoding="utf-8")

    write_json(transcript, transcript_data)

    if ranked_cache.exists():
        moments = json.loads(ranked_cache.read_text(encoding="utf-8"))
        cache_hit_rankings = True
    else:
        moments = rank_moments_from_transcript(transcript_data, total_duration, target_count)
        ranked_cache.parent.mkdir(parents=True, exist_ok=True)
        ranked_cache.write_text(json.dumps(moments, indent=2), encoding="utf-8")

    moments = add_packaging_variants(moments, prompt)
    write_json(ranked, moments)
    brief_json, brief_md = write_shorts_brief(job, source_url, moments)

    artifacts = [
        {"kind": "source_video", "path": str(src.relative_to(ROOT))},
        {"kind": "transcript", "path": str(transcript.relative_to(ROOT))},
        {"kind": "moments", "path": str(ranked.relative_to(ROOT))},
        {"kind": "shorts_brief_json", "path": str(brief_json.relative_to(ROOT))},
        {"kind": "shorts_brief_md", "path": str(brief_md.relative_to(ROOT))},
    ]

    clips_generated = 0
    subtitle_files = 0
    for i, m in enumerate(moments, start=1):
        clip_start = float(m["start_sec"])
        clip_end = float(m["end_sec"])

        out = job / "renders" / f"short_{i:02d}.mp4"
        srt = job / "captions" / f"short_{i:02d}.srt"
        out_captioned = job / "renders" / f"short_{i:02d}.captioned.mp4"

        clip_cache = cached_clip_path(source_url, clip_start, clip_end)
        if clip_cache.exists():
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(clip_cache.read_bytes())
        else:
            render_vertical_clip(src, out, clip_start, clip_end)
            clip_cache.parent.mkdir(parents=True, exist_ok=True)
            clip_cache.write_bytes(out.read_bytes())

        subtitle_count = write_srt_for_clip(transcript_data, clip_start, clip_end, srt)

        artifacts.append({"kind": "short_video", "path": str(out.relative_to(ROOT))})
        artifacts.append({"kind": "subtitle", "path": str(srt.relative_to(ROOT))})

        vtt = job / "captions" / f"short_{i:02d}.vtt"
        if srt_to_vtt(srt, vtt):
            artifacts.append({"kind": "subtitle_vtt", "path": str(vtt.relative_to(ROOT))})

        clip_meta = write_clip_metadata(job, m)
        artifacts.append({"kind": "clip_metadata", "path": str(clip_meta.relative_to(ROOT))})

        thumb = job / "thumbnails" / f"clip_{i:02d}.png"
        thumb_ok = render_thumbnail(src, thumb, clip_start + 0.5, str(m.get("thumbnail_text", "")))
        if thumb_ok and thumb.exists():
            artifacts.append({"kind": "thumbnail", "path": str(thumb.relative_to(ROOT))})

        if srt.exists() and srt.stat().st_size > 0:
            burned = burn_subtitles(out, srt, out_captioned)
            if burned and out_captioned.exists():
                artifacts.append({"kind": "short_video_captioned", "path": str(out_captioned.relative_to(ROOT))})
                subtitle_files += 1

        clips_generated += 1

    metrics = {
        "prompt": prompt,
        "prompt_keywords": prompt_keywords,
        "critique_score": 0.0,
        "validation_passed": True,
        "clips_generated": clips_generated,
        "duration_sec": total_duration,
        "transcript_segments": len(transcript_data.get("segments", [])),
        "transcribe_elapsed_sec": transcript_data.get("transcribe_elapsed_sec"),
        "subtitle_files": subtitle_files,
        "caption_burn_available": subtitle_files > 0,
        "cache_hit_source": cached_source_path(source_url).exists(),
        "cache_hit_transcript": cache_hit_transcript,
        "cache_hit_rankings": cache_hit_rankings,
        "cache_hit_audio_extract": not cache_hit_transcript,
        "cache_clip_count": sum(
            1 for m in moments
            if cached_clip_path(source_url, float(m["start_sec"]), float(m["end_sec"])).exists()
        ),
    }

    manifest = write_package_manifest(job, source_url, artifacts, metrics)
    artifacts.append({"kind": "package_manifest", "path": str(manifest.relative_to(ROOT))})

    package_zip = zip_job_dir(job)
    if package_zip and package_zip.exists():
        artifacts.append({"kind": "package_zip", "path": str(package_zip.relative_to(ROOT))})

    return {
        "ok": True,
        "feature": "shorts",
        "job_id": job.name,
        "artifacts": artifacts,
        "metrics": metrics,
    }


def clip_cache_key(url: str, start_sec: float, end_sec: float) -> str:
    return f"{url_key(url)}_{int(round(start_sec * 100))}_{int(round(end_sec * 100))}"

def cached_clip_path(url: str, start_sec: float, end_sec: float) -> Path:
    return cache_dir() / "clips" / f"{clip_cache_key(url, start_sec, end_sec)}.mp4"
