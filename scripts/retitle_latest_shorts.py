#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

API_LATEST = os.environ.get("MYTHIQ_REVIEW_API", "http://127.0.0.1:8788/api/latest")
SERIES = os.environ.get("MYTHIQ_SERIES_NAME", "Unstable SMP")
CREATORS = [x.strip() for x in os.environ.get(
    "MYTHIQ_CREATORS",
    "Unstable,Parrot,Flame,Wemmbu,Spoke"
).split(",") if x.strip()]

STOP = {
    "the","a","an","and","or","but","of","to","in","on","for","with","from","at","by",
    "is","it","this","that","these","those","was","were","be","been","are","as","he",
    "she","they","them","you","we","i","his","her","their","our","my","your","just",
    "really","very","then","than","have","has","had","what","when","where","why","how",
    "into","over","under","again","still","about","because","while","after","before",
    "minecraft","shorts","short","video","clip"
}

STYLE_TEMPLATES = [
    "{topic} 😂 #shorts",
    "{creator} {topic}.. 💀 | #shorts",
    "{creator} Was NOT Ready For {topic} 💀 #shorts",
    "They Got Scared From {topic} ☠️🔥 | {series} #shorts",
    "The Guy That Died To {topic} | {series} #shorts",
    "{topic} Changed Everything 😳 | {series} #shorts",
    "{creator} Almost Lost Because Of {topic} 😭 #shorts",
    "This {topic} Moment Was Insane 🔥 #shorts",
    "{creator} {topic} Was Crazy 😳 #shorts",
    "{topic} In {series} 💀 #shorts",
]

def safe_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def fetch_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read().decode("utf-8"))

def fetch_text(url: str) -> str:
    try:
        with urllib.request.urlopen(url) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""

def strip_subs(text: str) -> str:
    lines = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        if re.fullmatch(r"\d+", s):
            continue
        if "-->" in s:
            continue
        s = re.sub(r"<[^>]+>", " ", s)
        s = re.sub(r"{\\[^}]+}", " ", s)
        s = re.sub(r"\[[^\]]+\]", " ", s)
        s = re.sub(r"\([^)]+\)", " ", s)
        s = safe_text(s)
        if s:
            lines.append(s)
    return " ".join(lines)

def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z0-9']+", text)

def pick_creator(text: str, idx: int) -> str:
    tl = text.lower()
    for c in CREATORS:
        if c.lower() in tl:
            return c
    return CREATORS[idx % len(CREATORS)] if CREATORS else "Minecraft"

