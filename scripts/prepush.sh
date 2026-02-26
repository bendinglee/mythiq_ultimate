#!/usr/bin/env bash
set -euo pipefail
python3 -m py_compile api/app/main.py >/dev/null
./scripts/smoke_openapi.sh
