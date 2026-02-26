#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, glob

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default="")
    ap.add_argument("--out", default="reports/ab_pick_recommendations.json")
    args = ap.parse_args()

    path = args.report.strip()
    if not path:
        cand = sorted(glob.glob("reports/reward_report_*.json"))
        if not cand:
            raise SystemExit("❌ no reports/reward_report_*.json found; run learn_rewards.py first")
        path = cand[-1]

    rep = json.load(open(path, "r", encoding="utf-8"))
    groups = (rep.get("ab_pick_rewards") or {}).get("groups") or []
    rec = {}
    for g in groups:
        ab = g.get("ab_group")
        best = g.get("best_by_reward") or {}
        pick = best.get("pick")
        if ab and pick:
            rec[ab] = {"pick": pick, "avg_reward": best.get("avg_reward"), "n": best.get("n")}

    json.dump({"source_report": path, "recommendations": rec}, open(args.out, "w", encoding="utf-8"), indent=2)
    print(args.out)
    print(f"groups={len(rec)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
