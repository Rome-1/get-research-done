from __future__ import annotations

import ast
from pathlib import Path

import tests.conftest as tests_conftest

REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_ROOT = REPO_ROOT / "tests"
TOP_LEVEL_CONFTEST = TESTS_ROOT / "conftest.py"


def _assigned_literal(path: Path, *, name: str) -> object | None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        value_node: ast.AST | None = None
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                value_node = node.value
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == name:
                value_node = node.value
        if value_node is not None:
            return ast.literal_eval(value_node)
    return None


def test_top_level_conftest_does_not_filter_default_collection() -> None:
    top_level_text = TOP_LEVEL_CONFTEST.read_text(encoding="utf-8")

    assert not hasattr(tests_conftest, "FAST_SUITE_EXCLUDES")
    assert not hasattr(tests_conftest, "pytest_ignore_collect")
    assert "FAST_SUITE_EXCLUDES" not in top_level_text
    assert "--full-suite" not in top_level_text
    assert "GPD_TEST_FULL" not in top_level_text
    assert "pytest_ignore_collect" not in top_level_text


def test_nested_test_conftests_do_not_hide_suites_via_collect_ignore() -> None:
    offenders: list[str] = []

    for path in sorted(TESTS_ROOT.rglob("conftest.py")):
        if path == TOP_LEVEL_CONFTEST:
            continue
        if _assigned_literal(path, name="collect_ignore") is not None:
            offenders.append(str(path.relative_to(REPO_ROOT)))

    assert offenders == []
