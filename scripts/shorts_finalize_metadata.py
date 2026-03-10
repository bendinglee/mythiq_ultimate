#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

SERIES = "Unstable SMP"

CREATORS = ["Unstable", "Parrot", "Flame", "Wemmbu", "Spoke"]


def _clean_meta_text(x: str) -> str:
    x = (x or "").replace("\n", " ").replace("\r", " ")
    x = re.sub(r"\s+", " ", x).strip()
    x = re.sub(r"(?i)\bwebvtt\b", "", x)
    x = re.sub(r"(?i)\bkind:\s*captions\b", "", x)
    x = re.sub(r"(?i)\blanguage:\s*en\b", "", x)
    x = re.sub(r"(?i)\bNOTE\b", "", x)
    x = re.sub(r"\s+", " ", x).strip(" -:.")
    return x

def _clean_phrase(x: str) -> str:
    x = _clean_meta_text(x)
    x = re.sub(r"[^A-Za-z0-9' -]+", " ", x)
    x = re.sub(r"\s+", " ", x).strip()
    return x

def normalize_topic_strict(creator: str, raw_event: str, description_seed: str, old_topic: str) -> str:
    raw = _clean_phrase(raw_event).lower()
    desc = _clean_phrase(description_seed).lower()
    old = _clean_phrase(old_topic).lower()

    raw_blob = raw
    desc_blob = desc
    old_blob = old

    # preserve already-good old topics first
    if "armored" in old_blob or "durability" in old_blob:
        return "Armored Fight"
    if "king mace" in old_blob:
        return "King Mace"
    if "legendary king" in old_blob:
        return "Legendary King Fight"
    if "final king" in old_blob:
        return "Final King Fight"
    if "labyrinth" in old_blob:
        return "Labyrinth Base"
    if "nether" in old_blob:
        return "Nether Escape"
    if "arachnid" in old_blob:
        return "Arachnid Fight"
    if "smp fight" in old_blob:
        return "SMP Fight"

    # raw event dominates noisy description
    if any(x in raw_blob for x in ["armored durability", "armored fight", "durability fight", "armored"]):
        return "Armored Fight"
    if any(x in raw_blob for x in ["king mace", "mace curse"]):
        return "King Mace"
    if "legendary king" in raw_blob:
        return "Legendary King Fight"
    if "final king" in raw_blob:
        return "Final King Fight"
    if "labyrinth" in raw_blob:
        return "Labyrinth Base"
    if "nether" in raw_blob:
        return "Nether Escape"
    if "arachnid" in raw_blob:
        return "Arachnid Fight"
    if "smp fight" in raw_blob:
        return "SMP Fight"

    # very strict description fallbacks only
    if "true king of the unstable" in desc_blob or "arachnid" in desc_blob:
        return "Arachnid Fight"
    if "labyrinth" in desc_blob:
        return "Labyrinth Base"
    if "full nether" in desc_blob:
        return "Nether Escape"
    if "curse of power" in desc_blob:
        return "King Mace"
    if "legendary king" in desc_blob:
        return "Legendary King Fight"
    if "two more to fight" in desc_blob:
        return "Final King Fight"
    if "durability" in desc_blob and "armored" in desc_blob:
        return "Armored Fight"

    if old_blob:
        return " ".join(w.capitalize() for w in old_blob.split())

    return "SMP Fight"
def build_title_variants(creator: str, topic: str) -> list[str]:
    return [
        f"{creator} Was NOT Ready For {topic} 💀 #shorts",
        f"{creator} Almost Lost Because Of {topic} 😭 #shorts",
        f"{topic} Changed Everything For {creator} 🔥 #shorts",
        f"{creator} Had No Answer For {topic} 😳 #shorts",
    ]

def choose_best_title(creator: str, topic: str) -> str:
    return build_title_variants(creator, topic)[0]

