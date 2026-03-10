from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from faster_whisper import WhisperModel

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "artifacts"


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def mkdir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def job_dir(prefix: str = "shorts") -> Path:
    jid = f"{prefix}_{uuid.uuid4().hex[:12]}"
    p = ART / jid
    mkdir(p / "source")
    mkdir(p / "transcript")
    mkdir(p / "moments")
    mkdir(p / "renders")
    mkdir(p / "captions")
    mkdir(p / "thumbs")
    return p


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def probe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    ).strip()
    return float(out)


def cache_dir() -> Path:
    p = ART / "_cache" / "sources"
    p.mkdir(parents=True, exist_ok=True)
    return p


def url_key(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]



def cached_transcript_path(url: str) -> Path:
    return cache_dir() / f"{url_key(url)}.transcript.json"

def cached_ranked_path(url: str, target_count: int) -> Path:
    return cache_dir() / f"{url_key(url)}.ranked_{target_count}.json"

def cached_source_path(url: str) -> Path:
    return cache_dir() / f"{url_key(url)}.mp4"


def download_source(url: str, out_template: Path) -> Path:
    cache_mp4 = cached_source_path(url)
    out = out_template.with_suffix(".mp4")

    if cache_mp4.exists():
        shutil.copy2(cache_mp4, out)
        return out

    template = str(out_template.with_suffix(".%(ext)s"))
    run([
        "yt-dlp",
        "-f", "mp4/bestvideo+bestaudio/best",
        "-o", template,
        url,
    ])

    matches = sorted(out_template.parent.glob(out_template.stem + ".*"))
    if not matches:
        raise RuntimeError("download_source: no downloaded file found")

    src = matches[0]
    if src.suffix.lower() != ".mp4":
        converted = out_template.with_suffix(".mp4")
        run([
            "ffmpeg", "-y",
            "-i", str(src),
            "-c", "copy",
            str(converted),
        ])
        src = converted

    shutil.copy2(src, cache_mp4)
    if src != out:
        shutil.copy2(src, out)
        return out
    return src


def extract_audio(src: Path, wav: Path) -> None:
    run([
        "ffmpeg", "-y",
        "-i", str(src),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        str(wav),
    ])


def transcribe_audio(wav: Path) -> dict[str, Any]:
    t0 = time.time()
    model = WhisperModel("base", compute_type="int8")
    segments, info = model.transcribe(str(wav), beam_size=5, vad_filter=True)

    out_segments: list[dict[str, Any]] = []
    full_text: list[str] = []

    for seg in segments:
        text = (seg.text or "").strip()
        if not text:
            continue
        out_segments.append({
            "start": round(float(seg.start), 2),
            "end": round(float(seg.end), 2),
            "text": text,
        })
        full_text.append(text)

    return {
        "text": " ".join(full_text).strip(),
        "segments": out_segments,
        "language": getattr(info, "language", None),
        "duration_sec": out_segments[-1]["end"] if out_segments else 0.0,
        "transcribe_elapsed_sec": round(time.time() - t0, 2),
    }


