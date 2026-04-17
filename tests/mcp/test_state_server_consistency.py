"""Consistency test: all state_server MCP tools must have error handling."""

import ast
import json
from pathlib import Path
from types import SimpleNamespace

from grd.core.state import default_state_dict
from grd.mcp.servers.state_server import get_progress


async def _tool_names() -> list[str]:
    tools = await mcp.list_tools()
    return [tool.name for tool in tools]


def test_state_server_exposes_expected_tool_names() -> None:
    names = anyio.run(_tool_names)

    assert {
        "get_state",
        "get_phase_info",
        "advance_plan",
        "get_progress",
        "validate_state",
        "run_health_check",
        "get_config",
    } == set(names)


REQUIRED_EXCEPTIONS = {"GRDError", "OSError", "ValueError"}


def test_all_state_server_tools_have_error_handling():
    """Every @mcp.tool() in state_server.py must catch GRDError, OSError, ValueError."""
    source_path = Path(__file__).resolve().parents[2] / "src" / "grd" / "mcp" / "servers" / "state_server.py"
    source = source_path.read_text()
    tree = ast.parse(source, filename=str(source_path))

    tool_functions: list[ast.FunctionDef] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for deco in node.decorator_list:
                if _is_mcp_tool_decorator(deco):
                    tool_functions.append(node)
                    break

    # Sanity: the server must expose at least one tool
    assert tool_functions, "No @mcp.tool() functions found — parser may be broken"

    missing_try: list[str] = []
    missing_exceptions: dict[str, set[str]] = {}

    for func in tool_functions:
        # Look for at least one Try node anywhere in the function body
        try_nodes = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
        if not try_nodes:
            missing_try.append(func.name)
            continue

        # Collect all exception names caught across every handler in every
        # try/except inside the function.
        caught: set[str] = set()
        for try_node in try_nodes:
            for handler in try_node.handlers:
                caught |= _get_except_handler_names(handler)

        missing = REQUIRED_EXCEPTIONS - caught
        if missing:
            missing_exceptions[func.name] = missing

    errors: list[str] = []
    for name in missing_try:
        errors.append(f"  {name}(): missing try/except entirely")
    for name, missing in sorted(missing_exceptions.items()):
        errors.append(f"  {name}(): except handler does not catch {', '.join(sorted(missing))}")

    assert not errors, "MCP tool functions in state_server.py lack required error handling:\n" + "\n".join(errors)

    result = apply_return_updates(str(tmp_path), "GRD/phases/01-foundations/01-foundations-01-SUMMARY.md")

def test_state_server_has_expected_tool_count():
    """Guard against accidentally removing tools — expect at least 7."""
    source_path = Path(__file__).resolve().parents[2] / "src" / "grd" / "mcp" / "servers" / "state_server.py"
    source = source_path.read_text()
    tree = ast.parse(source, filename=str(source_path))

    result = apply_return_updates("relative/project", "GRD/phases/01-foundations/01-foundations-01-SUMMARY.md")

    assert tool_count >= 7, (
        f"Expected at least 7 @mcp.tool() functions, found {tool_count}. Was a tool accidentally removed?"
    )

    result = tool_fn(**kwargs)

    assert result["schema_version"] == 1
    assert result["error"] in {"boom", "missing", "bad"}


def test_load_state_json_strips_legacy_session_and_surfaces_contract_gate(monkeypatch, tmp_path: Path) -> None:
    state_obj = {
        "position": {"current_phase": "01"},
        "decisions": [],
        "blockers": [],
        "session": {"last_date": "2026-01-01"},
    }

    monkeypatch.setattr(
        "grd.mcp.servers.state_server.peek_state_json",
        lambda *_args, **_kwargs: (state_obj, [], "state.json"),
    )
    monkeypatch.setattr(
        "grd.mcp.servers.state_server._project_contract_runtime_payload_for_state",
        lambda *_args, **_kwargs: (
            {"status": "loaded"},
            {"valid": True},
            {"authoritative": True},
        ),
    )

    result = load_state_json(tmp_path)

    assert result is not None
    assert "session" not in result
    assert result["position"]["current_phase"] == "01"
    assert result["project_contract_load_info"]["status"] == "loaded"
    assert result["project_contract_validation"]["valid"] is True
    assert result["project_contract_gate"]["authoritative"] is True


def test_load_state_json_uses_read_only_peek_without_locking(monkeypatch, tmp_path: Path) -> None:
    state_obj = {
        "position": {"current_phase": "01"},
        "decisions": [],
        "blockers": [],
    }

    seen: dict[str, object] = {}

    def _peek_state_json(*args, **kwargs):
        seen["args"] = args
        seen["kwargs"] = kwargs
        return state_obj, [], "state.json"

    monkeypatch.setattr("grd.mcp.servers.state_server.peek_state_json", _peek_state_json)
    monkeypatch.setattr(
        "grd.mcp.servers.state_server._project_contract_runtime_payload_for_state",
        lambda *_args, **_kwargs: (
            {"status": "loaded"},
            {"valid": True},
            {"authoritative": True},
        ),
    )

    result = load_state_json(tmp_path)

    assert result is not None
    assert seen["args"] == (tmp_path,)
    assert seen["kwargs"]["recover_intent"] is False
    assert seen["kwargs"]["surface_blocked_project_contract"] is True
    assert seen["kwargs"]["acquire_lock"] is False


