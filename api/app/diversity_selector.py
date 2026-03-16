from __future__ import annotations
import argparse, json, re
from pathlib import Path

def read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))

def write_json(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2), encoding="utf-8")

def norm_tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", s.lower()))

def overlap(a: dict, b: dict) -> float:
    sa, ea = float(a["start"]), float(a["end"])
    sb, eb = float(b["start"]), float(b["end"])
    inter = max(0.0, min(ea, eb) - max(sa, sb))
    union = max(ea, eb) - min(sa, sb)
    return 0.0 if union <= 0 else inter / union

def token_jaccard(a: str, b: str) -> float:
    ta, tb = norm_tokens(a), norm_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(1, len(ta | tb))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("candidates_json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--target-count", type=int, default=10)
    args = ap.parse_args()

    rows = read_json(Path(args.candidates_json))
    picked = []
    angle_counts = {}

    for row in rows:
        angle = row.get("angle", "insight")
        row_text = row.get("text", "")

        ok = True
        for prev in picked:
            ov = overlap(row, prev)
            jac = token_jaccard(row_text, prev.get("text", ""))

            if ov > 0.55:
                ok = False
                break
            if jac > 0.72:
                ok = False
                break

        if not ok:
            continue

        # soft diversity instead of hard blocking
        current = angle_counts.get(angle, 0)
        if current >= 3:
            continue

        picked.append(row)
        angle_counts[angle] = current + 1

        if len(picked) >= args.target_count:
            break

    write_json(Path(args.out), picked)
    print(args.out)

if __name__ == "__main__":
    main()