def rank_moments_from_transcript(
    transcript_data: dict[str, Any],
    total_duration: float,
    target_count: int,
) -> list[dict[str, Any]]:
    segments = transcript_data.get("segments", []) or []
    if not segments or total_duration <= 0:
        return []

    window_size = 30.0
    step = 15.0
    start = 0.0
    windows: list[dict[str, Any]] = []

    keyword_bank = [
        "big", "danger", "fight", "war", "largest", "strong", "trapped",
        "lost", "found", "chased", "crazy", "insane", "secret", "legendary",
        "attack", "final", "escape", "run", "king", "death"
    ]

    while start < total_duration:
        end = min(total_duration, start + window_size)
        chunk = []

        for seg in segments:
            seg_start = float(seg.get("start", 0.0))
            seg_end = float(seg.get("end", 0.0))
            if seg_end > start and seg_start < end:
                chunk.append(seg)

        if not chunk:
            start += step
            continue

        text = " ".join((seg.get("text") or "").strip() for seg in chunk).strip()
        words = [w for w in re.split(r"\s+", text) if w]

        speech_seconds = sum(
            max(0.0, min(end, float(seg.get("end", 0.0))) - max(start, float(seg.get("start", 0.0))))
            for seg in chunk
        )
        speech_density = speech_seconds / max(1.0, end - start)

        strong = 0
        lower_text = text.lower()
        matched_keywords = []
        for kw in keyword_bank:
            if kw in lower_text:
                strong += 1
                matched_keywords.append(kw)

        hook_score = min(1.0, strong / 3.0)
        clarity_score = min(1.0, len(words) / 80.0)
        density_score = min(1.0, speech_density)

        score = (
            0.45 * hook_score +
            0.30 * density_score +
            0.25 * clarity_score
        )

        if text:
            reason_parts = []
            if hook_score >= 0.8:
                reason_parts.append("strong hook words")
            if density_score >= 0.7:
                reason_parts.append("dense speech")
            if clarity_score >= 0.7:
                reason_parts.append("clear spoken content")
            if matched_keywords:
                reason_parts.append("matched high-interest keywords")

            windows.append({
                "start_sec": round(start, 2),
                "end_sec": round(end, 2),
                "hook_score": round(hook_score, 3),
                "payoff_score": round(clarity_score, 3),
                "clip_score": round(score, 3),
                "speech_density": round(density_score, 3),
                "segment_count": len(chunk),
                "matched_keywords": matched_keywords[:8],
                "transcript_preview": text[:220],
                "reason": ", ".join(reason_parts) if reason_parts else "general transcript strength",
                "title": (text[:80] + "...") if len(text) > 80 else text,
            })

        start += step

    windows.sort(key=lambda x: x["clip_score"], reverse=True)

    picked: list[dict[str, Any]] = []
    for cand in windows:
        overlaps = False
        for chosen in picked:
            if not (cand["end_sec"] <= chosen["start_sec"] or cand["start_sec"] >= chosen["end_sec"]):
                overlaps = True
                break
        if overlaps:
            continue
        picked.append(cand)
        if len(picked) >= target_count:
            break

    for i, item in enumerate(picked, start=1):
        item["rank"] = i

    return picked


def render_vertical_clip(src: Path, dst: Path, start: float, end: float) -> None:
    dur = max(1.0, end - start)
    vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    run([
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", str(src),
        "-t", str(dur),
        "-vf", vf,
        "-r", "30",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        str(dst),
    ])



def fmt_srt_time(sec: float) -> str:
    ms = int(round(sec * 1000))
    h = ms // 3600000
    ms %= 3600000
    m = ms // 60000
    ms %= 60000
    s = ms // 1000
    ms %= 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt_for_clip(
    transcript_data: dict[str, Any],
    clip_start: float,
    clip_end: float,
    out_srt: Path,
) -> int:
    segs = transcript_data.get("segments", []) or []
    lines: list[str] = []
    idx = 1

    for seg in segs:
        a = float(seg.get("start", 0.0))
        b = float(seg.get("end", 0.0))
        text = str(seg.get("text", "")).strip()

        if not text or b <= clip_start or a >= clip_end:
            continue

        sa = max(0.0, a - clip_start)
        sb = max(sa + 0.1, min(clip_end, b) - clip_start)

        lines.append(str(idx))
        lines.append(f"{fmt_srt_time(sa)} --> {fmt_srt_time(sb)}")
        lines.append(text)
        lines.append("")
        idx += 1

    out_srt.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return idx - 1


def burn_subtitles(src_mp4: Path, src_srt: Path, out_mp4: Path) -> bool:
    filters = subprocess.check_output(
        ["ffmpeg", "-hide_banner", "-filters"],
        text=True,
        errors="ignore",
    )

    has_subtitles = " subtitles " in filters or filters.rstrip().endswith("subtitles")
    has_ass = " ass " in filters or filters.rstrip().endswith("ass")
    has_drawtext = " drawtext " in filters or filters.rstrip().endswith("drawtext")

    if not (has_subtitles or has_ass or has_drawtext):
        return False

    rel_srt = src_srt.relative_to(ROOT).as_posix()
    rel_srt = (
        rel_srt
        .replace("\\", r"\\\\")
        .replace(":", r"\:")
        .replace(",", r"\,")
        .replace("[", r"\[")
        .replace("]", r"\]")
    )
    vf = f"subtitles=filename={rel_srt}"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(src_mp4),
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "23",
            "-c:a", "copy",
            str(out_mp4),
        ],
        check=True,
        cwd=str(ROOT),
    )
    return True


