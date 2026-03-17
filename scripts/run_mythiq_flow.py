#!/usr/bin/env python3
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "mythiq" / "out"
OUT.mkdir(parents=True, exist_ok=True)

FLOW_MAP = {
    "flow.video_to_shorts": ROOT / "mythiq" / "flows" / "video_to_shorts",
    "flow.explainer_text": ROOT / "mythiq" / "flows" / "explainer_text",
    "flow.game_pack_builder": ROOT / "mythiq" / "flows" / "game_pack_builder",
}

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def save_output(flow_id: str, payload: dict) -> Path:
    safe = flow_id.replace(".", "_")
    out = OUT / f"{safe}.request.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out

def main() -> int:
    if len(sys.argv) != 2:
        print("usage: scripts/run_mythiq_flow.py path/to/input.json", file=sys.stderr)
        return 2

    inp_path = Path(sys.argv[1]).resolve()
    if not inp_path.exists():
        print(f"missing input file: {inp_path}", file=sys.stderr)
        return 2

    payload = load_json(inp_path)
    flow_id = payload.get("flow_id")
    if flow_id not in FLOW_MAP:
        print(f"unknown flow_id: {flow_id}", file=sys.stderr)
        return 2

    flow_dir = FLOW_MAP[flow_id]
    spec = load_json(flow_dir / "spec.json")
    prompt = (flow_dir / "prompt.txt").read_text(encoding="utf-8")

    bundle = {
        "flow_id": flow_id,
        "spec": spec,
        "input": payload,
        "prompt": prompt
    }

    out = save_output(flow_id, bundle)

    print("=" * 80)
    print(f"FLOW: {flow_id}")
    print(f"INPUT: {inp_path}")
    print(f"BUNDLE: {out}")
    print("=" * 80)
    print(prompt)
    print("=" * 80)
    print(json.dumps(payload, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
