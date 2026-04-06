from __future__ import annotations

import ast
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _top_level_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
        elif isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
    return imports


def test_adapter_base_does_not_import_registry_at_module_import_time() -> None:
    imports = _top_level_imports(REPO_ROOT / "src" / "gpd" / "adapters" / "base.py")

    assert "gpd.registry" not in imports


def test_registry_import_remains_stable_after_adapter_package_import() -> None:
    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-c",
            "import gpd.adapters.base\nfrom gpd import registry\nprint(hasattr(registry, 'render_command_visibility_sections_from_frontmatter'))",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert result.stdout.strip() == "True"
