from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_ci_runs_fast_and_full_pytest_suites_with_call_site_xdist_flags() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "Run fast test suite" in workflow
    assert "uv run pytest tests/ -q -n auto --dist=loadscope" in workflow
    assert "Run full test suite" in workflow
    assert "uv run pytest tests/ -q --full-suite -n auto --dist=loadscope" in workflow
    assert "-n auto --dist=loadscope" not in pyproject
