#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, io, json, sys
from collections import defaultdict
from datetime import datetime, timezone
import time
import urllib.request

def fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=5) as r:
        return r.read().decode("utf-8", errors="replace")

def parse_csv(text: str) -> list[dict]:
    f = io.StringIO(text)
    return list(csv.DictReader(f))

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:7777")
    ap.add_argument("--gen_limit", type=int, default=5000)
    ap.add_argument("--out_limit", type=int, default=5000)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    gen = parse_csv(fetch(f"{args.base}/v1/generations/export?limit={args.gen_limit}"))
    out = parse_csv(fetch(f"{args.base}/v1/outcomes/export?limit={args.out_limit}"))

    # outcomes keyed by "feature:key"
    rewards = defaultdict(list)  # (feature,key) -> [reward]
    for r in out:
        try:
            rewards[(r["feature"], r["key"])].append(float(r["reward"]))
        except Exception:
            pass

    # For ab_pick, expect outcome key like "<ab_group>:<picked>" (your current example uses "decide_check:A")
    groups = defaultdict(lambda: {"events": 0, "by_pick": defaultdict(lambda: {"n": 0, "reward_sum": 0.0})})

    for r in gen:
        if r.get("feature") != "ab_pick":
            continue
        ab_group = r.get("prompt") or ""
        picked = r.get("output") or ""
        key = f"{ab_group}:{picked}"
        g = groups[ab_group]
        g["events"] += 1
        rs = rewards.get(("ab_pick", key), [])
        if rs:
            g["by_pick"][picked]["n"] += len(rs)
            g["by_pick"][picked]["reward_sum"] += sum(rs)

    groups_out = []
    for ab_group, g in groups.items():
        by_pick = []
        for pick, d in g["by_pick"].items():
            n = d["n"]
            avg = (d["reward_sum"] / n) if n else None
            by_pick.append({"pick": pick, "n": n, "avg_reward": avg})
        by_pick.sort(key=lambda x: (-(x["avg_reward"] or -1e9), -x["n"], x["pick"]))
        best = by_pick[0] if by_pick else None
        groups_out.append({
            "ab_group": ab_group,
            "events": g["events"],
            "best_by_reward": best,
            "by_pick": by_pick[:10],
        })

    groups_out.sort(key=lambda x: (-x["events"], x["ab_group"]))

    now = int(time.time())
    report = {
        "ts": now,
        "utc": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
        "source": {"base": args.base, "gen_limit": args.gen_limit, "out_limit": args.out_limit},
        "ab_pick_rewards": {"groups": groups_out[:200]},
    }

    out_path = args.out.strip() or f"reports/reward_report_{now}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(out_path)
    if groups_out and groups_out[0]["best_by_reward"]:
        g0 = groups_out[0]
        b = g0["best_by_reward"]
        print(f"top_group={g0['ab_group']} events={g0['events']} best={b['pick']} avg_reward={b['avg_reward']} n={b['n']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
