from __future__ import annotations
import argparse, json, re
from pathlib import Path

GOOD_TERMS = {
    "teleport","totem","hunters","shield","maypick","alive","kidnap","kidnapping",
    "bounty","safe house","machine","cannon","trap","proof","disappeared","vanish",
    "immortal","taunting","connected"
}

BAD_FRAGMENT_PATTERNS = [
    r"^\W*$",
    r"^(what|okay|yeah|nice|go|wait|bro|dude)\W*$",
]

def read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))

def write_json(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2), encoding="utf-8")

def clean(s: str) -> str:
    return " ".join(str(s).split()).strip()

def score_row(row: dict) -> dict:
    text = clean(row.get("text", ""))
    hook = clean(row.get("hook", ""))
    angle = row.get("angle", "insight")
    duration = float(row.get("duration", max(0.0, float(row.get("end", 0)) - float(row.get("start", 0)))))

    score = 0.0
    pass_ok = True
    reasons = []

    wc = len(text.split())

    if wc >= 20:
        score += 2.5
    elif wc >= 14:
        score += 1.5
    else:
        score -= 3.0
        reasons.append("too_short")

    if 10 <= duration <= 22:
        score += 2.5
    elif 8 <= duration <= 26:
        score += 1.5
    else:
        score -= 1.5
        reasons.append("duration_off")

    lower = text.lower()

    term_hits = sum(1 for t in GOOD_TERMS if t in lower)
    score += min(4.0, term_hits * 0.8)

    if angle in {"reveal","mystery","threat","payoff"}:
        score += 1.5

    if "?" in text or "!" in text:
        score += 0.5

    if hook and len(hook.split()) >= 8:
        score += 0.8

    for pat in BAD_FRAGMENT_PATTERNS:
        if re.match(pat, lower):
            score -= 4.0
            pass_ok = False
            reasons.append("bad_fragment")

    # only hard-fail if clearly junk
    if wc < 10 and term_hits < 2:
        pass_ok = False
        reasons.append("insufficient_substance")

    # narrative override for strong windows
    if term_hits >= 3 and angle in {"reveal","mystery","threat","payoff"} and wc >= 16:
        pass_ok = True
        if score < 8.0:
            score = 8.0
        reasons.append("narrative_override")

    row["quality_score"] = round(score, 2)
    row["quality_pass"] = bool(pass_ok)
    row["quality_reasons"] = reasons
    return row

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edit_plan_json")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = read_json(Path(args.edit_plan_json))
    out = [score_row(dict(r)) for r in rows]
    write_json(Path(args.out), out)
    print(args.out)

if __name__ == "__main__":
    main()
