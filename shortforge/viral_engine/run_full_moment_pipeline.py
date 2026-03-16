from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def run(cmd: list[str], env: dict[str, str]) -> None:
    print("RUN:", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True, help="shortforge project run id, e.g. sidemen_scene_pipeline")
    ap.add_argument("--source-video", required=True, help="path to source video file")
    args = ap.parse_args()

    source_video = Path(args.source_video).expanduser()
    if not source_video.is_absolute():
        source_video = (ROOT / source_video).resolve()

    if not source_video.exists():
        raise SystemExit(f"❌ source video not found: {source_video}")

    env = os.environ.copy()
    env["RUN_ID"] = args.run_id
    env["SOURCE_VIDEO"] = str(source_video)

    cmds = [
        [sys.executable, "shortforge/viral_engine/render_scene_candidates.py"],
        [sys.executable, "shortforge/viral_engine/transcribe_moment_candidates.py"],
        [sys.executable, "shortforge/viral_engine/build_moment_proof_plan.py"],
        [sys.executable, "shortforge/viral_engine/build_moment_dashboard.py"],
    ]

    for cmd in cmds:
        run(cmd, env)

    base = ROOT / "shortforge" / "projects" / args.run_id
    final_dir = base / "final_selects"
    reports_dir = base / "reports"

    print("\n✅ full moment pipeline completed")
    print("RUN_ID:", args.run_id)
    print("SOURCE_VIDEO:", source_video)
    print("FINAL_DIR:", final_dir)
    print("REPORTS_DIR:", reports_dir)

    expected = [
        reports_dir / "moment_proof_report.json",
        reports_dir / "sidemen_top5.zip",
        reports_dir / "top5_summary.csv",
    ]
    for p in expected:
        print(("OK" if p.exists() else "MISSING"), p)

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
