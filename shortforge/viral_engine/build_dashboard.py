import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "shortforge" / "viral_engine" / "reports" / "latest_proof_report.json"
WEB = ROOT / "web" / "shorts_review"

data = json.loads(REPORT.read_text(encoding="utf-8"))
rows = data["ranked_clips"]

cards = []
for i, row in enumerate(rows[:10], 1):
    name = row["name"]
    score = row["score"]["viral_score"]
    hook = row["score"]["hook_strength"]
    arc = row["score"]["emotional_arc"]
    pace = row["score"]["pacing_score"]
    cards.append(f"""
    <div class="card">
      <h3>#{i} — {name}</h3>
      <p><b>Sector:</b> {row['sector']}</p>
      <p><b>Viral score:</b> {score}</p>
      <p>Hook: {hook} · Arc: {arc} · Pace: {pace}</p>
      <p><b>Transitions:</b> {", ".join(row["recommended_transitions"])}</p>
    </div>
    """)

html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mythiq Viral Proof</title>
<style>
body{{margin:0;background:#0b1118;color:#e8edf3;font-family:-apple-system,BlinkMacSystemFont,sans-serif}}
.wrap{{max-width:1440px;margin:0 auto;padding:24px}}
.hero,.card{{background:#121922;border:1px solid #223142;border-radius:18px;padding:16px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:18px;margin-top:20px}}
</style>
</head>
<body>
<div class="wrap">
  <section class="hero">
    <h1>Mythiq Viral Engine Proof Dashboard</h1>
    <p><b>Detected sector:</b> {data["sector"]}</p>
    <p><b>Source batch:</b> {data["source_batch"]}</p>
    <p><b>Ideal lengths:</b> {", ".join(str(x) for x in data["library"]["ideal_lengths"])}</p>
  </section>
  <div class="grid">
    {''.join(cards)}
  </div>
</div>
</body>
</html>
"""

(WEB / "viral_proof.html").write_text(html, encoding="utf-8")
print("✅ dashboard written:", WEB / "viral_proof.html")
