"""Regression tests for MCP skill tool list projection."""

from __future__ import annotations

from unittest.mock import patch

from grd.registry import AgentDef, CommandDef, SkillDef


def test_get_skill_command_allowed_tools_are_defensive_copies() -> None:
    from grd.mcp.servers.skills_server import get_skill

    command_tools = ["file_read", "shell", "shell"]
    command = CommandDef(
        name="grd:help",
        description="Help.",
        argument_hint="",
        requires={},
        allowed_tools=command_tools,
        content="Command body.",
        path="/tmp/grd-help.md",
        source="commands",
    )
    skill = SkillDef(
        name="grd-help",
        description="Help.",
        content="Command body.",
        category="help",
        path="/tmp/grd-help.md",
        source_kind="command",
        registry_name="help",
    )

    with (
        patch("grd.mcp.servers.skills_server._resolve_skill", return_value=skill),
        patch("grd.mcp.servers.skills_server.content_registry.get_command", return_value=command),
    ):
        result = get_skill("grd-help")

    assert result["allowed_tools"] == ["file_read", "shell"]
    assert result["allowed_tools"] is not command.allowed_tools
    assert result["allowed_tools_surface"] == "command.allowed-tools"
    result["allowed_tools"].append("network")
    assert command.allowed_tools == ["file_read", "shell", "shell"]


def test_get_skill_agent_surfaces_allowed_tools() -> None:
    from grd.mcp.servers.skills_server import get_skill

    agent_tools = ["shell", "file_read", "shell"]
    agent = AgentDef(
        name="grd-debugger",
        description="Debugger.",
        system_prompt="Agent body.",
        tools=agent_tools,
        color="blue",
        path="/tmp/grd-debugger.md",
        source="agents",
    )
    skill = SkillDef(
        name="grd-debugger",
        description="Debugger.",
        content="Agent body.",
        category="debugging",
        path="/tmp/grd-debugger.md",
        source_kind="agent",
        registry_name="grd-debugger",
    )

    with (
        patch("grd.mcp.servers.skills_server._resolve_skill", return_value=skill),
        patch("grd.mcp.servers.skills_server.content_registry.get_agent", return_value=agent),
    ):
        result = get_skill("grd-debugger")

    assert result["allowed_tools"] == ["shell", "file_read"]
    assert result["allowed_tools"] is not agent.tools
    assert result["allowed_tools_surface"] == "agent.tools"
    result["allowed_tools"].append("network")
    assert agent.tools == ["shell", "file_read", "shell"]
