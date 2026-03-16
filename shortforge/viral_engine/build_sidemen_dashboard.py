import json
import os
from pathlib import Path

root = Path(".").resolve()
run_id = os.environ["RUN_ID"]
report = root / "shortforge" / "projects" / run_id / "reports" / "proof_report.json"
out_html = root / "web" / "shorts_review" / "sidemen_proof.html"

data = json.loads(report.read_text(encoding="utf-8"))
rows = data["ranked_clips"]

cards = []
for i, row in enumerate(rows[:12], 1):
    s = row["score"]
    preview = row.get("transcript_text", "")[:220].replace("<", "&lt;").replace(">", "&gt;")
    cards.append(f"""
    <div class="card">
      <h3>#{i} — {row['name']}</h3>
      <p><b>Sector:</b> {row['sector']}</p>
      <p><b>Viral score:</b> {s['viral_score']}</p>
      <p>Hook: {s['hook_strength']} · Arc: {s['emotional_arc']} · Pace: {s['pacing_score']}</p>
      <p>Hook hits: {s['hook_hits']} · Arc hits: {s['arc_hits']} · Words: {s['word_count']} · Segments: {s['segment_count']}</p>
      <p><b>Transitions:</b> {", ".join(row["recommended_transitions"])}</p>
      <p><b>Transcript preview:</b> {preview}</p>
    </div>
    """)

html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sidemen Proof</title>
<style>
body{{margin:0;background:#0b1118;color:#e8edf3;font-family:-apple-system,BlinkMacSystemFont,sans-serif}}
.wrap{{max-width:1440px;margin:0 auto;padding:24px}}
.hero,.card{{background:#121922;border:1px solid #223142;border-radius:18px;padding:16px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:18px;margin-top:20px}}
p{{line-height:1.35}}
</style>
</head>
<body>
<div class="wrap">
  <section class="hero">
    <h1>Mythiq Sector Proof Dashboard</h1>
    <p><b>Source:</b> {data["source_name"]}</p>
    <p><b>Sector:</b> {data["sector"]}</p>
    <p><b>Ideal lengths:</b> {", ".join(str(x) for x in data["library"]["ideal_lengths"])}</p>
  </section>
  <div class="grid">
    {''.join(cards)}
  </div>
</div>
</body>
</html>
"""

out_html.write_text(html, encoding="utf-8")
print("✅ wrote", out_html)
