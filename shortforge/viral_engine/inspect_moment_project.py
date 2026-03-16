from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()

    base = ROOT / "shortforge" / "projects" / args.run_id
    if not base.exists():
        raise SystemExit(f"❌ missing project: {base}")

    print("PROJECT:", base)

    for sub in ["clips", "moment_renders", "top_ranked", "scene_renders", "final_selects", "reports"]:
        p = base / sub
        if not p.exists():
            print(f"{sub}: MISSING")
            continue

        files = sorted(x for x in p.iterdir() if x.is_file())
        print(f"{sub}: {len(files)} files")
        for f in files[:20]:
            print(" -", f.name, "|", f.stat().st_size)

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
