from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = ROOT / ".venv" / "bin" / "python"

def run(cmd: list[str]) -> None:
    print("RUN:", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)

def count_files(p: Path, pattern: str) -> int:
    if not p.exists():
        return 0
    return sum(1 for x in p.glob(pattern) if x.is_file())

def infer_counts(base: Path) -> dict[str, int]:
    manifest_path = base / "manifest.json"
    if manifest_path.exists():
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assets = data.get("assets", {})
        return {k: len(v) for k, v in assets.items() if isinstance(v, list)}
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

    counts = infer_counts(base)
    mode = detect_mode(counts)

    print("PROJECT_MODE:", mode)
    print("RUN_ID:", args.run_id)

    if mode == "moment_render_pipeline":
        print("✅ project is reusable moment-render pipeline")
        return 0
    if mode == "archive_only":
        raise SystemExit("❌ archive-only project: review/package only, not runnable")
    if mode == "candidate_pipeline":
        print("⚠️ candidate-only project: runner not implemented yet")
        return 0
    if mode == "scene_pipeline":
        print("⚠️ scene pipeline detected: runner path not implemented yet")
        return 0

    raise SystemExit("❌ unknown project mode")

if __name__ == "__main__":
    raise SystemExit(main())
