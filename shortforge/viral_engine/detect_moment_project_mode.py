from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def count_files(p: Path, pattern: str) -> int:
    if not p.exists():
        return 0
    return sum(1 for x in p.glob(pattern) if x.is_file())

def infer_counts_from_fs(base: Path) -> dict[str, int]:
    return {
        "clips": count_files(base / "clips", "*.mp4"),
        "moment_renders": count_files(base / "moment_renders", "*.mp4"),
        "top_ranked": count_files(base / "top_ranked", "*.mp4"),
        "scene_renders": count_files(base / "scene_renders", "*.mp4"),
        "final_selects": count_files(base / "final_selects", "*.mp4"),
    }

def detect_mode(counts: dict[str, int]) -> str:
    if counts.get("scene_renders", 0) >= 5 and counts.get("final_selects", 0) >= 1:
        return "scene_pipeline"
    if counts.get("moment_renders", 0) >= 3 and counts.get("top_ranked", 0) >= 1:
        return "moment_render_pipeline"
    if counts.get("clips", 0) >= 3:
        return "candidate_pipeline"
    if counts.get("final_selects", 0) >= 1:
        return "archive_only"
    return "unknown"

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()

    base = ROOT / "shortforge" / "projects" / args.run_id
    if not base.exists():
        raise SystemExit(f"❌ missing project: {base}")

    manifest_path = base / "manifest.json"

    if manifest_path.exists():
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assets = data.get("assets", {})
        counts = {k: len(v) for k, v in assets.items() if isinstance(v, list)}
        source = "manifest"
    else:
        counts = infer_counts_from_fs(base)
        source = "filesystem"

    mode = detect_mode(counts)

    print("PROJECT_MODE", mode)
    print("run_id", args.run_id)
    print("source", source)
    for k in sorted(counts):
        print(k, counts[k])

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
