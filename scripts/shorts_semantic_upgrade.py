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
BASE = os.environ.get("MYTHIQ_REVIEW_BASE", "http://127.0.0.1:8788")
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
    "minecraft","shorts","short","video","clip","normal","story","setup","twist",
    "payoff","moment","thing","stuff","until","think","going","full","there","theres",
    "there's","actually","talking","speak","speaking","look","looking","around","book",
    "everything","changes","change","server","lord","versus","who's","whos","qualify",
    "players","player","band","danger","take","walking","through","entrance","single",
    "webvtt","kind","sort","maybe","probably","literally","okay","ok"
}

EVENT_TERMS = {
    "trap","fight","clutch","lava","egg","base","death","fall","chase","duel","steal",
    "tnt","border","escape","hide","raid","jump","panic","scared","ambush","sneak",
    "betrayal","payback","revenge","spawn","secret","tower","bridge","diamond","nether",
    "portal","void","explosion","tunnel","labyrinth","king","axe","loot","gear","armor",
    "armored","crown","trapped","trapping","killed","died","fought","fighting","running",
    "ran","hidden","secretly","attacked","ambushed","netherite","cave","chest","stealing"
}

TITLE_PATTERNS = [
    "{creator} {event_phrase}.. 💀 | #shorts",
    "{creator} Was NOT Ready For {event_phrase} 💀 #shorts",
    "{event_phrase} Changed Everything 😳 | {series} #shorts",
    "They Got Scared From {event_phrase} ☠️🔥 | {series} #shorts",
    "The Guy That Died To {event_phrase} | {series} #shorts",
    "{creator} Almost Lost Because Of {event_phrase} 😭 #shorts",
    "This {event_phrase} Moment Was Insane 🔥 #shorts",
    "{creator} {event_phrase} Was Crazy 😳 #shorts",
    "{event_phrase} In {series} 💀 #shorts",
]

PREFERRED_EVENT_WORDS = {
    "fight","clutch","trap","base","tunnel","labyrinth","nether","armor","armored",
    "king","duel","lava","tnt","raid","portal","escape","death","chase","ambush",
    "loot","egg","border","tower","diamond","crown"
}

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

