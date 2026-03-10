#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/generate_demo_outputs.py
echo
echo "Generated:"
ls -1 mythiq/results