def test_get_state_reports_current_project_state_guidance(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("grd.mcp.servers.state_server.load_state_json", lambda *_args, **_kwargs: None)

    result = get_state(str(tmp_path))

    assert result == {
        "error": "No project state found. Run 'grd init new-project' to initialize a GRD project state.",
        "schema_version": 1,
    }


def test_run_health_check_preserves_latest_return_failure_details(monkeypatch, fake_project_dir) -> None:
    failing_check = HealthCheck(
        status=CheckStatus.FAIL,
        label="Latest Return Envelope",
        details={
            "file": "01-setup/01-setup-01-SUMMARY.md",
            "fields_found": [],
            "warning_count": 0,
        },
        issues=["01-setup/01-setup-01-SUMMARY.md: grd_return YAML parse error: malformed envelope"],
    )
    mock_report = HealthReport(
        overall=CheckStatus.FAIL,
        summary=HealthSummary(ok=0, warn=0, fail=1, total=1),
        checks=[failing_check],
        fixes_applied=[],
    )

    monkeypatch.setattr("grd.mcp.servers.state_server.run_health", lambda *_args, **_kwargs: mock_report)

    result = run_health_check(fake_project_dir)

    assert result["checks"][0]["label"] == "Latest Return Envelope"
    assert result["checks"][0]["details"]["file"] == "01-setup/01-setup-01-SUMMARY.md"
    assert result["checks"][0]["issues"][0].endswith("malformed envelope")


def test_health_peek_normalized_state_uses_read_only_peek_without_locking(monkeypatch, tmp_path: Path) -> None:
    from grd.core.health import _peek_normalized_state_for_health

    state_obj = {"position": {"current_phase": "01"}}
    seen: dict[str, object] = {}

    def _peek_state_json(*args, **kwargs):
        seen["args"] = args
        seen["kwargs"] = kwargs
        return state_obj, [], "STATE.md"

    monkeypatch.setattr("grd.core.health.peek_state_json", _peek_state_json)

    result, source = _peek_normalized_state_for_health(tmp_path)

    assert result == state_obj
    assert source == "STATE.md"
    assert seen["args"] == (tmp_path,)
    assert seen["kwargs"]["recover_intent"] is False
    assert seen["kwargs"]["surface_blocked_project_contract"] is True
    assert seen["kwargs"]["acquire_lock"] is False


def test_get_progress_does_not_mutate_checkpoint_shelf_artifacts(tmp_path: Path) -> None:
    """Progress reads should not create, update, or delete checkpoint shelf files."""
    cwd = tmp_path
    planning = cwd / "GRD"
    planning.mkdir()
    (planning / "phases").mkdir()
    (planning / "state.json").write_text(json.dumps(default_state_dict(), indent=2), encoding="utf-8")

    phase_one = planning / "phases" / "01-foundations"
    phase_one.mkdir()
    (phase_one / "PLAN.md").write_text("# plan\n", encoding="utf-8")
    (phase_one / "SUMMARY.md").write_text("# summary\n", encoding="utf-8")

    phase_two = planning / "phases" / "02-analysis"
    phase_two.mkdir()
    (phase_two / "PLAN.md").write_text("# plan\n", encoding="utf-8")
    (phase_two / "SUMMARY.md").write_text("# summary\n", encoding="utf-8")

    checkpoint_dir = cwd / "GRD" / "phase-checkpoints"
    checkpoint_dir.mkdir()
    stale_checkpoint = checkpoint_dir / "99-old-phase.md"
    stale_checkpoint.write_text("stale checkpoint\n", encoding="utf-8")
    checkpoints_index = cwd / "GRD" / "CHECKPOINTS.md"
    checkpoints_index.write_text("stale index\n", encoding="utf-8")

    result = get_progress(str(cwd))

    assert result["percent"] == 100
    assert result["total_plans"] == 2
    assert result["total_summaries"] == 2
    assert "checkpoint_files" not in result
    assert not (checkpoint_dir / "01-foundations.md").exists()
    assert not (checkpoint_dir / "02-analysis.md").exists()
    assert stale_checkpoint.read_text(encoding="utf-8") == "stale checkpoint\n"
    assert stale_checkpoint.exists()
    assert checkpoints_index.read_text(encoding="utf-8") == "stale index\n"


def test_get_phase_info_counts_only_matching_summary_identities(tmp_path: Path) -> None:
    cwd = tmp_path
    planning = cwd / "GRD"
    planning.mkdir()
    (planning / "phases").mkdir()
    phase_dir = cwd / "GRD" / "phases" / "01-setup"
    phase_dir.mkdir()
    (phase_dir / "PLAN.md").write_text("# plan\n", encoding="utf-8")
    (phase_dir / "01-setup-02-PLAN.md").write_text("# plan\n", encoding="utf-8")
    (phase_dir / "SUMMARY.md").write_text("# summary\n", encoding="utf-8")
    (phase_dir / "01-setup-99-SUMMARY.md").write_text("# summary\n", encoding="utf-8")

    result = get_phase_info(str(cwd), "01")

    assert result["plan_count"] == 2
    assert result["summary_count"] == 1
    assert result["complete"] is False