def abs_url(path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return BASE.rstrip("/") + path

def local_media_path(url_or_path: str) -> Path:
    s = url_or_path
    if s.startswith("http://") or s.startswith("https://"):
        s = re.sub(r"^https?://[^/]+", "", s)
    if s.startswith("/files/"):
        s = s[len("/files/"):]
    s = s.lstrip("/")
    return (Path.cwd() / s).resolve()

def strip_subs(text: str) -> str:
    out: list[str] = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.upper().startswith("WEBVTT"):
            continue
        if re.fullmatch(r"\d+", s):
            continue
        if "-->" in s:
            continue
        s = re.sub(r"<[^>]+>", " ", s)
        s = re.sub(r"{\\[^}]+}", " ", s)
        s = re.sub(r"\[[^\]]+\]", " ", s)
        s = re.sub(r"\([^)]+\)", " ", s)
        s = re.sub(r"[^A-Za-z0-9' ]+", " ", s)
        s = safe_text(s)
        if s:
            out.append(s)
    text = safe_text(" ".join(out))
    text = re.sub(r"\bWEBVTT\b", " ", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z0-9']+", text)

def pick_creator(text: str, idx: int) -> str:
    tl = text.lower()
    for c in CREATORS:
        if c.lower() in tl:
            return c
    return CREATORS[idx % len(CREATORS)] if CREATORS else "Minecraft"

def normalize_phrase(s: str) -> str:
    s = safe_text(s)
    s = re.sub(r"[^A-Za-z0-9' ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def extract_event_candidates(text: str) -> list[str]:
    words = tokens(text)

    clean: list[str] = []
    for w in words:
        wl = w.lower()
        if wl in STOP:
            continue
        if len(w) < 4:
            continue
        clean.append(w)

    banned_words = {
        "webvtt","talking","actually","looking","around","there","theres","there's",
        "changes","change","everything","normal","story","setup","twist","payoff",
        "qualify","players","player","danger","walking","through","entrance","single"
    }

    scored_phrases: list[tuple[int, str]] = []

    for n in (3, 2):
        for i in range(len(clean) - n + 1):
            phrase_words = clean[i:i+n]
            lw = [x.lower() for x in phrase_words]
            phrase = " ".join(phrase_words)
            pl = phrase.lower()

            if not (6 <= len(phrase) <= 32):
                continue
            if any(x in banned_words for x in lw):
                continue
            if not any(term in pl for term in EVENT_TERMS):
                continue

            score = 0
            score += sum(3 for term in EVENT_TERMS if term in pl)
            score += 2 if n == 2 else 3
            if any(x in PREFERRED_EVENT_WORDS for x in lw):
                score += 4

            scored_phrases.append((score, phrase))

    for w in clean:
        wl = w.lower()
        if wl in banned_words:
            continue
        if wl in EVENT_TERMS:
            scored_phrases.append((3, w))

    scored_phrases.sort(key=lambda x: (-x[0], -len(x[1])))

    out: list[str] = []
    seen: set[str] = set()
    for _, phrase in scored_phrases:
        phrase = normalize_phrase(phrase)
        key = phrase.lower()
        if not phrase or key in seen:
            continue
        if any(b in key.split() for b in banned_words):
            continue
        seen.add(key)
        out.append(phrase)

    good = [
        phrase for phrase in out
        if any(term in phrase.lower() for term in PREFERRED_EVENT_WORDS)
    ]
    return (good or out)[:8]

def sentence_split(text: str) -> list[str]:
    text = safe_text(text)
    if not text:
        return []
    parts = re.split(r'(?<=[.!?])\s+', text)
    return [safe_text(p) for p in parts if safe_text(p)]

def summarize_short(text: str, creator: str, event_phrase: str) -> tuple[str, str]:
    sents = sentence_split(text)
    if not sents:
        title_context = f"{creator} gets pulled into a {event_phrase.lower()} moment in {SERIES}."
        desc = (
            f"In this short, {creator} is at the center of a {event_phrase.lower()} moment in {SERIES}. "
            f"The clip focuses on the tension, reaction, and payoff of the scene in a fast vertical format."
        )
        return title_context, desc

    chosen: list[str] = []
    for s in sents:
        sl = s.lower()
        if creator.lower() in sl or event_phrase.lower() in sl or any(t in sl for t in PREFERRED_EVENT_WORDS):
            chosen.append(s)

    if not chosen:
        chosen = sents[:3]

    title_context = safe_text(" ".join(chosen[:2]))
    desc = safe_text(" ".join(chosen[:4]))

    if len(desc) < 120:
        desc = safe_text(
            f"{desc} This short centers on {creator} during a {event_phrase.lower()} sequence in {SERIES}, "
            f"highlighting the tension, reaction, and outcome of the moment."
        )

    return title_context, desc

def make_unique_title(creator: str, event_phrase: str, context: str, used: set[str]) -> str:
    variants: list[str] = []
    for tmpl in TITLE_PATTERNS:
        t = tmpl.format(creator=creator, event_phrase=event_phrase, series=SERIES)
        t = safe_text(t)
        if len(t) > 68:
            t = t[:68].rstrip() + "..."
        variants.append(t)

    def score(t: str) -> tuple:
        tl = t.lower()
        clean_bonus = 0
        if any(x in tl for x in PREFERRED_EVENT_WORDS):
            clean_bonus += 3
        if "webvtt" in tl or "talking" in tl or "actually" in tl:
            clean_bonus -= 5
        return (
            -int(38 <= len(t) <= 62),
            -int(creator.lower() in tl),
            -int(event_phrase.lower() in tl),
            -int("#shorts" in tl),
            -clean_bonus,
            abs(len(t) - 52),
        )

    variants = sorted(dict.fromkeys(variants), key=score)
    for v in variants:
        if v.lower() not in used:
            used.add(v.lower())
            return v

    fallback = f"{creator} {event_phrase} 💀 #shorts"
    if len(fallback) > 68:
        fallback = fallback[:68].rstrip() + "..."
    used.add(fallback.lower())
    return fallback

def ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ]).decode("utf-8", errors="ignore").strip()
    return float(out or "0")

def build_enhanced_edit(src: Path, dst: Path, subtitle_vtt: str | None = None) -> None:
    duration = ffprobe_duration(src)
    keep = min(duration, 17.5)

    vf = ",".join([
        f"trim=0:{keep}",
        "setpts=PTS/1.06",
        "scale=1080:1920:force_original_aspect_ratio=increase",
        "crop=1080:1920",
        "eq=contrast=1.07:saturation=1.12:brightness=0.01",
        "unsharp=5:5:0.9:3:3:0.5",
        "fps=30",
    ])

    af = f"atrim=0:{keep},atempo=1.06,loudnorm=I=-13:TP=-1.5:LRA=10,acompressor=threshold=-16dB:ratio=2.2:attack=20:release=250"

    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(src),
        "-vf", vf,
        "-af", af,
        "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "192k",
        str(dst),
    ], check=True)

