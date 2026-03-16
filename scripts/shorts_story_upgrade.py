#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

# ---------- helpers ----------

def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)

def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")

def clean_text(s: str) -> str:
    s = re.sub(r"\s+", " ", (s or "")).strip()
    s = s.replace("unstable s p", "Unstable SMP")
    return s

def find_latest_final_metadata() -> Path:
    cands = list(Path("artifacts").glob("shorts_*/semantic_upgrade/finalized/meta/final_metadata.json"))
    if not cands:
        raise SystemExit("No finalized meta found under artifacts/shorts_*/semantic_upgrade/finalized/meta/final_metadata.json")
    return max(cands, key=lambda p: p.stat().st_mtime)

def ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path)
    ], text=True).strip()
    return float(out)

# ---------- transcript discovery ----------

@dataclass
class Segment:
    start: float
    end: float
    text: str

def _float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default

def _iter_any_segments(obj: Any) -> Iterable[Segment]:
    if isinstance(obj, list):
        for item in obj:
            yield from _iter_any_segments(item)
        return

    if not isinstance(obj, dict):
        return

    # direct segment shape
    keys = {k.lower() for k in obj.keys()}
    if (
        ("start" in keys or "start_time" in keys or "begin" in keys)
        and ("end" in keys or "end_time" in keys or "finish" in keys)
        and ("text" in keys or "caption" in keys or "transcript" in keys or "content" in keys)
    ):
        start = _float(obj.get("start", obj.get("start_time", obj.get("begin", 0.0))))
        end = _float(obj.get("end", obj.get("end_time", obj.get("finish", start + 1.0))))
        text = clean_text(
            obj.get("text")
            or obj.get("caption")
            or obj.get("transcript")
            or obj.get("content")
            or ""
        )
        if end > start and text:
            yield Segment(start, end, text)

    # nested containers
    for v in obj.values():
        if isinstance(v, (list, dict)):
            yield from _iter_any_segments(v)

