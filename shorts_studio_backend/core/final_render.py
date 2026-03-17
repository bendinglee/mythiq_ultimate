from __future__ import annotations

import subprocess


def _ffmpeg_supports_subtitles_filter() -> bool:
    try:
        r = subprocess.run(
            ["ffmpeg", "-hide_banner", "-filters"],
            capture_output=True,
            text=True,
            check=False,
        )
        out = (r.stdout or "") + "\n" + (r.stderr or "")
        return (" subtitles " in out) or (" ass " in out)
    except Exception:
        return False

from pathlib import Path


def _escape_subtitles_path(path: str) -> str:
    p = str(Path(path).resolve())
    p = p.replace("\\", "\\\\")
    p = p.replace(":", r"\:")
    p = p.replace(",", r"\,")
    p = p.replace("[", r"\[")
    p = p.replace("]", r"\]")
    p = p.replace("'", r"\'")
    return p


def write_ass(subs, out_path: str) -> str:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "",
        "[V4+ Styles]",
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
        "Style: Default,Arial,72,&H00FFFFFF,&H0000FFFF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,4,0,2,80,80,140,1",
        "",
        "[Events]",
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
    ]

    def ts(x: float) -> str:
        h = int(x // 3600)
        m = int((x % 3600) // 60)
        s = int(x % 60)
        cs = int(round((x - int(x)) * 100))
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    for sub in subs:
        text = str(sub["text"]).replace("\n", " ").replace("{", r"\{").replace("}", r"\}")
        lines.append(
            f"Dialogue: 0,{ts(float(sub['start']))},{ts(float(sub['end']))},Default,,0,0,0,,{text}"
        )

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(out)


def render_final(src: str, start: float, end: float, out_path: str, mode: str = "tiktok_4k", ass_path: str | None = None) -> dict:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if mode == "tiktok_4k":
        scale_chain = "scale=2160:3840:force_original_aspect_ratio=decrease,pad=2160:3840:(ow-iw)/2:(oh-ih)/2,fps=30"
        crf = "18"
        preset = "slow"
    else:
        scale_chain = "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,fps=30"
        crf = "20"
        preset = "medium"

    use_burned_subs = bool(ass_path) and _ffmpeg_supports_subtitles_filter()

    if use_burned_subs:
        escaped = _escape_subtitles_path(ass_path)
        filter_chain = f"{scale_chain},subtitles=filename='{escaped}'"
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-to", str(end),
            "-i", str(src),
            "-vf", filter_chain,
            "-map", "0:v:0",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", preset,
            "-crf", crf,
            "-c:a", "aac",
            "-b:a", "192k",
            str(out),
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-to", str(end),
            "-i", str(src),
            "-vf", scale_chain,
            "-c:v", "libx264",
            "-preset", preset,
            "-crf", crf,
            "-c:a", "aac",
            "-b:a", "192k",
            str(out),
        ]

    subprocess.run(cmd, check=True)
    return {
        "final_path": str(out),
        "burn_captions_requested": bool(ass_path),
        "burn_captions_applied": bool(use_burned_subs),
        "warning": None if (not ass_path or use_burned_subs) else "ffmpeg build does not support subtitles filter; rendered without burned captions",
    }