def build_clean_description(title: str, creator: str, topic: str, raw_event: str, description_seed: str) -> str:
    src = _clean_meta_text(description_seed or raw_event)

    if src:
        src = re.sub(r"\bClip\s*\d+\b", "", src, flags=re.I)
        src = re.sub(r"\bThis short centers on\b.*", "", src, flags=re.I)
        src = re.sub(r"\bFeatured creator:\b.*", "", src, flags=re.I)
        src = re.sub(r"\bMain focus:\b.*", "", src, flags=re.I)
        src = re.sub(r"\bSeries:\b.*", "", src, flags=re.I)
        src = re.sub(r"#shorts.*", "", src, flags=re.I)
        src = re.sub(r"\s+", " ", src).strip(" -:.")
    if not src:
        src = f"{creator} gets pulled into a {topic.lower()} moment on Unstable SMP"

    if len(src) > 220:
        src = src[:217].rstrip() + "..."

    return (
        f"{src}. "
        f"Fast-paced vertical edit with a clear hook, escalation, and payoff.\n\n"
        f"Featured creator: {creator}\n"
        f"Main focus: {topic}\n"
        f"Series: Unstable SMP\n\n"
        f"#shorts #minecraft #{creator.lower()} #gaming #unstablesmp"
    )

NOISE = {
    "tension","strong","found","right","true","well","supposedly","dude","upset",
    "little","greedy","direct","order","cannot","refuse","opportunity","known",
    "mental","battle","went","like","base","it's","its","youre","you're","waste",
    "more","didn't","didnt","there","book","curse"
}

def safe_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def newest_ranking() -> Path:
    files = list(Path("artifacts").glob("shorts_*/semantic_upgrade/meta/ranking.json"))
    if not files:
        raise SystemExit("no semantic ranking.json found")
    return max(files, key=lambda p: p.stat().st_mtime)

def words(s: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z0-9']*", s)

def canonical_topic(event_phrase: str, candidates: list[str], creator: str) -> str:
    blob = " ".join([event_phrase] + (candidates or []))
    wl = [w.lower() for w in words(blob)]

    def has(*terms: str) -> bool:
        return all(t in wl for t in terms)

    def any_has(*terms: str) -> bool:
        return any(t in wl for t in terms)

    if has("labyrinth", "tunnel") or has("labyrinth", "base") or has("tunnel", "base"):
        return "Labyrinth Base"
    if any_has("nether", "portal"):
        return "Nether Escape"
    if has("king", "mace") or any_has("mace"):
        return "King Mace"
    if has("legendary", "king"):
        return "Legendary King Fight"
    if has("final", "king"):
        return "Final King Fight"
    if has("armored", "durability") or has("armor", "fight") or has("armored", "fight"):
        return "Armored Fight"
    if has("king", "arachnid") or has("arachnid",):
        return "Arachnid Fight"
    if has("fight", "king"):
        return "King Fight"
    if any_has("fight", "duel", "battle", "fighting"):
        return "SMP Fight"
    if any_has("base", "raid", "loot", "chest"):
        return "Base Raid"
    if any_has("trap", "trapped", "ambush", "ambushed"):
        return "Trap Moment"
    if any_has("lava", "void", "death", "died", "fall"):
        return "Near Death Moment"

    clean = []
    for w in words(event_phrase):
        lw = w.lower()
        if lw in NOISE:
            continue
        if lw == creator.lower():
            continue
        clean.append(w)

    topic = safe_text(" ".join(clean[:3]))
    return topic if topic else "SMP Moment"

def title_variants(creator: str, topic: str) -> list[str]:
    variants = [
        f"{creator} {topic}.. 💀 | #shorts",
        f"{creator} Was NOT Ready For {topic} 💀 #shorts",
        f"{topic} Changed Everything 😳 | {SERIES} #shorts",
        f"They Got Scared☠️🔥 | {SERIES} #shorts",
        f"The Guy That Died To {topic} | {SERIES} #shorts",
        f"{creator} Almost Lost Because Of {topic} 😭 #shorts",
        f"This {topic} Moment Was Insane 🔥 #shorts",
    ]
    out = []
    seen = set()
    for v in variants:
        v = safe_text(v)
        if len(v) > 68:
            v = v[:68].rstrip() + "..."
        key = v.lower()
        if key not in seen:
            seen.add(key)
            out.append(v)
    return out

def best_title(creator: str, topic: str) -> str:
    # simpler, cleaner house style first
    preferred = [
        f"{creator} Was NOT Ready For {topic} 💀 #shorts",
        f"{creator} {topic}.. 💀 | #shorts",
        f"{creator} Almost Lost Because Of {topic} 😭 #shorts",
        f"This {topic} Moment Was Insane 🔥 #shorts",
    ]
    for t in preferred:
        if len(t) <= 68:
            return t
    return preferred[0][:68].rstrip() + "..."

def final_description(creator: str, topic: str, raw_desc: str) -> str:
    raw_desc = safe_text(raw_desc)
    if len(raw_desc) > 240:
        raw_desc = raw_desc[:240].rstrip() + "..."
    return (
        f"In this short, {creator} is at the center of a {topic.lower()} moment in {SERIES}. "
        f"{raw_desc} "
        f"This clip is cut for fast pacing, vertical retention, and a strong payoff.\n\n"
        f"Featured creator: {creator}\n"
        f"Main focus: {topic}\n"
        f"Series: {SERIES}\n\n"
        f"#shorts #minecraft #{creator.lower()} #gaming #unstablesmp"
    )

def hook_pass(src: Path, dst: Path) -> None:
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(src),
        "-vf",
        "trim=0.35:15.85,setpts=PTS/1.08,scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,eq=contrast=1.10:saturation=1.15:brightness=0.015,"
        "unsharp=5:5:1.0:3:3:0.6,fps=30",
        "-af",
        "atrim=0.35:15.85,atempo=1.08,loudnorm=I=-13:TP=-1.5:LRA=9,"
        "acompressor=threshold=-16dB:ratio=2.4:attack=15:release=220",
        "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "19",
        "-c:a", "aac",
        "-b:a", "192k",
        str(dst),
    ], check=True)

