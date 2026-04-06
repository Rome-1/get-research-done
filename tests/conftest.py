from __future__ import annotations

import os
from pathlib import Path

_TESTS_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_ROOT.parent
_FAST_SUITE_ENV_VAR = "GPD_TEST_FULL"

# Keep the default suite focused on the fast daily path while still allowing
# explicit runs of heavyweight files and an opt-in full sweep.
FAST_SUITE_EXCLUDES = frozenset(
    {
        "adapters/test_install_roundtrip.py",
        "core/test_cli.py",
        "core/test_cli_install.py",
        "core/test_commands.py",
        "core/test_config.py",
        "core/test_context.py",
        "core/test_contract_validation.py",
        "core/test_conventions.py",
        "core/test_error_recovery.py",
        "core/test_executor_prompt_contract_visibility.py",
        "core/test_extras.py",
        "core/test_frontmatter.py",
        "core/test_frontmatter_edge.py",
        "core/test_git_ops.py",
        "core/test_json_utils.py",
        "core/test_manuscript_artifacts.py",
        "core/test_observability.py",
        "core/test_onboarding_surfaces.py",
        "core/test_paper_quality.py",
        "core/test_paper_quality_artifacts.py",
        "core/test_patterns.py",
        "core/test_phases.py",
        "core/test_plan_contract_prompt_visibility_regressions.py",
        "core/test_project_reentry.py",
        "core/test_query.py",
        "core/test_recovery_advice.py",
        "core/test_referee_policy.py",
        "core/test_result_dependency_workflow_wiring.py",
        "core/test_result_deps_cli.py",
        "core/test_result_search_cli.py",
        "core/test_result_show_cli.py",
        "core/test_results.py",
        "core/test_resume_runtime.py",
        "core/test_review_artifacts.py",
        "core/test_review_validation_commands.py",
        "core/test_roundtrip.py",
        "core/test_runtime_hints.py",
        "core/test_state.py",
        "core/test_state_mutations.py",
        "core/test_state_stress.py",
        "core/test_suggest.py",
        "core/test_workflow_presets.py",
        "hooks/test_check_update.py",
        "hooks/test_notify.py",
        "hooks/test_runtime_detect.py",
        "hooks/test_runtime_lookup.py",
        "hooks/test_statusline.py",
        "hooks/test_todo_resolution.py",
        "hooks/test_update_resolution.py",
        "mcp/test_verification_contract_server_regressions.py",
        "test_bootstrap_installer.py",
        "test_install_lifecycle.py",
        "test_release_consistency.py",
        "test_runtime_cli.py",
        "test_update_workflow.py",
    }
)


def _full_suite_requested(*, cli_flag: bool, env_value: str | None) -> bool:
    if cli_flag:
        return True
    if env_value is None:
        return False
    return env_value.strip().lower() in {"1", "true", "yes", "on"}


def fast_suite_ignored(rel_path: str, *, full_suite: bool, explicitly_requested: bool) -> bool:
    """Return whether one test path belongs to the default fast-suite skip set."""
    return not full_suite and not explicitly_requested and rel_path in FAST_SUITE_EXCLUDES


def _requested_collection_roots(config) -> tuple[Path, ...]:
    invocation = getattr(config, "invocation_params", None)
    args = getattr(invocation, "args", ()) if invocation is not None else ()
    roots: list[Path] = []
    for raw_arg in args:
        if not isinstance(raw_arg, str) or not raw_arg or raw_arg.startswith("-"):
            continue
        candidate_text = raw_arg.split("::", 1)[0]
        candidate = Path(candidate_text)
        candidate = (
            (Path.cwd() / candidate).resolve(strict=False)
            if not candidate.is_absolute()
            else candidate.resolve(strict=False)
        )
        if candidate.exists():
            roots.append(candidate)
    return tuple(dict.fromkeys(roots))


def _explicit_collection_requested(collection_path: Path, config) -> bool:
    for requested_root in _requested_collection_roots(config):
        if requested_root in {_REPO_ROOT, _TESTS_ROOT}:
            continue
        if requested_root.is_file():
            if collection_path == requested_root:
                return True
            continue
        try:
            collection_path.relative_to(requested_root)
        except ValueError:
            continue
        return True
    return False


def _full_suite_from_config(config) -> bool:
    return _full_suite_requested(
        cli_flag=bool(config.getoption("--full-suite")),
        env_value=os.environ.get(_FAST_SUITE_ENV_VAR),
    )


def pytest_addoption(parser) -> None:
    parser.addoption(
        "--full-suite",
        action="store_true",
        help=(
            "Run heavyweight suites that are skipped by default in the fast daily "
            f"path. The same can be enabled with {_FAST_SUITE_ENV_VAR}=1."
        ),
    )


def pytest_ignore_collect(collection_path, config) -> bool:
    resolved_path = Path(str(collection_path)).resolve(strict=False)
    try:
        rel_path = resolved_path.relative_to(_TESTS_ROOT).as_posix()
    except ValueError:
        return False
    return fast_suite_ignored(
        rel_path,
        full_suite=_full_suite_from_config(config),
        explicitly_requested=_explicit_collection_requested(resolved_path, config),
    )


def pytest_report_header(config) -> str:
    if _full_suite_from_config(config):
        return "test suite mode: full"
    return (
        "test suite mode: fast "
        f"(use --full-suite or {_FAST_SUITE_ENV_VAR}=1 to include heavyweight coverage)"
    )