def discover_segments(root: Path) -> list[Segment]:
    import json

    def _clean_text(x) -> str:
        return " ".join(str(x).replace("\n", " ").split()).strip()

    def _to_float(x):
        try:
            return float(x)
        except Exception:
            return None

    def _to_segment(row):
        if not isinstance(row, dict):
            return None
        start = _to_float(row.get("start"))
        end = _to_float(row.get("end"))
        text = _clean_text(row.get("text", ""))
        if start is None or end is None or end <= start or not text:
            return None
        return Segment(start=start, end=end, text=text)

    candidates = []

    tjson = root / "transcript" / "transcript.json"
    if tjson.exists():
        candidates.append(tjson)

    for pth in sorted(root.rglob("*.json")):
        if pth not in candidates:
            candidates.append(pth)

    segs: list[Segment] = []

    for pth in candidates:
        try:
            obj = json.loads(pth.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue

        if isinstance(obj, list):
            for row in obj:
                seg = _to_segment(row)
                if seg:
                    segs.append(seg)
            continue

        if isinstance(obj, dict):
            for key in ("segments", "items", "captions", "subtitles", "words", "results"):
                val = obj.get(key)
                if isinstance(val, list):
                    for row in val:
                        seg = _to_segment(row)
                        if seg:
                            segs.append(seg)

    deduped: list[Segment] = []
    seen = set()
    for seg in sorted(segs, key=lambda x: (x.start, x.end, x.text)):
        key = (round(seg.start, 2), round(seg.end, 2), seg.text[:120])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(seg)

    print(f"DISCOVER_SEGMENTS_OK count={len(deduped)} root={root}")
    return deduped

STOP = {
    "the","a","an","and","or","but","is","are","was","were","to","of","for","in","on","at",
    "with","this","that","it","its","into","from","up","out","you","your","we","they","he",
    "she","them","his","her","i","me","my","our","ours","their","theirs"
}

HOOK_WORDS = {
    "wait","no","what","why","whoa","finally","crazy","insane","dude","bro","oh","god",
    "king","fight","mace","legendary","nether","labyrinth","armored","cannot","refuse"
}

PAYOFF_WORDS = {
    "won","lost","mine","belongs","final","finally","ready","killed","fight","king","mace",
    "legendary","escape","armor","armored","tournament"
}

def tokenize(s: str) -> list[str]:
    import re
    return [w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP]

def score_segment(seg: Segment, creator: str, topic: str, raw_event: str, title: str, total_dur: float) -> float:
    text = seg.text.lower()
    toks = set(tokenize(f"{creator} {topic} {raw_event} {title}"))

    score = 0.0

    for t in toks:
        if t and t in text:
            score += 2.5

    for w in HOOK_WORDS:
        if w in text:
            score += 1.25

    for w in PAYOFF_WORDS:
        if w in text:
            score += 1.0

    dur = max(0.2, seg.end - seg.start)
    if 1.0 <= dur <= 4.2:
        score += 1.5
    elif dur <= 6.0:
        score += 0.5

    pos = seg.start / max(total_dur, 1.0)
    if pos <= 0.20:
        score += 0.8
    elif pos <= 0.55:
        score += 0.5

    if "!" in seg.text or "?" in seg.text:
        score += 0.5

    return score

def pick_story_segments(segments: list[Segment], creator: str, topic: str, raw_event: str, title: str, total_dur: float) -> list[Segment]:
    if not segments:
        return []

    ranked = sorted(
        segments,
        key=lambda s: score_segment(s, creator, topic, raw_event, title, total_dur),
        reverse=True,
    )

    selected: list[Segment] = []
    min_gap = 6.0

    def far_enough(seg: Segment) -> bool:
        for x in selected:
            if abs(seg.start - x.start) < min_gap:
                return False
        return True

    # 1) best hook from earlier half if possible
    early = [s for s in ranked if s.start <= total_dur * 0.55]
    if early:
        selected.append(early[0])
    else:
        selected.append(ranked[0])

    # 2) best setup/escalation/payoff from distinct places
    for band_start, band_end in [(0.15, 0.50), (0.45, 0.80), (0.70, 1.01)]:
        band = [s for s in ranked if total_dur * band_start <= s.start <= total_dur * band_end and far_enough(s)]
        if band:
            selected.append(band[0])

    # 3) fill to 4 beats if needed
    for s in ranked:
        if len(selected) >= 4:
            break
        if far_enough(s):
            selected.append(s)

    selected = sorted(selected, key=lambda s: s.start)

    # Make first beat the strongest hook even if later in timeline by moving it first
    if selected:
        best = max(selected, key=lambda s: score_segment(s, creator, topic, raw_event, title, total_dur))
        selected.remove(best)
        selected = [best] + selected

    return selected[:4]

# ---------- subtitle generation ----------

def srt_ts(sec: float) -> str:
    sec = max(0.0, sec)
    ms = int(round((sec - int(sec)) * 1000))
    total = int(sec)
    s = total % 60
    m = (total // 60) % 60
    h = total // 3600
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def build_srt(beats: list[dict[str, Any]], out_path: Path) -> None:
    lines = []
    n = 1
    t = 0.0
    for beat in beats:
        dur = float(beat["out_end"]) - float(beat["out_start"])
        txt = clean_text(beat["text"])
        if not txt:
            continue
        # break long captions into two chunks max
        parts = re.split(r"(?<=[.!?])\s+", txt)
        if len(parts) == 1 and len(txt) > 70:
            words = txt.split()
            mid = max(1, len(words)//2)
            parts = [" ".join(words[:mid]), " ".join(words[mid:])]
        part_dur = dur / max(1, len(parts))
        cur = t
        for part in parts[:2]:
            part = clean_text(part)
            if not part:
                continue
            lines.append(str(n))
            lines.append(f"{srt_ts(cur)} --> {srt_ts(cur + part_dur)}")
            lines.append(part)
            lines.append("")
            n += 1
            cur += part_dur
        t += dur
    out_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")

# ---------- ffmpeg rendering ----------

def make_segment(src: Path, dst: Path, start: float, end: float) -> None:
    dur = max(0.3, end - start)

    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "eq=contrast=1.12:saturation=1.18:brightness=0.02,"
        "unsharp=5:5:0.6:5:5:0.0"
    )

    af = "loudnorm=I=-16:TP=-1.5:LRA=9"

    run([
        "ffmpeg", "-y",
        "-ss", f"{start:.3f}",
        "-t", f"{dur:.3f}",
        "-i", str(src),
        "-vf", vf,
        "-af", af,
        "-r", "30",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "19",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(dst),
    ])

def concat_mp4s(inputs: list[Path], out_path: Path, workdir: Path) -> None:
    list_file = workdir / "concat.txt"
    list_file.write_text("".join(f"file '{p.resolve()}'\n" for p in inputs), encoding="utf-8")
    run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(out_path),
    ])

def burn_subtitles(video_path: Path, srt_path: Path, out_path: Path) -> None:
    import shutil

    out_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(video_path, out_path)

    sidecar = out_path.with_suffix(".srt")
    shutil.copy2(srt_path, sidecar)

    print(f"SUBTITLE_SIDECAR_OK video={out_path} srt={sidecar}")