def main() -> int:
    p = newest_ranking()
    data = json.loads(p.read_text(encoding="utf-8"))

    root = p.parent.parent / "finalized"
    meta = root / "meta"
    renders = root / "renders"
    meta.mkdir(parents=True, exist_ok=True)
    renders.mkdir(parents=True, exist_ok=True)

    final_rows = []

    for row in data:
        idx = int(row["index"])
        creator = row.get("creator", CREATORS[(idx - 1) % len(CREATORS)])
        raw_event = row.get("event_phrase", "")
        raw_desc = row.get("description", "")
        enhanced_video = row.get("enhanced_video")

        old_topic = row.get("topic", "")
        topic = normalize_topic_strict(creator, raw_event, raw_desc, old_topic)
        title = choose_best_title(creator, topic)
        variants = build_title_variants(creator, topic)
        desc = build_clean_description(title, creator, topic, raw_event, raw_desc)

        hook_video = None
        if enhanced_video:
            src = Path(enhanced_video)
            if src.exists():
                dst = renders / f"short_{idx:02d}_hook.mp4"
                hook_pass(src, dst)
                hook_video = str(dst)

        (meta / f"short_{idx:02d}.title.txt").write_text(title + "\n", encoding="utf-8")
        (meta / f"short_{idx:02d}.description.txt").write_text(desc + "\n", encoding="utf-8")
        (meta / f"short_{idx:02d}.variants.json").write_text(
            json.dumps(variants, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8"
        )
        (meta / f"short_{idx:02d}.topic.txt").write_text(topic + "\n", encoding="utf-8")

        final_rows.append({
            "index": idx,
            "creator": creator,
            "raw_event": raw_event,
            "topic": topic,
            "title": title,
            "title_variants": variants,
            "description": desc,
            "enhanced_video": enhanced_video,
            "hook_video": hook_video,
        })

    (meta / "final_metadata.json").write_text(
        json.dumps(final_rows, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )

    md = ["# Finalized Shorts Metadata", ""]
    for r in final_rows:
        md.append(f"## {r['index']:02d}. {r['title']}")
        md.append(f"- creator: {r['creator']}")
        md.append(f"- topic: {r['topic']}")
        md.append(f"- raw_event: {r['raw_event']}")
        md.append(f"- enhanced_video: `{r['enhanced_video']}`")
        md.append(f"- hook_video: `{r['hook_video']}`")
        md.append("- variants:")
        for v in r["title_variants"]:
            md.append(f"  - {v}")
        md.append("")
        md.append(r["description"])
        md.append("")
    (meta / "final_metadata.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"FINALIZE_OK source={p} out={root}")
    for r in final_rows:
        print(f"{r['index']:02d}. {r['title']}")
        print(f"    topic={r['topic']} | creator={r['creator']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
