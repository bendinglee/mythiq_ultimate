from __future__ import annotations
from pathlib import Path
import argparse, json, re

def quality_score(row: dict) -> dict:
    score = 0.0
    hook = row.get("hook","")
    text = row.get("text","")
    edit = row.get("edit", {})
    dur = float(row["end"]) - float(row["start"])

    if len(hook.split()) >= 4:
        score += 2.0
    if "?" in hook or any(x in hook.lower() for x in ["why","how","secret","truth","changed","revealed","mistake"]):
        score += 2.0
    if dur <= 6.0:
        score += 1.5
    if row.get("angle") in ("reveal","payoff","extreme","problem","curiosity"):
        score += 1.5
    if edit.get("motion_intensity") in ("medium","high"):
        score += 1.0
    if edit.get("highlight_keywords"):
        score += 1.0
    if len(re.findall(r"[A-Za-z0-9]", text)) >= 30:
        score += 1.0

    row["quality_score"] = round(score, 2)
    row["quality_pass"] = score >= 5.0
    return row

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("infile")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = json.loads(Path(args.infile).read_text())
    out = [quality_score(r) for r in rows]
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(args.out)

if __name__ == "__main__":
    main()
