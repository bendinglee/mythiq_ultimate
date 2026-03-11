from __future__ import annotations
from pathlib import Path
import argparse, json

def decision_for(row: dict) -> dict:
    angle = row.get("angle", "insight")
    score = float(row.get("score", 0.0))
    dur = max(0.1, float(row["end"]) - float(row["start"]))

    if angle in ("extreme", "reveal", "payoff"):
        transition = "hard_cut"
        zoom = "punch_in"
        motion = "high"
    elif angle in ("problem", "curiosity"):
        transition = "whip"
        zoom = "drift"
        motion = "medium"
    else:
        transition = "hard_cut"
        zoom = "static_push"
        motion = "medium"

    if dur <= 2.0:
        cut_every = 1.0
    elif dur <= 4.0:
        cut_every = 1.5
    else:
        cut_every = 2.0

    return {
        **row,
        "edit": {
            "transition": transition,
            "zoom": zoom,
            "motion_intensity": motion,
            "caption_style": "subtitle_first",
            "highlight_keywords": True,
            "cut_every_s": cut_every,
            "hook_text": row.get("hook",""),
            "payoff_text": row.get("payoff",""),
            "broll_needed": angle in ("curiosity","insight","problem"),
            "overlay_style": "bold_keyword"
        }
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("infile")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = json.loads(Path(args.infile).read_text())
    out = [decision_for(r) for r in rows]
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(args.out)

if __name__ == "__main__":
    main()
