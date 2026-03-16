from __future__ import annotations

import argparse
import html
import json
import shutil
from pathlib import Path


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def copy_file(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def first_existing(*paths):
    for p in paths:
        if p.exists():
            return p
    return None


def resolve_root(root: Path) -> Path:
    root = root.resolve()

    # If caller passed a metadata directory, resolve to matching real rendered tmp job.
    if root.name.startswith("mythiq_shorts_") and "artifacts/shorts_meta" in str(root):
        slug = root.name
        for base in (Path("/private/tmp"), Path("/tmp")):
            cand = (base / slug).resolve()
            renders = cand / "ultimate" / "renders"
            if cand.is_dir() and renders.exists() and list(renders.glob("*.mp4")):
                return cand

    return root


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    args = ap.parse_args()

    root = resolve_root(Path(args.root))
    job_id = root.name

    meta = root / "meta"
    rows_path = first_existing(
        meta / "export_candidates.json",
        meta / "quality.json",
        meta / "selected.json",
    )
    rows = load_json(rows_path) if rows_path else []

    renders = sorted((root / "ultimate" / "renders").glob("*.mp4"))

    web_root = Path("web/shorts_review")
    media_root = web_root / "media" / job_id
    media_root.mkdir(parents=True, exist_ok=True)

    items = []
    for i, mp4 in enumerate(renders, 1):
        row = rows[i - 1] if i - 1 < len(rows) else {}
        filename = f"{i:02d}_{mp4.name}"
        rel = f"media/{job_id}/{filename}"
        dst = web_root / rel
        copy_file(mp4, dst)

        items.append({
            "index": i,
            "title": row.get("title") or f"Short {i:02d}",
            "video_url": rel,
            "download_url": rel,
            "angle": row.get("angle"),
            "quality_score": row.get("quality_score"),
            "export_score": row.get("export_score"),
            "start": row.get("start"),
            "end": row.get("end"),
            "hook": row.get("hook"),
            "story_setup": row.get("story_setup"),
            "story_conflict": row.get("story_conflict") or row.get("hook"),
            "story_payoff": row.get("story_payoff"),
        })

    save_json(web_root / "shorts_index.json", items)

    def esc(x):
        return html.escape("" if x is None else str(x))

    cards = []
    for item in items:
        cards.append(f"""
        <article class="card">
          <div class="badge">{esc(item["index"]):>02}</div>
          <h2>{esc(item["title"])}</h2>
          <div class="meta">
            <span>angle: {esc(item["angle"])}</span>
            <span>quality: {esc(item["quality_score"])}</span>
            <span>export: {esc(item["export_score"])}</span>
            <span>range: {esc(item["start"])}→{esc(item["end"])}</span>
          </div>
          <video controls preload="metadata" playsinline src="{esc(item['video_url'])}"></video>
          <div class="story">
            <p><strong>Setup</strong><br>{esc(item.get("story_setup") or "-")}</p>
            <p><strong>Conflict</strong><br>{esc(item.get("story_conflict") or "-")}</p>
            <p><strong>Payoff</strong><br>{esc(item.get("story_payoff") or "-")}</p>
          </div>
          <p class="actions"><a href="{esc(item['download_url'])}" download>Download clip</a></p>
        </article>
        """)

    html_doc = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>Shorts Review</title>
<style>
body {{
  font-family: -apple-system, BlinkMacSystemFont, sans-serif;
  background: #0b0f14;
  color: #e8eef5;
  margin: 0;
  padding: 24px;
}}
.wrap {{
  max-width: 1400px;
  margin: 0 auto;
}}
.grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
  gap: 20px;
}}
.card {{
  background: #121821;
  border: 1px solid #253041;
  border-radius: 16px;
  padding: 16px;
}}
.badge {{
  display: inline-block;
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 999px;
  background: #1d2633;
  margin-bottom: 8px;
}}
h1 {{
  margin: 0 0 20px 0;
}}
h2 {{
  margin: 0 0 10px 0;
  font-size: 20px;
}}
.meta {{
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  font-size: 12px;
  opacity: 0.9;
  margin-bottom: 12px;
}}
video {{
  width: 100%;
  border-radius: 12px;
  background: #000;
}}
.story {{
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
  margin-top: 12px;
}}
.actions {{
  margin-top: 12px;
}}
a {{
  color: #8ec5ff;
}}
</style>
</head>
<body>
  <div class="wrap">
    <h1>Shorts Review</h1>
    <div class="grid">
      {''.join(cards)}
    </div>
  </div>
</body>
</html>
"""
    (web_root / "index.html").write_text(html_doc, encoding="utf-8")

    print(f"WROTE {web_root / 'index.html'}")
    print(f"WROTE {web_root / 'shorts_index.json'}")
    print(f"ITEMS {len(items)}")


if __name__ == "__main__":
    main()
