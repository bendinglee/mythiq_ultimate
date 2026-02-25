#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m py_compile api/app/main.py
echo "✅ api/app/main.py compiles"
