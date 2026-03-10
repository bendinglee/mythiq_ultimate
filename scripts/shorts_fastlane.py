#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import os
import random
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any

API_LATEST = os.environ.get("MYTHIQ_REVIEW_API", "http://127.0.0.1:8788/api/latest")
BASE_MEDIA = os.environ.get("MYTHIQ_REVIEW_BASE", "http://127.0.0.1:8788")
DEFAULT_CREATORS = [x.strip() for x in os.environ.get(
    "MYTHIQ_CREATORS",
    "Unstable,Parrot,Flame,Wemmbu,Spoke"
).split(",") if x.strip()]

HOOKS = [
    "This Went Completely Wrong",
    "They Were NOT Ready For This",
    "The Craziest Moment",
    "This Escalated Fast",
    "Nobody Expected This",
    "The Funniest Moment",
    "This Changed Everything",
    "The Cleanest Play",
    "This Was Actually Insane",
    "The Wildest SMP Moment",
]

TAILS = [
    "#shorts",
    "| Unstable SMP #shorts",
    "😳 #shorts",
    "💀 #shorts",
    "🔥 #shorts",
    "😂 #shorts",
]

STOP = {
    "the","a","an","and","or","but","of","to","in","on","for","with","from","at","by",
    "is","it","this","that","these","those","was","were","be","been","are","as"
}

def sh(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)

def load_latest() -> dict[str, Any]:
    with urllib.request.urlopen(API_LATEST) as r:
        return json.loads(r.read().decode("utf-8"))

def url_to_local_path(url_or_path: str) -> Path:
    s = url_or_path
    if s.startswith("http://") or s.startswith("https://"):
        s = re.sub(r"^https?://[^/]+", "", s)
    if s.startswith("/files/"):
        s = s[len("/files/"):]
    s = s.lstrip("/")
    p = Path.cwd() / s
    return p.resolve()

def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def safe_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def pick_creator(title: str, creators: list[str], idx: int) -> str:
    t = title.lower()
    for c in creators:
        if c.lower() in t:
            return c
    return creators[idx % len(creators)] if creators else "Minecraft"

def extract_keywords(title: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9']+", title)
    out = []
    for w in words:
        wl = w.lower()
        if wl not in STOP and len(w) >= 4:
            out.append(w)
    seen = set()
    uniq = []
    for w in out:
        k = w.lower()
        if k not in seen:
            seen.add(k)
            uniq.append(w)
    return uniq[:4]

def make_title(orig_title: str, creator: str, idx: int) -> str:
    kws = extract_keywords(orig_title)
    hook = HOOKS[idx % len(HOOKS)]
    tail = TAILS[idx % len(TAILS)]

    variants = []
    if kws:
        variants.append(f"{creator} {hook} With {' '.join(kws[:2])} {tail}")
        variants.append(f"{creator} {' '.join(kws[:2])} {hook} {tail}")
        variants.append(f"{' '.join(kws[:2])} Broke The SMP {tail}")
    variants.append(f"{creator} {hook} {tail}")
    variants.append(f"{hook} | {creator} {tail}")

    cleaned = []
    for v in variants:
        v = safe_text(v)
        v = re.sub(r"\s+\| \|", " |", v)
        v = re.sub(r"\s{2,}", " ", v).strip()
        if len(v) > 70:
            v = v[:67].rstrip() + "..."
        cleaned.append(v)

    best = sorted(cleaned, key=lambda x: (
        -int(40 <= len(x) <= 62),
        -sum(int(c in x.lower()) for c in [creator.lower(), "smp", "minecraft", "shorts"]),
        -len(extract_keywords(x)),
        -len(x)
    ))[0]
    return best

def make_caption(title: str, creator: str) -> str:
    return safe_text(
        f"{title}\n"
        f"Fast-paced Minecraft short featuring {creator}. "
        f"High-retention pacing, hard cuts, vertical format, clean replay value.\n"
        f"#shorts #minecraft #{creator.lower()} #gaming #unstablesmp"
    )

def score_clip(idx: int, clip: dict[str, Any]) -> float:
    t = safe_text(clip.get("title") or "")
    score = 50.0
    if any(x in t.lower() for x in ["craziest", "insane", "wrong", "funniest", "wildest"]):
        score += 12
    if any(x in t.lower() for x in ["unstable", "parrot", "flame", "wemmbu", "spoke"]):
        score += 8
    if any(x in t.lower() for x in ["smp", "minecraft"]):
        score += 6
    if 38 <= len(t) <= 62:
        score += 10
    score += max(0, 6 - abs((idx % 6) - 3))
    return round(score, 2)

def ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ]).decode("utf-8", errors="ignore").strip()
    return float(out or "0")

