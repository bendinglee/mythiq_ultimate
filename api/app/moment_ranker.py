from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Iterable
import json, math, re
from pathlib import Path

STOP = {
    "the","a","an","and","or","but","is","are","was","were","to","of","for","in","on","at",
    "with","this","that","it","its","into","from","up","out","you","your","we","they","he",
    "she","them","his","her","i","me","my","our","ours","their","theirs"
}
HOOK_WORDS = {
    "secret","truth","crazy","insane","exposed","nobody","never","worst","best","why",
    "how","what","impossible","mistake","warning","changed","revealed","suddenly"
}
PAYOFF_WORDS = {
    "so","therefore","finally","because","result","then","after","won","lost","found",
    "proved","ended","realized","understood","discovered"
}

@dataclass
class Segment:
    start: float
    end: float
    text: str

@dataclass
class Candidate:
    start: float
    end: float
    text: str
    score: float
    angle: str
    hook: str
    payoff: str
    region: str

def _clean_text(x: Any) -> str:
    return " ".join(str(x).replace("\n", " ").split()).strip()

def _to_float(x: Any):
    try:
        return float(x)
    except Exception:
        return None

def _to_segment(row: Any):
    if not isinstance(row, dict):
        return None
    start = _to_float(row.get("start"))
    end = _to_float(row.get("end"))
    text = _clean_text(row.get("text", ""))
    if start is None or end is None or end <= start or not text:
        return None
    return Segment(start=start, end=end, text=text)

def discover_segments(root: Path) -> list[Segment]:
    candidates = []
    tjson = root / "transcript" / "transcript.json"
    if tjson.exists():
        candidates.append(tjson)
    for p in sorted(root.rglob("*.json")):
        if p not in candidates:
            candidates.append(p)

    segs: list[Segment] = []
    for p in candidates:
        try:
            obj = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue

        if isinstance(obj, list):
            for row in obj:
                seg = _to_segment(row)
                if seg:
                    segs.append(seg)
            continue

        if isinstance(obj, dict):
            for key in ("segments", "items", "captions", "subtitles", "words", "results"):
                val = obj.get(key)
                if isinstance(val, list):
                    for row in val:
                        seg = _to_segment(row)
                        if seg:
                            segs.append(seg)

    out: list[Segment] = []
    seen = set()
    for seg in sorted(segs, key=lambda x: (x.start, x.end, x.text)):
        key = (round(seg.start, 2), round(seg.end, 2), seg.text[:120])
        if key in seen:
            continue
        seen.add(key)
        out.append(seg)
    return out

def tokenize(s: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP]

def angle_for_text(text: str) -> str:
    t = text.lower()
    if "why" in t or "how" in t:
        return "curiosity"
    if any(w in t for w in ("mistake","wrong","failed","failure","problem","issue")):
        return "problem"
    if any(w in t for w in ("finally","revealed","found","discovered","realized")):
        return "reveal"
    if any(w in t for w in ("best","worst","crazy","insane","impossible")):
        return "extreme"
    if any(w in t for w in ("won","lost","result","proved","ended")):
        return "payoff"
    return "insight"

def hook_for_text(text: str) -> str:
    clean = _clean_text(text)
    if not clean:
        return ""
    parts = re.split(r'(?<=[.!?])\s+', clean)
    return parts[0][:140]

def payoff_for_text(text: str) -> str:
    clean = _clean_text(text)
    if not clean:
        return ""
    parts = re.split(r'(?<=[.!?])\s+', clean)
    return parts[-1][:140]

def score_segment(seg: Segment, topic_hint: str, total_dur: float) -> float:
    text = seg.text.lower()
    toks = set(tokenize(topic_hint))
    score = 0.0

    for t in toks:
        if t and t in text:
            score += 2.5

    for w in HOOK_WORDS:
        if w in text:
            score += 1.25
    for w in PAYOFF_WORDS:
        if w in text:
            score += 1.0

    dur = max(0.2, seg.end - seg.start)
    if 1.0 <= dur <= 4.2:
        score += 1.5
    elif dur <= 6.0:
        score += 0.5

    pos = seg.start / max(total_dur, 1.0)
    if pos <= 0.20:
        score += 0.8
    elif pos <= 0.55:
        score += 0.5

    if "!" in seg.text or "?" in seg.text:
        score += 0.5

    if len(seg.text.split()) >= 6:
        score += 0.5

    return score

def build_candidates(root: Path, topic_hint: str = "") -> list[Candidate]:
    segs = discover_segments(root)
    if not segs:
        return []
    total_dur = max(s.end for s in segs)
    out = []
    for seg in segs:
        pos = seg.start / max(total_dur, 1.0)
        region = "early" if pos < 0.33 else ("mid" if pos < 0.66 else "late")
        out.append(Candidate(
            start=seg.start,
            end=seg.end,
            text=_clean_text(seg.text),
            score=score_segment(seg, topic_hint, total_dur),
            angle=angle_for_text(seg.text),
            hook=hook_for_text(seg.text),
            payoff=payoff_for_text(seg.text),
            region=region,
        ))
    return sorted(out, key=lambda x: x.score, reverse=True)

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--topic", default="")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    rows = [asdict(x) for x in build_candidates(Path(args.root), args.topic)]
    if args.out:
        Path(args.out).write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print(args.out)
    else:
        print(json.dumps(rows[:20], indent=2))

if __name__ == "__main__":
    main()