def build_shorts(source_url: str, target_count: int = 5) -> dict[str, Any]:
    job = job_dir("shorts")
    jid = job.name

    src_placeholder = job / "source" / "original"
    wav = job / "source" / "audio.wav"
    transcript = job / "transcript" / "transcript.json"
    ranked = job / "moments" / "ranked.json"

    src = download_source(source_url, src_placeholder)
    total_duration = probe_duration(src)

    transcript_cache = cached_transcript_path(source_url)
    ranked_cache = cached_ranked_path(source_url, target_count)

    cache_hit_transcript = False
    cache_hit_rankings = False

    if transcript_cache.exists():
        transcript_data = json.loads(transcript_cache.read_text(encoding="utf-8"))
        cache_hit_transcript = True
    else:
        extract_audio(src, wav)
        transcript_data = transcribe_audio(wav)
        transcript_data["source_duration_sec"] = total_duration
        transcript_cache.parent.mkdir(parents=True, exist_ok=True)
        transcript_cache.write_text(json.dumps(transcript_data, indent=2), encoding="utf-8")

    write_json(transcript, transcript_data)

    if ranked_cache.exists():
        moments = json.loads(ranked_cache.read_text(encoding="utf-8"))
        cache_hit_rankings = True
    else:
        moments = rank_moments_from_transcript(transcript_data, total_duration, target_count)
        ranked_cache.parent.mkdir(parents=True, exist_ok=True)
        ranked_cache.write_text(json.dumps(moments, indent=2), encoding="utf-8")

    write_json(ranked, moments)

    artifacts = [
        {"kind": "source_video", "path": str(src.relative_to(ROOT))},
        {"kind": "transcript", "path": str(transcript.relative_to(ROOT))},
        {"kind": "moments", "path": str(ranked.relative_to(ROOT))},
    ]

    clips_generated = 0
    subtitle_files = 0
    for i, m in enumerate(moments, start=1):
        clip_start = float(m["start_sec"])
        clip_end = float(m["end_sec"])

        out = job / "renders" / f"short_{i:02d}.mp4"
        srt = job / "captions" / f"short_{i:02d}.srt"
        out_captioned = job / "renders" / f"short_{i:02d}.captioned.mp4"

        clip_cache = cached_clip_path(source_url, clip_start, clip_end)
        if clip_cache.exists():
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(clip_cache.read_bytes())
        else:
            render_vertical_clip(src, out, clip_start, clip_end)
            clip_cache.parent.mkdir(parents=True, exist_ok=True)
            clip_cache.write_bytes(out.read_bytes())

        subtitle_count = write_srt_for_clip(transcript_data, clip_start, clip_end, srt)

        artifacts.append({"kind": "short_video", "path": str(out.relative_to(ROOT))})
        artifacts.append({"kind": "subtitle", "path": str(srt.relative_to(ROOT))})

        if subtitle_count > 0:
            burned = burn_subtitles(out, srt, out_captioned)
            if burned and out_captioned.exists():
                artifacts.append({"kind": "short_video_captioned", "path": str(out_captioned.relative_to(ROOT))})
                subtitle_files += 1

        clips_generated += 1

    return {
        "ok": True,
        "job_id": jid,
        "feature": "shorts",
        "status": "done",
        "source": {"url": source_url},
        "artifacts": artifacts,
        "metrics": {
            "critique_score": 0.0,
            "validation_passed": True,
            "clips_generated": clips_generated,
            "duration_sec": total_duration,
            "transcript_segments": len(transcript_data.get("segments", [])),
            "transcribe_elapsed_sec": transcript_data.get("transcribe_elapsed_sec"),
            "subtitle_files": subtitle_files,
            "caption_burn_available": subtitle_files > 0,
            "cache_hit_source": cached_source_path(source_url).exists(),
            "cache_hit_transcript": cache_hit_transcript,
            "cache_hit_rankings": cache_hit_rankings,
            "cache_hit_audio_extract": not cache_hit_transcript,
            "cache_clip_count": sum(
                1 for m in moments
                if cached_clip_path(source_url, float(m["start_sec"]), float(m["end_sec"])).exists()
            ),
        },
        "critic_report": {},
        "logs": [],
    }


def clip_cache_key(url: str, start_sec: float, end_sec: float) -> str:
    return f"{url_key(url)}_{int(round(start_sec * 100))}_{int(round(end_sec * 100))}"

def cached_clip_path(url: str, start_sec: float, end_sec: float) -> Path:
    return cache_dir() / "clips" / f"{clip_cache_key(url, start_sec, end_sec)}.mp4"
