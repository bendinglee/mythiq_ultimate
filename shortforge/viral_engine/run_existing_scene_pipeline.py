from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / ".venv" / "bin" / "python"

def pyexe() -> str:
    if PYTHON.exists():
        return str(PYTHON)
    return sys.executable

def run(cmd: list[str], env: dict[str, str]) -> None:
    print("RUN:", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()

    env = os.environ.copy()
    env["RUN_ID"] = args.run_id

    scene_dir = ROOT / "shortforge" / "projects" / args.run_id / "scene_renders"
    scenes = sorted(scene_dir.glob("*.mp4"))
    if not scenes:
        raise SystemExit(f"❌ no scene renders found in {scene_dir}")
    if len(scenes) < 5:
        raise SystemExit(f"❌ too few scene renders for reuse: found {len(scenes)} in {scene_dir}")
    tiny = [p for p in scenes if p.stat().st_size < 50000]
    if tiny:
        raise SystemExit("❌ invalid tiny scene renders: " + ", ".join(x.name for x in tiny))

    print("PYTHON:", pyexe())
    print("SCENE_COUNT:", len(scenes))
    for p in scenes[:10]:
        print("SCENE:", p.name)

    py = pyexe()
    cmds = [
        [py, "shortforge/viral_engine/transcribe_moment_candidates.py"],
        [py, "shortforge/viral_engine/build_moment_proof_plan.py"],
        [py, "shortforge/viral_engine/build_moment_dashboard.py"],
    ]

    for cmd in cmds:
        run(cmd, env)

    base = ROOT / "shortforge" / "projects" / args.run_id
    reports = base / "reports"

    expected = [
        reports / "moment_proof_report.json",
        reports / "sidemen_top5.zip",
        reports / "top5_summary.csv",
    ]
    print("\n✅ existing-scene pipeline completed")
    for p in expected:
        print(("OK" if p.exists() else "MISSING"), p)

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
