#!/usr/bin/env bash
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:7777}"
./scripts/dev.sh smoke >/dev/null
./scripts/learn_ab_pick.py --base "$BASE" --limit 5000
./scripts/learn_rewards.py --base "$BASE" --gen_limit 5000 --out_limit 5000
echo LEARN_ALL_OK
