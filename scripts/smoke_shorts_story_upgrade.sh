#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

python3 scripts/shorts_story_upgrade.py >/tmp/shorts_story_upgrade.log 2>&1 || {
  cat /tmp/shorts_story_upgrade.log
  exit 1
}

LATEST="$(find artifacts -path '*/semantic_upgrade/ultimate/meta/storyline_plan.json' | tail -n 1)"
test -n "${LATEST:-}" || { echo "missing storyline_plan.json"; exit 1; }

python3 - <<'PY'
import json, pathlib, sys
paths = list(pathlib.Path("artifacts").glob("shorts_*/semantic_upgrade/ultimate/meta/storyline_plan.json"))
if not paths:
    raise SystemExit("no storyline_plan.json found")
p = max(paths, key=lambda x: x.stat().st_mtime)
data = json.loads(p.read_text())
assert isinstance(data, list) and len(data) >= 1, "empty storyline plan"
ok = 0
for row in data:
    out = row.get("output_video")
    if out and pathlib.Path(out).exists():
        ok += 1
assert ok >= 1, "no output videos found"
print("SMOKE_SHORTS_STORY_UPGRADE_OK", ok)
PY