def build_fast_clip(src: Path, dst: Path, speed: float = 1.05, max_len: float = 18.0) -> None:
    dur = ffprobe_duration(src)
    keep = min(dur, max_len)
    vf = (
        f"trim=0:{keep},"
        f"setpts=PTS/{speed},"
        f"scale=1080:1920:force_original_aspect_ratio=increase,"
        f"crop=1080:1920,"
        f"unsharp=5:5:0.8:3:3:0.4,"
        f"fps=30"
    )
    af = f"atrim=0:{keep},atempo={speed},loudnorm=I=-14:TP=-1.5:LRA=11"
    sh([
        "ffmpeg", "-y",
        "-i", str(src),
        "-vf", vf,
        "-af", af,
        "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "21",
        "-c:a", "aac",
        "-b:a", "192k",
        str(dst),
    ])

def main() -> int:
    data = load_latest()
    if not data.get("ok"):
        print("latest payload not ok", file=sys.stderr)
        return 1

    job_id = data.get("job_id", "unknown_job")
    clips = data.get("clips") or []
    if not clips:
        print("no clips in latest payload", file=sys.stderr)
        return 1

    out_root = Path.cwd() / "artifacts" / job_id / "fastlane"
    renders = out_root / "renders"
    meta = out_root / "meta"
    renders.mkdir(parents=True, exist_ok=True)
    meta.mkdir(parents=True, exist_ok=True)

    ranking = []
    creators = DEFAULT_CREATORS[:]

    for i, clip in enumerate(clips, start=1):
        source_url = clip.get("captioned_video_url") or clip.get("video_url")
        if not source_url:
            continue

        src = url_to_local_path(source_url)
        if not src.exists():
            print(f"missing source clip: {src}", file=sys.stderr)
            continue

        orig_title = safe_text(clip.get("title") or f"Clip {i}")
        creator = pick_creator(orig_title, creators, i - 1)
        new_title = make_title(orig_title, creator, i - 1)
        caption = make_caption(new_title, creator)
        score = score_clip(i, {"title": new_title})

        dst = renders / f"short_{i:02d}_fast.mp4"
        build_fast_clip(src, dst, speed=1.05, max_len=18.0)

        (meta / f"short_{i:02d}.title.txt").write_text(new_title + "\n", encoding="utf-8")
        (meta / f"short_{i:02d}.caption.txt").write_text(caption + "\n", encoding="utf-8")
        (meta / f"short_{i:02d}.hashtags.txt").write_text(
            f"#shorts\n#minecraft\n#{creator.lower()}\n#gaming\n#unstablesmp\n",
            encoding="utf-8"
        )

        row = {
            "index": i,
            "creator": creator,
            "source_title": orig_title,
            "title": new_title,
            "score": score,
            "source_video": str(src),
            "fast_video": str(dst),
        }
        ranking.append(row)

    ranking.sort(key=lambda x: x["score"], reverse=True)
    write_json(meta / "ranking.json", ranking)

    md = ["# Fastlane Shorts Pack", ""]
    for r in ranking:
        md.append(f"## {r['index']:02d} — {r['title']}")
        md.append(f"- creator: {r['creator']}")
        md.append(f"- score: {r['score']}")
        md.append(f"- fast_video: `{r['fast_video']}`")
        md.append("")
    (meta / "ranking.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"FASTLANE_OK job_id={job_id} clips={len(ranking)} out={out_root}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
