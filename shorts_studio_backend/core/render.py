import subprocess
from pathlib import Path

def render_preview(src, clip, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{clip['name']}.mp4"

    cmd = [
        "ffmpeg","-y",
        "-ss", str(clip["start"]),
        "-to", str(clip["end"]),
        "-i", src,
        "-vf", "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2",
        "-c:v","libx264","-preset","veryfast","-crf","28",
        "-an",
        str(out)
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return str(out)
