from __future__ import annotations

import argparse, json, re, hashlib
from pathlib import Path

MIN_LEN = 22.0
MAX_LEN = 30.5
TARGET_DEFAULT = 4
LEDGER = Path("artifacts/shorts_meta/export_history.json")

def load_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))

def save_json(p, data):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

def norm(s):
    return re.sub(r"\s+", " ", str(s or "").strip()).lower()

def dur(r):
    return float(r.get("end", 0)) - float(r.get("start", 0))

def overlap(a0, a1, b0, b1):
    return max(0.0, min(a1, b1) - max(a0, b0))

def story_text(r):
    return " ".join([
        str(r.get("hook", "")),
        str(r.get("story_setup", "")),
        str(r.get("story_conflict", "")),
        str(r.get("story_payoff", "")),
        str(r.get("angle", "")),
    ])

def has_story_shape(r):
    setup = norm(r.get("story_setup", ""))
    conflict = norm(r.get("story_conflict", "")) or norm(r.get("hook", ""))
    payoff = norm(r.get("story_payoff", ""))
    return bool(conflict) and (bool(setup) or bool(payoff))

def title_from_story(r):
    t = norm(story_text(r))
    rules = [
        ("shield", "The Shield Proved They Knew Maypick"),
        ("maypick", "The Clue That Maypick Was Alive"),
        ("totem", "They Escaped Every Trap With Totems"),
        ("teleport", "They Teleported Before The Kill"),
        ("safe house", "The Safe House Was Not Safe"),
        ("bounty", "The Bounty Was A Kidnapping Setup"),
        ("kidnap", "They Were Not Killing Players"),
        ("machine", "There Was Only One Way To Kill Them"),
        ("trap", "The Trap Should Have Worked"),
        ("proof", "This Was The Proof They Were Immortal"),
        ("sir pig", "Sir Pig Knew More Than He Said"),
        ("sirpig", "Sir Pig Knew More Than He Said"),
    ]
    for needle, title in rules:
        if needle in t:
            return title
    angle = norm(r.get("angle", ""))
    if angle == "reveal":
        return "The Reveal Changed Everything"
    if angle == "mystery":
        return "Nothing About This Made Sense"
    if angle == "threat":
        return "This Was Bigger Than A Raid"
    if angle == "payoff":
        return "This Was The Moment It Paid Off"
    return "The Moment The Story Turned"

def score_row(r):
    q = float(r.get("quality_score", 0))
    e = float(r.get("export_score", 0) or 0)
    d = dur(r)

    setup = norm(r.get("story_setup", ""))
    conflict = norm(r.get("story_conflict", "")) or norm(r.get("hook", ""))
    payoff = norm(r.get("story_payoff", ""))
    txt = norm(story_text(r))

    score = 0.0
    score += q * 1.7
    score += e * 0.7

    if setup:
        score += 2.5
    if conflict:
        score += 4.0
    if payoff:
        score += 4.5
    if has_story_shape(r):
        score += 3.0

    if MIN_LEN <= d <= MAX_LEN:
        score += 4.0
    elif 18.0 <= d <= 34.0:
        score += 1.5
    else:
        score -= 3.0

    story_words = [
        "because","however","proof","found","alive","dead","bounty","shield",
        "totem","teleport","trap","machine","safe house","kidnap","escape",
        "hunter","hunters","maypick","jumper","spies","sir pig"
    ]
    score += sum(0.35 for w in story_words if w in txt)

    bad = [
        "if you guys enjoyed this video",
        "subscribe",
        "watch this video",
        "youtube thinks",
        "goodbye",
    ]
    if any(b in txt for b in bad):
        score -= 8.0

    if "inventory" in txt and not payoff and not setup:
        score -= 1.5

    return round(score, 3)

def video_key(rows):
    seed = "||".join(
        f'{round(float(r.get("start",0)),2)}:{round(float(r.get("end",0)),2)}:{norm(r.get("hook",""))}'
        for r in rows[:150]
    )
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()

def load_ledger():
    if LEDGER.exists():
        try:
            return json.loads(LEDGER.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_ledger(data):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(data, indent=2), encoding="utf-8")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("quality_json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--target-count", type=int, default=TARGET_DEFAULT)
    ap.add_argument("--count", type=int, default=None)
    args = ap.parse_args()

    target = args.count if args.count is not None else args.target_count
    rows = load_json(args.quality_json)

    cooked = []
    for r in rows:
        rr = dict(r)
        rr["title"] = title_from_story(rr)
        rr["story_score"] = score_row(rr)
        cooked.append(rr)

    cooked.sort(key=lambda x: float(x.get("story_score", 0)), reverse=True)

    picked = []
    for r in cooked:
        if len(picked) >= target:
            break
        a0, a1 = float(r.get("start", 0)), float(r.get("end", 0))
        ok = True
        for p in picked:
            b0, b1 = float(p.get("start", 0)), float(p.get("end", 0))
            if overlap(a0, a1, b0, b1) >= 5.0:
                ok = False
                break
            if norm(r.get("title")) == norm(p.get("title")):
                ok = False
                break
        if ok:
            picked.append(r)

    ledger = load_ledger()
    k = video_key(rows)
    old = ledger.get(k, [])
    final = []
    for r in picked:
        a0, a1 = float(r.get("start", 0)), float(r.get("end", 0))
        if any(overlap(a0, a1, float(o["start"]), float(o["end"])) >= 5.0 for o in old):
            continue
        final.append(r)
    if len(final) < target:
        for r in picked:
            if r not in final:
                final.append(r)
            if len(final) >= target:
                break

    final = final[:target]
    ledger.setdefault(k, [])
    for r in final:
        ledger[k].append({"start": r.get("start"), "end": r.get("end"), "title": r.get("title")})
    save_ledger(ledger)

    save_json(args.out, final)
    print(args.out)

if __name__ == "__main__":
    main()
