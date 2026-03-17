#!/usr/bin/env python3
from __future__ import annotations

import json
import os
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

STOP = {
    "the","a","an","and","or","but","of","to","in","on","for","with","from","at","by",
    "is","it","this","that","these","those","was","were","be","been","are","as","he",
    "she","they","them","you","we","i","his","her","their","our","my","your"
}

STYLE_TEMPLATES = [
    "{topic} 😂 #shorts",
    "Do You Remember {topic}? 🥺 #shorts",
    "{creator} {topic}.. 💀 | #shorts",
    "They Got Scared From {topic} ☠️🔥 | {series} #shorts",
    "The Guy That Died To {topic} | {series} #shorts",
    "Most Underrated {series} Players",
    "{creator} Almost Lost Because Of {topic} 😭 #shorts",
    "{topic} Changed Everything 😳 | {series} #shorts",
    "{creator} Was NOT Ready For {topic} 💀 #shorts",
    "This {topic} Moment Was Insane 🔥 #shorts",
]

SERIES_DEFAULT = os.environ.get("MYTHIQ_SERIES_NAME", "Unstable SMP")

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
    return (Path.cwd() / s).resolve()

def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def safe_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

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

def pick_creator(text: str, creators: list[str], idx: int) -> str:
    t = text.lower()
    for c in creators:
        if c.lower() in t:
            return c
    return creators[idx % len(creators)] if creators else "Minecraft"

def normalize_topic(s: str) -> str:
    s = safe_text(s)
    s = re.sub(r'[#|]+', ' ', s)
    s = re.sub(r'\b(shorts|trending|viral|minecraft|smp)\b', ' ', s, flags=re.I)
    s = re.sub(r'[^A-Za-z0-9\' ]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def keywords_from_text(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9']+", text)
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
    return uniq

def best_topic_for_clip(clip: dict[str, Any]) -> str:
    candidates = []

    for key in [
        "title",
        "hook",
        "summary",
        "caption",
        "description",
        "transcript",
        "clip_title",
        "scene_title"
    ]:
        v = clip.get(key)
        if isinstance(v, str) and v.strip():
            candidates.append(v.strip())

    joined = " ".join(candidates)
    kws = keywords_from_text(joined)

    phrases = []
    if len(kws) >= 2:
        phrases.append(f"{kws[0]} {kws[1]}")
    if len(kws) >= 3:
        phrases.append(f"{kws[0]} {kws[1]} {kws[2]}")
    if len(kws) >= 1:
        phrases.append(kws[0])

    for c in candidates:
        n = normalize_topic(c)
        if 4 <= len(n) <= 28:
            phrases.append(n)

    cleaned = []
    seen = set()
    for p in phrases:
        p = normalize_topic(p)
        if not p:
            continue
        if len(p) < 4:
            continue
        key = p.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(p)

    if cleaned:
        cleaned.sort(key=lambda x: (
            -int(8 <= len(x) <= 24),
            -len(x.split()),
            -len(x)
        ))
        return cleaned[0]

    return "Minecraft Moment"

def make_title_for_clip(clip: dict[str, Any], creator: str, idx: int, series: str) -> str:
    topic = best_topic_for_clip(clip)

    titles = []
    for tmpl in STYLE_TEMPLATES:
        t = tmpl.format(
            topic=topic,
            creator=creator,
            series=series
        )
        t = safe_text(t)
        t = re.sub(r"\s+\|\s+#shorts", " | #shorts", t)
        t = re.sub(r"\s{2,}", " ", t).strip()
        if len(t) > 68:
            t = t[:68].rstrip() + "..."
        titles.append(t)

    def score_title(t: str) -> tuple:
        tl = t.lower()
        return (
            -int(38 <= len(t) <= 62),
            -int(topic.lower() in tl),
            -int(creator.lower() in tl),
            -int(series.lower() in tl),
            -int("#shorts" in tl),
            abs(len(t) - 52),
        )

    titles.sort(key=score_title)
    return titles[0]

def make_caption(title: str, creator: str) -> str:
    return safe_text(
        f"{title}\n"
        f"Fast-paced Minecraft short featuring {creator}.\n"
        f"#shorts #minecraft #{creator.lower()} #gaming #unstablesmp"
    )

def score_clip(title: str, topic: str, creator: str) -> float:
    score = 50.0
    if 38 <= len(title) <= 62:
        score += 10
    if creator.lower() in title.lower():
        score += 8
    if topic.lower() in title.lower():
        score += 12
    if "#shorts" in title.lower():
        score += 4
    return round(score, 2)

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
    series = SERIES_DEFAULT

    for i, clip in enumerate(clips, start=1):
        source_url = clip.get("captioned_video_url") or clip.get("video_url")
        if not source_url:
            continue

        src = url_to_local_path(source_url)
        if not src.exists():
            print(f"missing source clip: {src}", file=sys.stderr)
            continue

        raw_text = " ".join([
            str(clip.get("title") or ""),
            str(clip.get("hook") or ""),
            str(clip.get("summary") or ""),
            str(clip.get("caption") or ""),
            str(clip.get("description") or ""),
            str(clip.get("transcript") or ""),
        ]).strip()

        creator = pick_creator(raw_text, creators, i - 1)
        topic = best_topic_for_clip(clip)
        new_title = make_title_for_clip(clip, creator, i - 1, series)
        caption = make_caption(new_title, creator)
        score = score_clip(new_title, topic, creator)

        dst = renders / f"short_{i:02d}_fast.mp4"
        build_fast_clip(src, dst, speed=1.05, max_len=18.0)

        (meta / f"short_{i:02d}.title.txt").write_text(new_title + "\n", encoding="utf-8")
        (meta / f"short_{i:02d}.caption.txt").write_text(caption + "\n", encoding="utf-8")
        (meta / f"short_{i:02d}.topic.txt").write_text(topic + "\n", encoding="utf-8")
        (meta / f"short_{i:02d}.hashtags.txt").write_text(
            f"#shorts\n#minecraft\n#{creator.lower()}\n#gaming\n#unstablesmp\n",
            encoding="utf-8"
        )

        ranking.append({
            "index": i,
            "creator": creator,
            "topic": topic,
            "source_title": clip.get("title"),
            "title": new_title,
            "score": score,
            "source_video": str(src),
            "fast_video": str(dst),
        })

    ranking.sort(key=lambda x: x["score"], reverse=True)
    write_json(meta / "ranking.json", ranking)

    md = ["# Fastlane Shorts Pack", ""]
    for r in ranking:
        md.append(f"## {r['index']:02d} — {r['title']}")
        md.append(f"- creator: {r['creator']}")
        md.append(f"- topic: {r['topic']}")
        md.append(f"- score: {r['score']}")
        md.append(f"- fast_video: `{r['fast_video']}`")
        md.append("")
    (meta / "ranking.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"FASTLANE_OK job_id={job_id} clips={len(ranking)} out={out_root}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
