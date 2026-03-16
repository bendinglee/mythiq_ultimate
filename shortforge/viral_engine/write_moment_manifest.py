from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def files_with_sizes(p: Path, pattern: str):
    out = []
    for f in sorted(p.glob(pattern)):
        if f.is_file():
            out.append({
                "name": f.name,
                "size": f.stat().st_size,
            })
    return out

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()

    base = ROOT / "shortforge" / "projects" / args.run_id
    if not base.exists():
        raise SystemExit(f"❌ missing project: {base}")

    manifest = {
        "run_id": args.run_id,
        "project_dir": str(base),
        "kind": "moment_project",
        "status": "active",
        "assets": {
            "clips": files_with_sizes(base / "clips", "*.mp4") if (base / "clips").exists() else [],
            "moment_renders": files_with_sizes(base / "moment_renders", "*.mp4") if (base / "moment_renders").exists() else [],
            "top_ranked": files_with_sizes(base / "top_ranked", "*.mp4") if (base / "top_ranked").exists() else [],
            "scene_renders": files_with_sizes(base / "scene_renders", "*.mp4") if (base / "scene_renders").exists() else [],
            "final_selects": files_with_sizes(base / "final_selects", "*.mp4") if (base / "final_selects").exists() else [],
        },
        "reports": files_with_sizes(base / "reports", "*.json") + files_with_sizes(base / "reports", "*.csv"),
    }

    out = base / "manifest.json"
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"✅ wrote {out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
