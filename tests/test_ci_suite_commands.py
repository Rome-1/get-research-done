from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_ci_workflow_runs_fast_and_full_pytest_suites_with_call_site_xdist_flags() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "Run fast test suite" in workflow
    assert "uv run pytest tests/ -q -n auto --dist=loadscope" in workflow
    assert "Run full test suite" in workflow
    assert "uv run pytest tests/ -q --full-suite -n auto --dist=loadscope" in workflow
    assert 'addopts = "-n auto --dist=loadscope"' not in pyproject


def test_tests_readme_documents_fast_and_full_suite_entrypoints() -> None:
    tests_readme = (REPO_ROOT / "tests" / "README.md").read_text(encoding="utf-8")

    assert "Default `uv run pytest tests/ -q` uses the fast daily suite declared in" in tests_readme
    assert "`uv run pytest tests/ -q -n auto --dist=loadscope`" in tests_readme
    assert "`uv run pytest tests/ -q --full-suite -n auto --dist=loadscope`" in tests_readme
    assert "parallel flags now live at the call site instead of repo config" in tests_readme
    assert "The GitHub Actions workflow runs both fast and full suites explicitly." in tests_readme
