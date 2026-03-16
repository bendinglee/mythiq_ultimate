from __future__ import annotations

import argparse
import html
import json
import random
import re
import shutil
import sqlite3
import subprocess
import time
from pathlib import Path

DB_PATH = Path("shortforge/db/shortforge.sqlite3")
WEB = Path("web/shorts_review")

def sh(cmd, check=True):
    return subprocess.run(cmd, text=True, capture_output=True, check=check)

def norm(text: str) -> str:
    return " ".join((text or "").lower().replace("\n", " ").split())

def slug(text: str) -> str:
    t = re.sub(r"[^a-z0-9]+", "_", norm(text)).strip("_")
    return t[:80] or "clip"

def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS exports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id TEXT,
        run_id TEXT,
        variant TEXT,
        start REAL,
        end REAL,
        title TEXT,
        transcript TEXT,
        anchor_text TEXT,
        score REAL,
        created_at REAL
    )
    """)
    conn.commit()
    return conn

def prev_texts(conn, source_id: str):
    if not source_id:
        return []
    rows = conn.execute(
        "SELECT transcript FROM exports WHERE source_id=? ORDER BY created_at DESC LIMIT 200",
        (source_id,)
    ).fetchall()
    return [r[0] for r in rows if r and r[0]]

def ff_duration(path: Path) -> float:
    out = sh([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1",
        str(path)
    ]).stdout.strip()
    return float(out)

def transcribe(video: Path, out_json: Path):
    if out_json.exists():
        return json.loads(out_json.read_text(encoding="utf-8"))

    from faster_whisper import WhisperModel

    model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(video), vad_filter=True, word_timestamps=True, beam_size=5)

    words = []
    segs = []
    for s in segments:
        seg_text = (s.text or "").strip()
        segs.append({"start": float(s.start), "end": float(s.end), "text": seg_text})
        if s.words:
            for w in s.words:
                token = (w.word or "").strip()
                if token:
                    words.append({
                        "start": float(w.start),
                        "end": float(w.end),
                        "word": token
                    })

    data = {
        "language": getattr(info, "language", "en"),
        "segments": segs,
        "words": words,
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def infer_sector(text: str) -> str:
    t = norm(text)
    if any(x in t for x in ["minecraft", "pvp", "hunter", "hunters", "trap", "pearl", "netherite", "fight", "cobweb"]):
        return "gaming"
    if any(x in t for x in ["learn", "lesson", "explain", "how to", "why this works"]):
        return "education"
    if any(x in t for x in ["stock", "market", "money", "finance", "invest"]):
        return "finance"
    if any(x in t for x in ["story", "happened", "found out", "realized"]):
        return "story"
    return "commentary"

def detect_event_type(anchor_text: str, transcript: str, short_style: str = "auto") -> str:
    t = norm((anchor_text or "") + " " + (transcript or ""))
    if short_style != "auto":
        return short_style
    if any(x in t for x in ["trap", "bait", "stasis"]):
        return "trap"
    if any(x in t for x in ["clutch", "pearl", "survive", "survived", "escape", "escaped", "last second"]):
        return "clutch"
    if any(x in t for x in ["fell", "throw", "failed", "oops", "choked"]):
        return "fail"
    if any(x in t for x in ["revealed", "realized", "truth", "found out"]):
        return "reveal"
    return "destroy"

def generate_headline(event_type: str, anchor_text: str, transcript: str, sector: str) -> str:
    t = norm((anchor_text or "") + " " + (transcript or ""))

    if event_type == "trap":
        if "cobweb" in t or "web" in t:
            return "The Cobweb Trap Changed Everything"
        if "trap" in t:
            return "This Trap Actually Worked"
        return "He Walked Right Into It"

    if event_type == "clutch":
        if "pearl" in t:
            return "That Pearl Saved The Fight"
        if "horse" in t:
            return "The Horse Saved Everything"
        if "survive" in t or "survived" in t or "unkillable" in t:
            return "He Should Not Have Survived This"
        return "This Was A Massive Clutch"

    if event_type == "fail":
        if "fell" in t:
            return "He Actually Fell For It"
        if "wolves" in t or "wolf" in t:
            return "The Wolves Made This Fight Worse"
        return "Everything Went Wrong Here"

    if event_type == "reveal":
        return "This Changed Everything"

    if "10 players" in t or "outnumbered" in t or "by myself" in t:
        return "He Was Outnumbered From The Start"
    if "cobweb" in t or "web" in t:
        return "The Cobweb Trap Changed Everything"
    if "horse" in t or "unkillable" in t:
        return "He Nearly Lost Everything Here"
    if "wolves" in t or "wolf" in t:
        return "The Wolves Changed This Fight"
    if "hunters" in t:
        return "They Picked The Wrong Fight"
    if "netherite" in t:
        return "He Nearly Lost Everything Here"
    if "fight" in t:
        return "This Fight Turned Around Instantly"
    return "This Fight Turned Instantly"



def generate_title_candidates(event_type:str, anchor_text:str, transcript:str, sector:str):
    t = norm((anchor_text or "") + " " + (transcript or ""))
    out = []

    primary = generate_headline(event_type, anchor_text, transcript, sector)
    out.append(primary)

    if event_type == "destroy":
        if "outnumbered" in t or "10 players" in t or "by myself" in t:
            out += [
                "He Was Not Supposed To Win This",
                "He Was Outnumbered From The Start",
                "This Fight Should Have Been Over"
            ]
        elif "fight" in t:
            out += [
                "This Fight Turned Around Instantly",
                "He Should Not Have Taken This Fight",
                "One Move Changed This Fight"
            ]
    elif event_type == "trap":
        out += [
            "The Cobweb Trap Changed Everything",
            "This Trap Actually Worked",
            "He Walked Right Into It"
        ]
    elif event_type == "clutch":
        out += [
            "This Was A Massive Clutch",
            "He Should Not Have Survived This",
            "That Pearl Saved The Fight"
        ]
    elif event_type == "fail":
        out += [
            "Everything Went Wrong Here",
            "He Actually Fell For It",
            "This Was A Complete Throw"
        ]
    elif event_type == "reveal":
        out += [
            "This Changed Everything",
            "This Reveal Changed The Fight",
            "The Truth Changed Everything"
        ]

    # dedupe while preserving order
    seen = set()
    clean = []
    for x in out:
        k = x.strip().lower()
        if k and k not in seen:
            clean.append(x.strip())
            seen.add(k)
    return clean[:5]

def generate_description_candidates(event_type:str, anchor_text:str, transcript:str, sector:str):
    t = norm(transcript)
    out = []

    if sector == "gaming":
        if "cobweb" in t or "web" in t:
            out += [
                "A combat trick turns the fight completely in his favor.",
                "What looks risky at first becomes the move that changes the whole fight.",
                "The entire fight shifts once the cobweb setup works."
            ]
        elif "10 players" in t or "by myself" in t or "outnumbered" in t:
            out += [
                "He gets overwhelmed early, but the fight does not go the way anyone expects.",
                "He starts at a huge disadvantage and still finds a way to turn it.",
                "What should be a losing fight becomes a real comeback moment."
            ]
        elif "wolves" in t or "wolf" in t:
            out += [
                "What should be a normal fight gets thrown off by wolves in the middle of the action.",
                "The fight turns chaotic once the wolves become part of it.",
                "A normal combat moment turns messy because of the wolves."
            ]
        elif "horse" in t or "unkillable" in t or "netherite" in t:
            out += [
                "He is close to losing everything and has to survive the most dangerous stretch of the fight.",
                "This becomes a survival moment the second the pressure spikes.",
                "He has almost no room for error and still manages to stay alive."
            ]
        elif "fight" in t:
            out += [
                "The fight shifts fast, and one decision changes the entire momentum.",
                "One moment flips the pressure and changes the outcome of the fight.",
                "What starts as a normal fight turns the second one move lands."
            ]
        else:
            out += [
                "A high-pressure gaming moment with a clear turning point.",
                "This short focuses on the key turning point in the action.",
                "A fast gaming moment where the outcome changes quickly."
            ]
    else:
        out += [
            "A focused short built around the main moment in the clip.",
            "This short centers on the key turning point.",
            "A concise clip built around the clearest payoff."
        ]

    seen = set()
    clean = []
    for x in out:
        k = x.strip().lower()
        if k and k not in seen:
            clean.append(x.strip())
            seen.add(k)
    return clean[:5]

def rank_text_candidate(text:str, transcript:str, used:list[str]):
    tt = norm(text)
    tr = norm(transcript)
    score = 0.0

    tw = set(tt.split())
    rw = set(tr.split())

    # overlap / relevance
    if tw and rw:
        score += len(tw & rw) / max(1, len(tw))

    # readability / compactness
    n = len(text.split())
    if 4 <= n <= 9:
        score += 0.8
    elif 10 <= n <= 14:
        score += 0.5

    # uniqueness against used strings
    if used:
        max_sim = 0.0
        for u in used:
            uw = set(norm(u).split())
            if not uw:
                continue
            sim = len(tw & uw) / max(1, len(tw | uw))
            if sim > max_sim:
                max_sim = sim
        score += (1.0 - max_sim) * 0.8
    else:
        score += 0.8

    return round(score, 4)



def learned_title_bonus(title):
    import json, pathlib
    path = pathlib.Path("shortforge/db/learned_weights.json")
    if not path.exists():
        return 0
    weights = json.loads(path.read_text())
    score = 0
    for w in title.lower().split():
        score += weights.get(w,0)
    return score * 0.01
def rank_title_desc_pair(title:str, desc:str, transcript:str, used_titles:list[str], used_descs:list[str]):
    score = 0.0
    score += rank_text_candidate(title, transcript, used_titles) + learned_title_bonus(title)
    score += rank_text_candidate(desc, transcript, used_descs)

    t = norm(title + " " + desc)
    tr = norm(transcript)

    # coherence bonuses
    if "cobweb" in tr and "cobweb" in t:
        score += 0.8
    if ("wolf" in tr or "wolves" in tr) and ("wolf" in t or "wolves" in t):
        score += 0.8
    if ("horse" in tr or "netherite" in tr or "unkillable" in tr) and ("lost everything" in t or "stay alive" in t or "survive" in t):
        score += 0.8
    if ("10 players" in tr or "by myself" in tr or "outnumbered" in tr) and ("outnumbered" in t or "should have been over" in t):
        score += 0.8
    if "fight" in tr and "fight" in t:
        score += 0.3

    return round(score, 4)


def log_clip_result(run_id, source_id, title, description, transcript, sector):
    import sqlite3
    conn = sqlite3.connect("shortforge/db/shorts_eval.sqlite3")
    conn.execute(
        "INSERT INTO clip_runs (run_id,source_id,title,description,transcript,sector) VALUES (?,?,?,?,?,?)",
        (run_id,source_id,title,description,transcript,sector)
    )
    conn.commit()
def generate_title_description(anchor_text: str, transcript: str, short_style: str = "auto", used_titles=None, used_descs=None):
    used_titles = used_titles or []
    used_descs = used_descs or []

    anchor = (anchor_text or "").strip()
    text = (transcript or "").strip()
    tn = norm(anchor + " " + text)

    sector = infer_sector(anchor + " " + text)
    if any(x in tn for x in ["fight", "pvp", "hunter", "hunters", "netherite", "pearl", "trap", "clutch", "killed", "cobweb"]):
        sector = "gaming"

    event_type = detect_event_type(anchor, text, short_style)

    title_candidates = generate_title_candidates(event_type, anchor, text, sector)
    desc_candidates = generate_description_candidates(event_type, anchor, text, sector)

    pairs = []
    for title in title_candidates:
        for desc in desc_candidates:
            pairs.append((title, desc))

    best_title, best_desc = max(
        pairs,
        key=lambda pair: rank_title_desc_pair(pair[0], pair[1], text, used_titles, used_descs)
    )

    return best_title[:80], best_desc[:220], sector

HOOK_WORDS = {"what", "wait", "why", "how", "bro", "nah", "no way", "trap", "fight", "hunters", "clutch", "pearl", "destroyed"}
TURN_WORDS = {"but", "then", "until", "however", "except", "suddenly", "instead", "almost", "finally", "because"}

def style_bonus(short_style: str, anchor_text: str, transcript: str) -> float:
    t = norm((anchor_text or "") + " " + (transcript or ""))
    score = 0.0
    if short_style in ("auto", "destroy"):
        for w in ["destroy", "destroyed", "smoked", "rolled", "deleted", "won", "killed", "fight"]:
            if w in t:
                score += 0.18
    if short_style in ("auto", "clutch"):
        for w in ["clutch", "survived", "escape", "last second", "pearl"]:
            if w in t:
                score += 0.18
    if short_style in ("auto", "trap"):
        for w in ["trap", "bait", "lured", "fell for", "stasis"]:
            if w in t:
                score += 0.18
    if short_style in ("auto", "fail"):
        for w in ["failed", "throw", "missed", "fell", "choked", "oops"]:
            if w in t:
                score += 0.18
    if short_style in ("auto", "reveal"):
        for w in ["found out", "realized", "revealed", "truth", "actually"]:
            if w in t:
                score += 0.16
    return min(score, 0.36)

def novelty_score(text: str, olds: list[str]) -> float:
    t = norm(text)
    if not olds:
        return 1.0
    sims = []
    ws = set(t.split())
    for o in olds[-50:]:
        os = set(norm(o).split())
        if not ws or not os:
            continue
        sims.append(len(ws & os) / max(1, len(ws | os)))
    if not sims:
        return 1.0
    return max(0.0, 1.0 - max(sims))

def score_clip(text: str, dur: float, olds: list[str], rel: float, short_style: str = "auto") -> float:
    first = norm(" ".join(text.split()[:12]))
    hook = 0.24 + min(0.44, sum(1 for x in HOOK_WORDS if x in first) * 0.09)
    arc = 0.85 if any(x in norm(text) for x in TURN_WORDS) else 0.30
    pace = 1.0 if 2.1 <= (len(text.split()) / max(dur, 0.1)) <= 3.6 else 0.50
    novelty = novelty_score(text, olds)
    return round(min(1.0, hook*0.30 + arc*0.22 + pace*0.16 + novelty*0.10 + rel*0.10 + style_bonus(short_style, first, text)*0.40), 4)

def choose_candidates(words, segments, dur, count, explore, old, seed, variant, short_style="auto"):
    rng = random.Random(seed)
    lengths = [18.0, 20.0, 22.0, 24.0, 26.0, 28.0]
    candidates = []

    for seg in segments:
        text = (seg.get("text") or "").strip()
        if len(text.split()) < 8:
            continue
        a0 = float(seg["start"])
        for L in lengths:
            a = max(0.0, a0 - 2.0)
            b = min(dur, a + L)
            chunk_words = [w for w in words if a <= w["start"] <= b]
            transcript = " ".join(w["word"] for w in chunk_words).strip() if chunk_words else text
            if len(transcript.split()) < 10:
                transcript = text
            rel = 0.5
            if any(x in norm(transcript) for x in ["fight", "hunters", "trap", "clutch", "pearl", "netherite", "destroy"]):
                rel = 0.8
            sc = score_clip(transcript, b-a, old, rel, short_style) + rng.random() * explore * 0.06
            anchor = text[:180]
            candidates.append({
                "variant": variant,
                "start": round(a, 3),
                "end": round(b, 3),
                "title": anchor[:80],
                "anchor_text": anchor,
                "transcript": transcript,
                "score": round(sc, 4),
                "relevance": rel
            })

    candidates.sort(key=lambda x: x["score"], reverse=True)

    chosen = []
    used = []
    for c in candidates:
        t = norm(c["transcript"])
        if any(len(set(t.split()) & set(norm(u).split())) / max(1, len(set(t.split()) | set(norm(u).split()))) > 0.55 for u in used):
            continue
        chosen.append(c)
        used.append(c["transcript"])
        if len(chosen) >= count:
            break
    return chosen

def render(video: Path, a: float, b: float, title: str, outdir: Path, idx: int, variant: str):
    raw = outdir / f"{idx:02d}_{variant}_raw.mp4"
    final = outdir / f"{idx:02d}_{variant}_{slug(title)}_ultimate.mp4"

    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "eq=contrast=1.03:saturation=1.06:brightness=0.01,"
        "unsharp=5:5:0.6:5:5:0.0,"
        "format=yuv420p"
    )

    sh([
        "ffmpeg","-y",
        "-ss", str(a), "-to", str(b), "-i", str(video),
        "-vf", vf,
        "-af", "loudnorm=I=-16:LRA=11:TP=-1.5",
        "-c:v", "libx264", "-preset", "slow", "-crf", "19",
        "-c:a", "aac", "-b:a", "192k",
        str(raw)
    ])

    shutil.copy2(raw, final)
    return final

def review(run_id, items):
    WEB.mkdir(parents=True, exist_ok=True)
    cards = []
    for x in items:
        cards.append(f"""<article class="card">
