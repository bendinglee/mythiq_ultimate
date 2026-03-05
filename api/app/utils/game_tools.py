from __future__ import annotations
from pathlib import Path
import shutil

CANON_REL = Path("tools/canonical_game_tools")

def enforce_canonical_game_tools(repo_dir: str | Path, project_root: str | Path) -> None:
    repo_dir = Path(repo_dir)
    project_root = Path(project_root)

    canon = (project_root / CANON_REL).resolve()
    if not canon.is_dir():
        raise FileNotFoundError(f"missing canonical tools dir: {canon}")

    tools_dir = repo_dir / "tools"
    if not tools_dir.is_dir():
        raise FileNotFoundError(f"generated repo missing tools/: {tools_dir}")

    for name in ("ai_auto_pick.mjs", "ai_save_variants.mjs", "ai_gen_variants.mjs"):
        src = canon / name
        if not src.is_file():
            raise FileNotFoundError(f"missing canonical tool: {src}")
        dst = tools_dir / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