def normalize_topic(s: str) -> str:
    s = safe_text(s)
    s = re.sub(r"[^A-Za-z0-9' ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def extract_topic_candidates(text: str) -> list[str]:
    toks = words(text)
    clean = []
    for t in toks:
        tl = t.lower()
        if tl in STOP:
            continue
        if len(t) < 4:
            continue
        clean.append(t)

    phrases = []
    # 2-grams and 3-grams
    for n in (3, 2):
        for i in range(len(clean) - n + 1):
            p = " ".join(clean[i:i+n])
            if 6 <= len(p) <= 28:
                phrases.append(p)

    # single strong words last
    for t in clean:
        if 5 <= len(t) <= 16:
            phrases.append(t)

    # prefer action/event words if present
    priority = []
    event_words = [
        "trap","fight","clutch","lava","egg","base","death","fall","chase","duel",
        "steal","tnt","border","escape","hide","raid","jump","panic","scared",
        "ambush","sneak","betrayal","payback","revenge","spawn","secret","tower",
        "bridge","diamond","nether","portal","void","explosion"
    ]
    for p in phrases:
        pl = p.lower()
        if any(w in pl for w in event_words):
            priority.append(p)

    ordered = priority + phrases

    out = []
    seen = set()
    for p in ordered:
        p = normalize_topic(p)
        k = p.lower()
        if not p or k in seen:
            continue
        seen.add(k)
        out.append(p)
    return out

def best_topic(clip: dict[str, Any], idx: int) -> tuple[str, list[str], str]:
    subtitle_text = ""
    for key in ("subtitle_vtt_url", "subtitle_url"):
        url = clip.get(key)
        if isinstance(url, str) and url:
            subtitle_text = fetch_text("http://127.0.0.1:8788" + url if url.startswith("/") else url)
            subtitle_text = strip_subs(subtitle_text)
            if subtitle_text:
                break

    source_bits = [
        str(clip.get("title") or ""),
        str(clip.get("hook") or ""),
        str(clip.get("summary") or ""),
        str(clip.get("description") or ""),
        str(clip.get("caption") or ""),
        subtitle_text,
    ]
    blob = safe_text(" ".join(x for x in source_bits if x))
    cands = extract_topic_candidates(blob)

    if cands:
        return cands[0], cands, blob
    return "Minecraft Moment", ["Minecraft Moment"], blob

def make_title(creator: str, topic: str, topic_candidates: list[str], used: set[str]) -> str:
    variants = []
    topics = topic_candidates[:4] if topic_candidates else [topic]

    for tp in topics:
        for tmpl in STYLE_TEMPLATES:
            t = tmpl.format(topic=tp, creator=creator, series=SERIES)
            t = safe_text(t)
            if len(t) > 66:
                t = t[:66].rstrip() + "..."
            variants.append(t)

    def score(t: str) -> tuple:
        tl = t.lower()
        return (
            -int(38 <= len(t) <= 62),
            -int(topic.lower() in tl),
            -int(creator.lower() in tl),
            -int("#shorts" in tl),
            -sum(int(x in tl) for x in ["story with a setup twist", "story tension", "story payoff"]),
            abs(len(t) - 52),
        )

    variants = sorted(dict.fromkeys(variants), key=score)

    for t in variants:
        if t.lower() not in used:
            used.add(t.lower())
            return t

    fallback = f"{creator} {topic} 💀 #shorts"
    if len(fallback) > 66:
        fallback = fallback[:66].rstrip() + "..."
    used.add(fallback.lower())
    return fallback

def main() -> int:
    data = fetch_json(API_LATEST)
    if not data.get("ok"):
        print("latest payload not ok", file=sys.stderr)
        return 1

    job_id = data.get("job_id")
    clips = data.get("clips") or []
    if not job_id or not clips:
        print("missing latest job/clips", file=sys.stderr)
        return 1

    fastlane_meta = Path("artifacts") / job_id / "fastlane" / "meta"
    fastlane_meta.mkdir(parents=True, exist_ok=True)

    used_titles: set[str] = set()
    ranking = []

    for i, clip in enumerate(clips, start=1):
        topic, topic_candidates, blob = best_topic(clip, i - 1)
        creator = pick_creator(blob, i - 1)
        title = make_title(creator, topic, topic_candidates, used_titles)

        (fastlane_meta / f"short_{i:02d}.topic.txt").write_text(topic + "\n", encoding="utf-8")
        (fastlane_meta / f"short_{i:02d}.title.txt").write_text(title + "\n", encoding="utf-8")
        (fastlane_meta / f"short_{i:02d}.caption.txt").write_text(
            f"{title}\n#shorts #minecraft #{creator.lower()} #gaming #unstablesmp\n",
            encoding="utf-8"
        )

        ranking.append({
            "index": i,
            "creator": creator,
            "topic": topic,
            "topic_candidates": topic_candidates[:5],
            "title": title,
            "source_title": clip.get("title"),
            "subtitle_url": clip.get("subtitle_url"),
            "subtitle_vtt_url": clip.get("subtitle_vtt_url"),
        })

    (fastlane_meta / "ranking.json").write_text(
        json.dumps(ranking, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )

    md = ["# Retitled Shorts", ""]
    for r in ranking:
        md.append(f"## {r['index']:02d}. {r['title']}")
        md.append(f"- creator: {r['creator']}")
        md.append(f"- topic: {r['topic']}")
        md.append(f"- candidates: {', '.join(r['topic_candidates'])}")
        md.append("")
    (fastlane_meta / "ranking.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"RETITLE_OK job_id={job_id} clips={len(ranking)} meta={fastlane_meta}")
    for r in ranking:
        print(f"{r['index']:02d}. {r['title']}")
        print(f"    topic={r['topic']} | creator={r['creator']} | candidates={r['topic_candidates'][:3]}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
