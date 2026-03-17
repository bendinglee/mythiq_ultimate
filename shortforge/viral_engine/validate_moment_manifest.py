from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()

    base = ROOT / "shortforge" / "projects" / args.run_id
    manifest_path = base / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"❌ missing manifest: {manifest_path}")

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assets = data.get("assets", {})

    clips = assets.get("clips", [])
    moment_renders = assets.get("moment_renders", [])
    top_ranked = assets.get("top_ranked", [])

    if len(clips) < 3:
        raise SystemExit(f"❌ too few clips: {len(clips)}")
    if len(moment_renders) < 3:
        raise SystemExit(f"❌ too few moment_renders: {len(moment_renders)}")
    if len(top_ranked) < 1:
        raise SystemExit(f"❌ missing top_ranked outputs")

    tiny = []
    for group_name in ("clips", "moment_renders", "top_ranked"):
        for row in assets.get(group_name, []):
            if row["size"] < 50000:
                tiny.append(f'{group_name}/{row["name"]}')

    if tiny:
        raise SystemExit("❌ tiny invalid media files: " + ", ".join(tiny))

    print("VALID_MANIFEST_OK")
    print("run_id:", args.run_id)
    print("clips:", len(clips))
    print("moment_renders:", len(moment_renders))
    print("top_ranked:", len(top_ranked))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