def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="")
    args = ap.parse_args()

    meta_path = None
    if args.root:
        artifact_root = Path(args.root)
        finalized_meta_dir = artifact_root / "meta"
        finalized_meta_dir.mkdir(parents=True, exist_ok=True)

        selected_json = finalized_meta_dir / "selected.json"
        edit_plan_json = finalized_meta_dir / "edit_plan.json"
        quality_json = finalized_meta_dir / "quality.json"

        if quality_json.exists():
            final_rows = read_json(quality_json)
        elif edit_plan_json.exists():
            final_rows = read_json(edit_plan_json)
        elif selected_json.exists():
            final_rows = read_json(selected_json)
        else:
            raise SystemExit(f"Missing selected/edit_plan/quality json in {finalized_meta_dir}")

    else:
        meta_path = find_latest_final_metadata()
        if not meta_path:
            raise SystemExit("No shorts metadata found")

        finalized_meta_dir = meta_path.parent
        finalized_dir = finalized_meta_dir.parent
        semantic_upgrade_dir = finalized_dir.parent
        artifact_root = semantic_upgrade_dir.parent
        final_rows = read_json(meta_path)

    original = artifact_root / "source" / "original.mp4"
    if not original.exists():
        raise SystemExit(f"Missing original source video: {original}")

    total_dur = ffprobe_duration(original)
    print(f"USING_SHORTS_ROOT {artifact_root}")
    all_segments = discover_segments(artifact_root)
    if not all_segments:
        print("WARN: no transcript segments found; subtitle/recut quality will be limited")

    if args.root:
        out_dir = artifact_root / "ultimate"
    else:
        out_dir = semantic_upgrade_dir / "ultimate"

    renders_dir = out_dir / "renders"
    meta_out = out_dir / "meta"
    renders_dir.mkdir(parents=True, exist_ok=True)
    meta_out.mkdir(parents=True, exist_ok=True)

    plan_rows = []

    for row in final_rows:
        idx = int(row.get("index", len(plan_rows) + 1))
        creator = row.get("creator", "")
        topic = row.get("topic", "")
        raw_event = row.get("raw_event", "")
        title = row.get("title", row.get("hook", ""))
        desc = row.get("description", row.get("text", ""))

        beats = pick_story_segments(all_segments, creator, topic, raw_event, title, total_dur)

        if not beats:
            src_fallback = Path(row.get("hook_video") or row.get("enhanced_video") or "")
            if not src_fallback.exists():
                print(f"SKIP {idx:02d}: no beats and no fallback video")
                continue
            polished = renders_dir / f"short_{idx:02d}_ultimate.mp4"
            shutil.copy2(src_fallback, polished)
            plan_rows.append({
                "index": idx,
                "title": title,
                "creator": creator,
                "topic": topic,
                "mode": "fallback_copy",
                "output_video": str(polished),
                "beats": [],
            })
            continue

        with tempfile.TemporaryDirectory(prefix=f"shorts_upgrade_{idx:02d}_") as td:
            td_path = Path(td)
            pieces = []
            beat_rows = []
            out_cursor = 0.0

            for n, seg in enumerate(beats, 1):
                s = max(0.0, seg.start - 0.08)
                e = min(total_dur, seg.end + 0.08)
                if e - s > 3.2:
                    e = s + 4.2
                if e - s < 0.8:
                    e = min(total_dur, s + 1.0)

                piece = td_path / f"piece_{n:02d}.mp4"
                make_segment(original, piece, s, e)
                pieces.append(piece)

                beat_rows.append({
                    "beat": n,
                    "src_start": s,
                    "src_end": e,
                    "out_start": out_cursor,
                    "out_end": out_cursor + (e - s),
                    "text": seg.text.upper(),
                })
                out_cursor += (e - s)

            concat_path = td_path / "concat.mp4"
            concat_mp4s(pieces, concat_path, td_path)

            srt_path = td_path / "subs.srt"
            build_srt(beat_rows, srt_path)

            polished = renders_dir / f"short_{idx:02d}_ultimate.mp4"
            burn_subtitles(concat_path, srt_path, polished)

            plan_rows.append({
                "index": idx,
                "title": title,
                "creator": creator,
                "topic": topic,
                "raw_event": raw_event,
                "description": desc,
                "output_video": str(polished),
                "beats": beat_rows,
            })

            print(f"ULTIMATE_OK {idx:02d} -> {polished}")

    write_json(meta_out / "storyline_plan.json", plan_rows)
    print("WROTE", meta_out / "storyline_plan.json")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
