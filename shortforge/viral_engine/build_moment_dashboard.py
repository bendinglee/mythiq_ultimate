import json
import os
import shutil
import zipfile
from pathlib import Path

run_id = os.environ["RUN_ID"]
base = Path.cwd() / "shortforge" / "projects" / run_id
report = base / "reports" / "moment_proof_report.json"
scene_dir = base / "scene_renders"
final_dir = base / "final_selects"
web_dir = Path.cwd() / "web" / "shorts_review"

if not report.exists():
    raise SystemExit(f"❌ missing report: {report}")

data = json.loads(report.read_text(encoding="utf-8"))
rows = data.get("ranked_clips", [])
if not rows:
    raise SystemExit("❌ no ranked clips found")

web_dir.mkdir(parents=True, exist_ok=True)
final_dir.mkdir(parents=True, exist_ok=True)

# rebuild final top 5 folder
for old in final_dir.glob("*.mp4"):
    old.unlink()

top5 = rows[:5]
for i, row in enumerate(top5, 1):
    src = scene_dir / row["name"]
    if not src.exists():
        print("skip missing final:", src)
        continue
    dst = final_dir / f"{i:02d}_{row['name']}"
    shutil.copy2(src, dst)

# build zip of top 5
zip_path = base / "reports" / "sidemen_top5.zip"
if zip_path.exists():
    zip_path.unlink()

with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for p in sorted(final_dir.glob("*.mp4")):
        zf.write(p, arcname=p.name)

cards = []
for i, row in enumerate(rows, 1):
    s = row["score"]
    file_name = row["name"]
    video_path = f"/shortforge/projects/{run_id}/scene_renders/{file_name}"
    download_path = video_path
    preview = row.get("transcript_text", "")[:260].replace("<", "&lt;").replace(">", "&gt;")

    cards.append(f"""
    <div class="card">
      <h2>#{i} — {file_name}</h2>
      <p><b>Score:</b> {s['viral_score']}</p>
      <p><b>Source:</b> {row.get('source_clip', 'scene')}</p>
      <p>Hook: {s.get('hook_hits', 0)} · Arc: {s.get('arc_hits', 0)} · Words: {s.get('word_count', 0)} · Segments: {s.get('segment_count', 0)}</p>

      <video controls preload="metadata" playsinline>
        <source src="{video_path}" type="video/mp4">
      </video>

      <div class="actions">
        <a class="btn" href="{download_path}" download>Download clip</a>
      </div>

      <p><b>Transcript:</b> {preview}</p>
    </div>
    """)

moments_html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sidemen Moments</title>
<style>
body{{margin:0;background:#0b1118;color:#e8edf3;font-family:-apple-system,BlinkMacSystemFont,sans-serif}}
.wrap{{max-width:1280px;margin:0 auto;padding:24px}}
.hero,.card{{background:#121922;border:1px solid #223142;border-radius:18px;padding:18px}}
.grid{{display:grid;grid-template-columns:1fr;gap:18px;margin-top:20px}}
video{{width:100%;border-radius:12px;margin:12px 0;background:#000}}
h1,h2{{margin-top:0}}
p{{line-height:1.4}}
.actions{{display:flex;gap:12px;flex-wrap:wrap;margin:10px 0 6px 0}}
.btn{{display:inline-block;padding:10px 14px;border-radius:10px;background:#2563eb;color:#fff;text-decoration:none;font-weight:600}}
.btn.secondary{{background:#0f766e}}
</style>
</head>
<body>
<div class="wrap">
  <section class="hero">
    <h1>Mythiq Viral Moment Dashboard</h1>
    <p><b>Run ID:</b> {data["run_id"]}</p>
    <p><b>Source:</b> {data["source_name"]}</p>
    <p><b>Sector:</b> {data["sector"]}</p>
    <div class="actions">
      <a class="btn secondary" href="/shortforge/projects/{run_id}/reports/sidemen_top5.zip" download>Download Top 5 ZIP</a>
      <a class="btn" href="/web/shorts_review/sidemen_top5.html">Open Top 5 page</a>
    </div>
  </section>
  <div class="grid">
    {''.join(cards)}
  </div>
</div>
</body>
</html>
"""

top5_cards = []
for i, row in enumerate(top5, 1):
    src_name = f"{i:02d}_{row['name']}"
    video_path = f"/shortforge/projects/{run_id}/final_selects/{src_name}"
    preview = row.get("transcript_text", "")[:260].replace("<", "&lt;").replace(">", "&gt;")
    s = row["score"]

    top5_cards.append(f"""
    <div class="card">
      <h2>#{i} — {src_name}</h2>
      <p><b>Score:</b> {s['viral_score']}</p>
      <video controls preload="metadata" playsinline>
        <source src="{video_path}" type="video/mp4">
      </video>
      <div class="actions">
        <a class="btn" href="{video_path}" download>Download clip</a>
      </div>
      <p><b>Transcript:</b> {preview}</p>
    </div>
    """)

top5_html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Top 5 Sidemen Scenes</title>
<style>
body{{margin:0;background:#0b1118;color:#e8edf3;font-family:-apple-system,BlinkMacSystemFont,sans-serif}}
.wrap{{max-width:1280px;margin:0 auto;padding:24px}}
.hero,.card{{background:#121922;border:1px solid #223142;border-radius:18px;padding:18px}}
.grid{{display:grid;grid-template-columns:1fr;gap:18px;margin-top:20px}}
video{{width:100%;border-radius:12px;margin:12px 0;background:#000}}
h1,h2{{margin-top:0}}
.actions{{display:flex;gap:12px;flex-wrap:wrap;margin:10px 0 6px 0}}
.btn{{display:inline-block;padding:10px 14px;border-radius:10px;background:#2563eb;color:#fff;text-decoration:none;font-weight:600}}
.btn.secondary{{background:#0f766e}}
</style>
</head>
<body>
<div class="wrap">
  <section class="hero">
    <h1>Top 5 Final Picks</h1>
    <p><b>Run ID:</b> {data["run_id"]}</p>
    <p><b>Source:</b> {data["source_name"]}</p>
    <div class="actions">
      <a class="btn secondary" href="/shortforge/projects/{run_id}/reports/sidemen_top5.zip" download>Download Top 5 ZIP</a>
      <a class="btn" href="/web/shorts_review/sidemen_moments.html">Open Full Ranking</a>
    </div>
  </section>
  <div class="grid">
    {''.join(top5_cards)}
  </div>
</div>
</body>
</html>
"""

(web_dir / "sidemen_moments.html").write_text(moments_html, encoding="utf-8")
(web_dir / "sidemen_top5.html").write_text(top5_html, encoding="utf-8")

csv_path = base / "reports" / "top5_summary.csv"
with csv_path.open("w", encoding="utf-8") as f:
    f.write("rank,file,score\n")
    for i, row in enumerate(top5, 1):
        f.write(f'{i},"{row["name"]}",{row["score"]["viral_score"]}\n')

print("✅ final selects:", final_dir)
for p in sorted(final_dir.glob("*.mp4")):
    print("-", p.name)
print("✅ zip:", zip_path)
print("✅ csv:", csv_path)
print("✅ wrote", web_dir / "sidemen_moments.html")
print("✅ wrote", web_dir / "sidemen_top5.html")
