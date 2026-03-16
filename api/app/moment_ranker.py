from __future__ import annotations
import argparse, json, re
from pathlib import Path

STOP = {
    "the","a","an","and","or","but","is","are","was","were","to","of","for","in","on","at",
    "with","this","that","it","its","into","from","up","out","you","your","we","they","he",
    "she","them","his","her","i","me","my","our","ours","their","theirs"
}

HOOK_WORDS = {
    "secret","truth","crazy","insane","exposed","nobody","never","worst","best","why",
    "how","what","impossible","mistake","warning","changed","revealed","suddenly",
    "vanished","teleport","disappeared","hunters","alive","kidnapped","proof","trap",
    "shield","safe house","machine","cannon"
}

PAYOFF_WORDS = {
    "so","therefore","finally","because","result","then","after","won","lost","found",
    "proved","ended","realized","understood","discovered","alive","killed","escaped",
    "teleport","vanish","bounty","kidnapping","machine","justice","shield"
}

WEAK_LINES = {
    "what", "okay", "yeah", "nice", "go", "wait", "dude"
}

def read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))

def write_json(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2), encoding="utf-8")

def tokenize(s: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP]

def clean_text(s: str) -> str:
    return " ".join(str(s).replace("\n", " ").split()).strip()

def load_segments(job_root: Path) -> list[dict]:
    p = job_root / "transcript" / "transcript.json"
    data = read_json(p)
    segs = data.get("segments", [])
    out = []
    for row in segs:
        try:
            start = float(row["start"])
            end = float(row["end"])
            text = clean_text(row["text"])
        except Exception:
            continue
        if end <= start or not text:
            continue
        out.append({"start": start, "end": end, "text": text})
    return out

def angle_for_text(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ("alive","proof","revealed","found","discovered","realized","connection")):
        return "reveal"
    if any(w in t for w in ("teleport","vanish","disappear","impossible","immortal")):
        return "mystery"
    if any(w in t for w in ("mistake","wrong","failed","failure","problem","issue","trapped")):
        return "problem"
    if any(w in t for w in ("hunters","kidnap","kidnapping","bounty","safe house","shield")):
        return "threat"
    if any(w in t for w in ("machine","trap","cannon","kill","justice","survive","escape")):
        return "payoff"
    if "why" in t or "how" in t:
        return "curiosity"
    if any(w in t for w in ("best","worst","crazy","insane")):
        return "extreme"
    return "insight"

def build_windows(segs: list[dict], min_dur: float = 8.0, max_dur: float = 22.0) -> list[dict]:
    windows = []
    n = len(segs)
    for i in range(n):
        start = segs[i]["start"]
        text_parts = []
        end = start
        for j in range(i, n):
            end = segs[j]["end"]
            dur = end - start
            text_parts.append(segs[j]["text"])
            if dur > max_dur:
                break
            if dur >= min_dur:
                text = clean_text(" ".join(text_parts))
                windows.append({
                    "start": round(start, 2),
                    "end": round(end, 2),
                    "duration": round(dur, 2),
                    "text": text,
                })
    return windows

def score_window(win: dict, topic_hint: str) -> float:
    text = win["text"].lower()
    wc = len(win["text"].split())
    dur = float(win["duration"])
    score = 0.0

    toks = set(tokenize(topic_hint))
    for t in toks:
        if t and t in text:
            score += 1.2

    for w in HOOK_WORDS:
        if w in text:
            score += 1.4
    for w in PAYOFF_WORDS:
        if w in text:
            score += 1.2

    if 10.0 <= dur <= 20.0:
        score += 2.5
    elif 8.0 <= dur <= 24.0:
        score += 1.2

    if 25 <= wc <= 90:
        score += 2.5
    elif 15 <= wc <= 110:
        score += 1.2
    else:
        score -= 2.5

    weak_hits = sum(1 for x in re.findall(r"[A-Za-z0-9']+", text) if x in WEAK_LINES)
    if weak_hits >= 3:
        score -= 2.0

    strong_terms = (
        "skinless", "hunters", "teleport", "vanish", "disappear", "alive",
        "kidnap", "kidnapping", "bounty", "safe house", "shield", "maypick",
        "machine", "cannon", "trap", "justice", "immortal", "totem"
    )
    for term in strong_terms:
        if term in text:
            score += 1.6

    if "?" in win["text"] or "!" in win["text"]:
        score += 0.4

    return round(score, 2)

def make_hook(text: str) -> str:
    words = clean_text(text).split()
    if not words:
        return ""
    return " ".join(words[:18])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job_root")
    ap.add_argument("--topic", default="")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    root = Path(args.job_root)
    segs = load_segments(root)
    windows = build_windows(segs)

    rows = []
    for w in windows:
        txt = w["text"]
        if len(txt.split()) < 12:
            continue
        row = {
            "start": w["start"],
            "end": w["end"],
            "duration": w["duration"],
            "text": txt,
            "hook": make_hook(txt),
            "angle": angle_for_text(txt),
        }
        row["score"] = score_window(row, args.topic)
        rows.append(row)

    rows.sort(key=lambda x: x["score"], reverse=True)
    write_json(Path(args.out), rows[:120])
    print(args.out)

if __name__ == "__main__":
    main()