<div class="badge">{x['index']:02d} · {html.escape(x.get('variant','A'))}</div>
<h2>{html.escape(x['title'])}</h2>
<div class="meta">
  <span>score: {x['score']:.3f}</span>
  <span>relevance: {float(x.get('relevance',0.0)):.3f}</span>
  <span>range: {x['start']:.2f}→{x['end']:.2f}</span>
</div>
<video controls preload="metadata" playsinline src="{html.escape(x['video_url'])}"></video>
<p><strong>Sector:</strong> {html.escape(x.get('sector','auto'))}</p>
<p><strong>Description:</strong><br>{html.escape((x.get('description') or '-')[:320])}</p>
<p><strong>Anchor from source video:</strong><br>{html.escape((x.get('anchor_text') or '-')[:220])}</p>
<p><strong>Clip transcript:</strong><br>{html.escape(x['transcript'][:240])}</p>
<p><a href="{html.escape(x['download_url'])}" download>Download clip</a></p>
</article>""")
    page = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ShortForge Review</title><style>
body{{margin:0;background:#0b1118;color:#e8edf3;font-family:-apple-system,BlinkMacSystemFont,sans-serif}}
.wrap{{max-width:1440px;margin:0 auto;padding:24px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:18px}}
.card{{background:#121922;border:1px solid #223142;border-radius:18px;padding:16px}}
.badge{{display:inline-block;background:#1e2a38;padding:4px 10px;border-radius:999px;font-size:12px;margin-bottom:8px}}
video{{width:100%;border-radius:14px;background:#000}}
.meta{{display:flex;gap:10px;flex-wrap:wrap;font-size:12px;opacity:.9;margin-bottom:12px}}
a{{color:#8ec5ff}}
</style></head><body><div class="wrap"><h1>ShortForge Review · {html.escape(run_id)}</h1><div class="grid">{''.join(cards)}</div></div></body></html>"""
    (WEB / "index.html").write_text(page, encoding="utf-8")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--count", type=int, default=10)
    ap.add_argument("--explore", type=float, default=0.55)
    ap.add_argument("--source-id", default="")
    ap.add_argument("--short-style", default="auto", choices=["auto","destroy","clutch","trap","fail","funny","reveal"])
    args = ap.parse_args()

    video = Path(args.video).resolve()
    if not video.exists():
        raise SystemExit(f"missing video: {video}")

    run_id = f"mythiq_shorts_{int(time.time())}"
    root = Path("artifacts/shorts_meta") / run_id
    meta = root / "meta"
    renders = root / "ultimate" / "renders"
    web_media = WEB / "media" / run_id
    meta.mkdir(parents=True, exist_ok=True)
    renders.mkdir(parents=True, exist_ok=True)
    web_media.mkdir(parents=True, exist_ok=True)

    c = db()
    old = prev_texts(c, args.source_id)

    tx = transcribe(video, meta / "transcript.json")
    dur = ff_duration(video)
    words = tx.get("words", [])
    segs = tx.get("segments", [])

    seedA = int(time.time()) % 100000
    seedB = seedA + 17

    chosenA = choose_candidates(words, segs, dur, max(1, args.count // 2), args.explore, old, seedA, "A", args.short_style)
    chosenB = choose_candidates(words, segs, dur, args.count - len(chosenA), min(0.85, args.explore + 0.15), old + [x["transcript"] for x in chosenA], seedB, "B", args.short_style)
    chosen = chosenA + chosenB

    items = []
    used_titles = set()

    for i, x in enumerate(chosen, 1):
        final = render(video, x["start"], x["end"], x["title"], renders, i, x.get("variant", "A"))
        shutil.copy2(final, web_media / final.name)

        generated_title, generated_description, sector = generate_title_description(
            x.get("anchor_text", ""),
            x["transcript"],
            args.short_style,
            list(used_titles),
            [it.get("description","") for it in items]
        )

        base_title = generated_title
        n = 2
        while generated_title in used_titles:
            generated_title = f"{base_title} #{n}"
            n += 1
        used_titles.add(generated_title)

        c.execute(
            "INSERT INTO exports(source_id,run_id,variant,start,end,title,transcript,anchor_text,score,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (args.source_id, run_id, x.get("variant","A"), x["start"], x["end"], generated_title, x["transcript"], x.get("anchor_text",""), x["score"], time.time())
        )

        items.append({
            "index": i,
            "variant": x.get("variant", "A"),
            "title": generated_title,
            "description": generated_description,
            "sector": sector,
            "start": x["start"],
            "end": x["end"],
            "score": x["score"],
            "relevance": x.get("relevance", 0.0),
            "anchor_text": x.get("anchor_text", ""),
            "video_url": f"media/{run_id}/{final.name}",
            "download_url": f"media/{run_id}/{final.name}",
            "transcript": x["transcript"]
        })

    c.commit()
    (meta / "export_candidates.json").write_text(json.dumps(items, indent=2), encoding="utf-8")
    (WEB / "shorts_index.json").write_text(json.dumps(items, indent=2), encoding="utf-8")
    review(run_id, items)

    print(json.dumps({
        "ok": True,
        "run_id": run_id,
        "count": len(items),
        "review_page": "http://127.0.0.1:8788/web/shorts_review/"
    }, indent=2))

if __name__ == "__main__":
    main()
