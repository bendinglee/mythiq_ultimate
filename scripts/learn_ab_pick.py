#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.request import Request, urlopen

@dataclass
class Vote:
    ts: int
    ab_group: str
    picked: str | None
    decided: bool | None
    inserted: bool | None

def fetch_csv(base: str, limit: int) -> list[dict[str, str]]:
    url = f"{base.rstrip('/')}/v1/generations/export?limit={int(limit)}"
    req = Request(url, headers={"accept": "text/csv"})
    with urlopen(req, timeout=10) as r:
        raw = r.read().decode("utf-8", errors="replace")
    rows = list(csv.DictReader(raw.splitlines()))
    return rows

def parse_meta(meta_json: str) -> dict:
    if not meta_json:
        return {}
    try:
        return json.loads(meta_json)
    except Exception:
        return {}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:7777")
    ap.add_argument("--limit", type=int, default=5000)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    rows = fetch_csv(args.base, args.limit)

    votes: list[Vote] = []
    for r in rows:
        if r.get("feature") != "ab_pick":
            continue
        ts = int(r.get("ts") or 0)
        ab_group = (r.get("prompt") or "").strip()
        picked = (r.get("output") or "").strip() or None
        meta = parse_meta(r.get("meta_json") or "")
        decided = meta.get("decided")
        inserted = meta.get("inserted")
        votes.append(Vote(ts=ts, ab_group=ab_group, picked=picked, decided=decided, inserted=inserted))

    by_group: dict[str, dict] = {}
    counts = defaultdict(lambda: {"n": 0, "picks": defaultdict(int), "decided_events": 0, "inserted_true": 0, "inserted_false": 0, "first_ts": None, "last_ts": None})

    for v in votes:
        c = counts[v.ab_group]
        c["n"] += 1
        if v.picked is not None:
            c["picks"][v.picked] += 1
        if v.decided is True:
            c["decided_events"] += 1
        if v.inserted is True:
            c["inserted_true"] += 1
        if v.inserted is False:
            c["inserted_false"] += 1
        c["first_ts"] = v.ts if c["first_ts"] is None else min(c["first_ts"], v.ts)
        c["last_ts"] = v.ts if c["last_ts"] is None else max(c["last_ts"], v.ts)

    def pick_rate(picks: dict, key: str) -> float:
        total = sum(picks.values())
        return (picks.get(key, 0) / total) if total else 0.0

    # summarize
    groups_out = []
    for g, c in counts.items():
        picks = dict(c["picks"])
        total_picks = sum(picks.values())
        top_pick = None
        top_n = 0
        for k, n in picks.items():
            if n > top_n:
                top_pick, top_n = k, n

        groups_out.append({
            "ab_group": g,
            "events": c["n"],
            "total_picks": total_picks,
            "top_pick": top_pick,
            "top_pick_rate": (top_n / total_picks) if total_picks else 0.0,
            "picks": picks,
            "decided_events": c["decided_events"],
            "inserted_true": c["inserted_true"],
            "inserted_false": c["inserted_false"],
            "first_ts": c["first_ts"],
            "last_ts": c["last_ts"],
        })

    groups_out.sort(key=lambda x: (-x["events"], x["ab_group"]))

    now = int(time.time())
    report = {
        "ts": now,
        "utc": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
        "source": {"base": args.base, "limit": args.limit},
        "ab_pick": {
            "events": len(votes),
            "groups": groups_out[:200],  # cap
        },
    }

    out = args.out.strip() or f"reports/ab_pick_report_{now}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(out)
    # quick human hint
    if groups_out:
        g0 = groups_out[0]
        print(f"top_group={g0['ab_group']} events={g0['events']} top_pick={g0['top_pick']} rate={g0['top_pick_rate']:.2f}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
