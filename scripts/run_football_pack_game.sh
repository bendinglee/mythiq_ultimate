#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../mythiq/generated/football_pack_game"
python3 -m http.server 8088