def main() -> int:
    data = fetch_json(API_LATEST)
    if not data.get("ok"):
        print("latest payload not ok", file=sys.stderr)
        return 1

    job_id = data.get("job_id", "unknown_job")
    clips = data.get("clips") or []
    if not clips:
        print("no clips found", file=sys.stderr)
        return 1

    root = Path("artifacts") / job_id / "semantic_upgrade"
    meta = root / "meta"
    renders = root / "renders"
    meta.mkdir(parents=True, exist_ok=True)
    renders.mkdir(parents=True, exist_ok=True)

    used_titles: set[str] = set()
    ranking: list[dict[str, Any]] = []

    for i, clip in enumerate(clips, start=1):
        subtitle_text = ""
        subtitle_url = clip.get("subtitle_vtt_url") or clip.get("subtitle_url")
        if subtitle_url:
            subtitle_text = fetch_text(abs_url(subtitle_url))
            subtitle_text = strip_subs(subtitle_text)

        raw_blob = safe_text(" ".join([
            str(clip.get("title") or ""),
            str(clip.get("hook") or ""),
            str(clip.get("summary") or ""),
            str(clip.get("caption") or ""),
            str(clip.get("description") or ""),
            subtitle_text,
        ]))

        creator = pick_creator(raw_blob, i - 1)
        event_candidates = extract_event_candidates(raw_blob)
        event_phrase = event_candidates[0] if event_candidates else "Unstable SMP Fight"
        context, description = summarize_short(subtitle_text or raw_blob, creator, event_phrase)
        title = make_unique_title(creator, event_phrase, context, used_titles)

        source_video = clip.get("captioned_video_url") or clip.get("video_url")
        enhanced_video = None
        if source_video:
            src = local_media_path(source_video)
            if src.exists():
                dst = renders / f"short_{i:02d}_enhanced.mp4"
                build_enhanced_edit(src, dst, subtitle_url)
                enhanced_video = str(dst)

        desc_full = safe_text(
            f"{description}\n\n"
            f"Main focus: {event_phrase}.\n"
            f"Featured creator: {creator}.\n"
            f"Series: {SERIES}.\n\n"
            f"#shorts #minecraft #{creator.lower()} #gaming #unstablesmp"
        )

        (meta / f"short_{i:02d}.title.txt").write_text(title + "\n", encoding="utf-8")
        (meta / f"short_{i:02d}.description.txt").write_text(desc_full + "\n", encoding="utf-8")
        (meta / f"short_{i:02d}.event.txt").write_text(event_phrase + "\n", encoding="utf-8")
        (meta / f"short_{i:02d}.context.txt").write_text(context + "\n", encoding="utf-8")

        ranking.append({
            "index": i,
            "creator": creator,
            "event_phrase": event_phrase,
            "event_candidates": event_candidates[:5],
            "title": title,
            "description": desc_full,
            "enhanced_video": enhanced_video,
            "source_title": clip.get("title"),
        })

    (meta / "ranking.json").write_text(
        json.dumps(ranking, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )

    md = ["# Semantic Shorts Upgrade", ""]
    for r in ranking:
        md.append(f"## {r['index']:02d}. {r['title']}")
        md.append(f"- creator: {r['creator']}")
        md.append(f"- event: {r['event_phrase']}")
        md.append(f"- candidates: {', '.join(r['event_candidates'])}")
        md.append(f"- enhanced_video: `{r['enhanced_video']}`")
        md.append("")
        md.append(r["description"])
        md.append("")
    (meta / "ranking.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"SEMANTIC_UPGRADE_OK job_id={job_id} clips={len(ranking)} out={root}")
    for r in ranking:
        print(f"{r['index']:02d}. {r['title']}")
        print(f"    creator={r['creator']} | event={r['event_phrase']} | candidates={r['event_candidates'][:3]}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
