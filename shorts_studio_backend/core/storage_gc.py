from __future__ import annotations
import time
from pathlib import Path

def cleanup_trash(trash_dir: str, ttl_hours: int = 24) -> list[str]:
    now = time.time()
    ttl = ttl_hours * 3600
    removed = []
    root = Path(trash_dir)

    if not root.exists():
        return removed

    for p in root.rglob("*"):
        if p.is_file():
            age = now - p.stat().st_mtime
            if age >= ttl:
                p.unlink(missing_ok=True)
                removed.append(str(p))

    for d in sorted(root.rglob("*"), reverse=True):
        if d.is_dir():
            try:
                d.rmdir()
            except OSError:
                pass

    return removed

def dir_size_bytes(path: str) -> int:
    total = 0
    root = Path(path)
    if not root.exists():
        return 0
    for p in root.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
    return total
