#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

python3 scripts/run_mythiq_flow.py mythiq/examples/video_input_minecraft_server.json
python3 scripts/run_mythiq_flow.py mythiq/examples/explainer_input_tesla.json
python3 scripts/run_mythiq_flow.py mythiq/examples/game_input_football_packs.json
