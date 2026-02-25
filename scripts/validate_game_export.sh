#!/usr/bin/env bash
set -euo pipefail
DIR="${1:?usage: validate_game_export.sh <export_dir>}"

test -f "$DIR/index.html" || { echo "FAIL: missing index.html"; exit 1; }

# lightweight sanity: does index.html reference a script?
grep -Eiq "<script" "$DIR/index.html" || { echo "FAIL: index.html has no script tag"; exit 1; }

echo "OK: basic export validation passed"
