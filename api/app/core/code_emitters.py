from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import hashlib
import re


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return s[:48] or "codegen"


def emit_code_bundle(prompt: str, content: str) -> Dict[str, Any]:
    key = hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:12]
    root = Path("projects") / f"code_{key}" / "codegen" / _slug(prompt)
    root.mkdir(parents=True, exist_ok=True)

    main_py = root / "main.py"
    test_py = root / "test_main.py"
    readme_md = root / "README.md"

    main_py.write_text(content, encoding="utf-8")

    test_py.write_text(
        '''from main import solve

def test_solve_contract():
    out = solve()
    assert isinstance(out, dict)
    assert out.get("ok") is True
''',
        encoding="utf-8",
    )

    readme_md.write_text(
        f"""# Mythiq Code Bundle

## Prompt
{prompt}

## Files
- `main.py` - generated implementation
- `test_main.py` - minimal contract test
- `README.md` - bundle notes
""",
        encoding="utf-8",
    )

    files: List[str] = [str(main_py), str(test_py), str(readme_md)]
    return {
        "root": str(root),
        "files": files,
        "file_count": len(files),
    }
