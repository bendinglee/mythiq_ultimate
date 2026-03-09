from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

PROJECTS = Path("projects")

KNOWN_FEATURES = ("text", "code", "docs", "shorts", "image", "game", "animation")


def _all_files(root: Path) -> List[str]:
    return [str(p) for p in sorted(root.rglob("*")) if p.is_file()]


def _detect_feature(root: Path, files: List[str]) -> str:
    rp = str(root)

    # direct generated bundle roots like projects/code_xxx, docs_xxx, etc.
    for feat in KNOWN_FEATURES:
        if f"/{feat}_" in rp or Path(rp).name.startswith(f"{feat}_"):
            return feat

    joined = "\n".join(files)

    checks = [
        ("code", ["/generated/code/", "/codegen/", "main.py", "test_main.py"]),
        ("docs", ["/generated/docs/", "/docsgen/", "OUTLINE.md", "SUMMARY.md", "document_blueprint"]),
        ("shorts", ["/generated/shorts/", "/shortsgen/", "HOOKS.md", "edit_plan.json", "shorts_blueprint"]),
        ("image", ["/generated/image/", "/imagegen/", "storyboard.json", "render_plan.json", "image_prompt_package"]),
        ("game", ["/generated/game/", "/builder_scaffold/", "/gamegen/", "game_config.json", "index.html"]),
        ("animation", ["/generated/animation/", "/animationgen/", "SHOT_LIST.md", "scene_beats.json", "animation_prompt_package"]),
        ("text", ["/generated/text/", "/textgen/", "response.txt", "summary.md"]),
    ]

    for feat, needles in checks:
        if any(n in joined for n in needles):
            return feat

    return "unknown"


def list_artifacts(limit: int = 100) -> Dict[str, Any]:
    PROJECTS.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    for root in sorted(PROJECTS.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not root.is_dir():
            continue
        if root.name.startswith("."):
            continue
        if root.name == "_exports":
            continue

        files = _all_files(root)
        rows.append(
            {
                "artifact_id": root.name,
                "feature": _detect_feature(root, files),
                "root": str(root),
                "files": files,
            }
        )

        if len(rows) >= limit:
            break

    return {
        "ok": True,
        "count": len(rows),
        "artifacts": rows,
    }
