"""Behavior-focused adapter regression coverage."""

from __future__ import annotations

import importlib
import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from grd.core.public_surface_contract import local_cli_bridge_commands
from grd.mcp.builtin_servers import GRD_MCP_SERVER_KEYS


def test_write_settings_errors_reference_the_directory(tmp_path: Path) -> None:
    from grd.adapters.install_utils import write_settings

    settings_path = tmp_path / "settings.json"

    with patch("pathlib.Path.write_text", side_effect=PermissionError("denied")):
        with pytest.raises(PermissionError, match=re.escape(str(tmp_path))):
            write_settings(settings_path, {"key": "value"})


def test_write_settings_mkdir_errors_reference_settings_directory(tmp_path: Path) -> None:
    from grd.adapters.install_utils import write_settings

    settings_path = tmp_path / "deep" / "nested" / "settings.json"

    with patch("pathlib.Path.mkdir", side_effect=PermissionError("denied")):
        with pytest.raises(PermissionError, match="settings directory"):
            write_settings(settings_path, {"key": "value"})


def test_convert_tool_references_uses_literal_replacements() -> None:
    from grd.adapters.install_utils import convert_tool_references_in_body

    assert "todo_write" in convert_tool_references_in_body(
        "Use TodoWrite to record tasks.",
        {"TodoWrite": "todo_write"},
    )
    assert "new\\1tool" in convert_tool_references_in_body(
        "Use OldTool to do things.",
        {"OldTool": "new\\1tool"},
    )


def test_codex_install_restores_skills_dir_after_failure(grd_root: Path, tmp_path: Path) -> None:
    from grd.adapters.codex import CodexAdapter

    adapter = CodexAdapter()
    sentinel = Path("/original/skills/dir")
    adapter._skills_dir = sentinel

    target = tmp_path / ".codex"
    target.mkdir()

    with patch.object(
        CodexAdapter.__bases__[0],
        "install",
        side_effect=RuntimeError("simulated install failure"),
    ):
        with pytest.raises(RuntimeError, match="simulated install failure"):
            adapter.install(grd_root, target, is_global=False, skills_dir=tmp_path / "new-skills")

    assert adapter._skills_dir == sentinel


def test_codex_install_restores_skills_dir_after_success(grd_root: Path, tmp_path: Path) -> None:
    from grd.adapters.codex import CodexAdapter

    adapter = CodexAdapter()
    sentinel = Path("/original/skills/dir")
    adapter._skills_dir = sentinel

    target = tmp_path / ".codex"
    target.mkdir()
    fake_result = {"runtime": "codex", "target": str(target), "commands": 0, "agents": 0}

    with patch.object(CodexAdapter.__bases__[0], "install", return_value=fake_result):
        result = adapter.install(grd_root, target, is_global=False, skills_dir=tmp_path / "new-skills")

    assert result == fake_result
    assert adapter._skills_dir == sentinel


def test_configure_opencode_permissions_recovers_from_non_dict_json(tmp_path: Path) -> None:
    from grd.adapters.opencode import configure_opencode_permissions

    config_dir = tmp_path / "opencode"
    config_dir.mkdir()
    (config_dir / "opencode.json").write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    before = (config_dir / "opencode.json").read_text(encoding="utf-8")

    with pytest.raises(RuntimeError, match="malformed"):
        configure_opencode_permissions(config_dir)

    assert (config_dir / "opencode.json").read_text(encoding="utf-8") == before


def test_write_mcp_servers_opencode_recovers_from_non_dict_mcp_key(tmp_path: Path) -> None:
    from grd.adapters.opencode import _write_mcp_servers_opencode

    config_dir = tmp_path / "opencode"
    config_dir.mkdir()
    (config_dir / "opencode.json").write_text(json.dumps({"mcp": "not a dict"}), encoding="utf-8")
    before = (config_dir / "opencode.json").read_text(encoding="utf-8")

    count = _write_mcp_servers_opencode(
        config_dir,
        {
            "grd-errors": {
                "command": "python",
                "args": ["-m", "grd.mcp.servers.errors_mcp"],
            }
        },
    )
    written = json.loads((config_dir / "opencode.json").read_text(encoding="utf-8"))

    assert count == 1
    assert isinstance(written["mcp"], dict)
    assert "grd-errors" in written["mcp"]


@pytest.mark.parametrize(
    ("module_name", "function_name"),
    [
        ("grd.adapters.claude_code", "_rewrite_grd_cli_invocations"),
        ("grd.adapters.codex", "_rewrite_codex_grd_cli_invocations"),
        ("grd.adapters.gemini", "_rewrite_grd_cli_invocations"),
        ("grd.adapters.opencode", "_rewrite_grd_cli_invocations"),
    ],
)
@pytest.mark.parametrize(
    ("shell_line", "expected_fragment"),
    [
        ("grd; echo ok\n", "/runtime/grd; echo ok"),
        ("echo $(grd)\n", "echo $(/runtime/grd)"),
        ("grd>out.log\n", "/runtime/grd>out.log"),
    ],
)
def test_runtime_shell_rewriters_handle_metacharacter_terminated_grd_commands(
    module_name: str,
    function_name: str,
    shell_line: str,
    expected_fragment: str,
) -> None:
    module = importlib.import_module(module_name)
    rewrite = getattr(module, function_name)

    result = rewrite(f"```bash\n{shell_line}```\n", "/runtime/grd")

    assert expected_fragment in result


@pytest.mark.parametrize(
    ("module_name", "function_name"),
    [
        ("grd.adapters.claude_code", "_rewrite_grd_cli_invocations"),
        ("grd.adapters.codex", "_rewrite_codex_grd_cli_invocations"),
        ("grd.adapters.gemini", "_rewrite_grd_cli_invocations"),
        ("grd.adapters.opencode", "_rewrite_grd_cli_invocations"),
    ],
)
def test_runtime_rewriters_preserve_public_local_cli_contract(module_name: str, function_name: str) -> None:
    module = importlib.import_module(module_name)
    rewrite = getattr(module, function_name)

    public_commands = local_cli_bridge_commands()
    content = (
        "Use `grd --help` before anything else.\n"
        "Keep `grd config ensure-section` bridged because it is an executable shell step.\n"
        "```bash\n"
        + "\n".join([*public_commands, "grd config ensure-section"])
        + "\n```\n"
    )

    result = rewrite(content, "/runtime/grd")

    assert "`grd --help`" in result
    assert "`grd config ensure-section`" in result
    for command in public_commands:
        assert command in result
        assert f"/runtime/grd{command[3:]}" not in result
    assert "/runtime/grd config ensure-section" in result
