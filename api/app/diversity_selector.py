from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
import argparse, json, re
from collections import Counter

def norm_words(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", s.lower()))

def jaccard(a: str, b: str) -> float:
    aa, bb = norm_words(a), norm_words(b)
    if not aa or not bb:
        return 0.0
    return len(aa & bb) / max(1, len(aa | bb))

def time_overlap(a, b) -> float:
    inter = max(0.0, min(a["end"], b["end"]) - max(a["start"], b["start"]))
    union = max(a["end"], b["end"]) - min(a["start"], b["start"])
    return inter / max(union, 1e-6)

def too_similar(c, selected) -> bool:
    for s in selected:
        if time_overlap(c, s) > 0.35:
            return True
        if jaccard(c["text"], s["text"]) > 0.35:
            return True
        if jaccard(c.get("hook",""), s.get("hook","")) > 0.55:
            return True
    return False

def select(candidates: list[dict], target_count: int = 10) -> list[dict]:
    selected = []
    angle_counts = Counter()
    region_counts = Counter()

    for c in sorted(candidates, key=lambda x: x.get("score", 0.0), reverse=True):
        angle = c.get("angle", "insight")
        region = c.get("region", "mid")

        if too_similar(c, selected):
            continue
        if angle_counts[angle] >= 2:
            continue
        if region_counts[region] >= max(3, target_count // 3 + 1):
            continue

        selected.append(c)
        angle_counts[angle] += 1
        region_counts[region] += 1
        if len(selected) >= target_count:
            break
    return selected

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("infile")
    ap.add_argument("--out", required=True)
    ap.add_argument("--target-count", type=int, default=10)
    args = ap.parse_args()

    candidates = json.loads(Path(args.infile).read_text())
    chosen = select(candidates, args.target_count)
    Path(args.out).write_text(json.dumps(chosen, indent=2), encoding="utf-8")
    print(args.out)

if __name__ == "__main__":
    main()
