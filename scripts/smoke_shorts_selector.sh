#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

TMP="$(mktemp -d)"
cat > "$TMP/in.json" <<'JSON'
[
  {"start":0,"end":3,"text":"Why this changed everything","score":9,"angle":"curiosity","hook":"Why this changed everything","payoff":"big payoff","region":"early"},
  {"start":1,"end":4,"text":"Why this changed everything again","score":8.8,"angle":"curiosity","hook":"Why this changed everything","payoff":"big payoff","region":"early"},
  {"start":10,"end":13,"text":"The biggest mistake they made","score":8.6,"angle":"problem","hook":"The biggest mistake they made","payoff":"mistake payoff","region":"mid"},
  {"start":20,"end":23,"text":"What happened next was insane","score":8.3,"angle":"extreme","hook":"What happened next was insane","payoff":"insane ending","region":"late"}
]
JSON

python3 api/app/diversity_selector.py "$TMP/in.json" --out "$TMP/out.json" --target-count 3 >/dev/null
python3 - <<'PY' "$TMP/out.json"
import json, sys
rows = json.load(open(sys.argv[1]))
assert len(rows) == 3, rows
assert rows[0]["angle"] == "curiosity"
assert rows[1]["angle"] != "curiosity" or rows[1]["text"] != "Why this changed everything again"
print("SMOKE_SHORTS_SELECTOR_OK", len(rows))
PY
