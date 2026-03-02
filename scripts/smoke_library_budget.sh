#!/usr/bin/env bash
set -euo pipefail

test -f libs/text/seed.json
test -f libs/code/seed.json

python - <<'PY'
import json
from pathlib import Path

def tok(s:str)->int:
    # cheap proxy; replace later with real token counter
    return max(1, len(s.split()))

total=0
for fp in [Path("libs/text/seed.json"), Path("libs/code/seed.json")]:
    rows=json.loads(fp.read_text(encoding="utf-8"))
    assert 1 <= len(rows) <= 50
    for r in rows[:5]:
        t=tok(r["prompt_template"])
        assert t <= 200, (fp, r["id"], t)
        total += t
assert total <= 1000, total
print("SMOKE_LIB_BUDGET_OK total_words=", total)
PY
