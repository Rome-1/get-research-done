"""Regression tests for strict state/skills MCP response envelopes."""

from __future__ import annotations

from unittest.mock import patch

from grd.core.errors import GRDError
from grd.registry import SkillDef


def _assert_stable_envelope(result: object, expected_payload: dict[str, object]) -> None:
    from grd.mcp.servers import StableMCPEnvelope

    assert isinstance(result, StableMCPEnvelope)
    assert result["schema_version"] == 1
    assert result != expected_payload
    assert dict(result) == {"schema_version": 1, **expected_payload}
    assert result == {"schema_version": 1, **expected_payload}


def test_state_server_success_response_uses_strict_stable_envelope() -> None:
    from grd.mcp.servers.state_server import get_state

    mock_state = {"position": {"current_phase": "01"}, "decisions": []}

    with patch("grd.mcp.servers.state_server.load_state_json", return_value=mock_state):
        result = get_state("/fake/project")

    _assert_stable_envelope(result, mock_state)


def test_state_server_error_response_uses_strict_stable_envelope() -> None:
    from grd.mcp.servers.state_server import get_state

    with patch("grd.mcp.servers.state_server.load_state_json", side_effect=GRDError("boom")):
        result = get_state("/fake/project")

    _assert_stable_envelope(result, {"error": "boom"})


def test_state_server_unexpected_exception_uses_strict_stable_error_envelope() -> None:
    from grd.mcp.servers.state_server import get_config

    with patch("grd.mcp.servers.state_server.load_config", side_effect=RuntimeError("unexpected boom")):
        result = get_config("/fake/project")

    _assert_stable_envelope(result, {"error": "unexpected boom"})


def test_skills_server_success_response_uses_strict_stable_envelope() -> None:
    from grd.mcp.servers.skills_server import list_skills

    skills = [
        SkillDef(
            name="grd-execute-phase",
            description="Execute.",
            content="Run execution.",
            category="execution",
            path="/tmp/grd-execute-phase.md",
            source_kind="command",
            registry_name="execute-phase",
        ),
        SkillDef(
            name="grd-help",
            description="Help.",
            content="Help content.",
            category="help",
            path="/tmp/grd-help.md",
            source_kind="command",
            registry_name="help",
        ),
    ]

    with patch("grd.mcp.servers.skills_server._load_skill_index", return_value=skills):
        result = list_skills()

    _assert_stable_envelope(
        result,
        {
            "skills": [
                {
                    "name": "grd-execute-phase",
                    "description": "Execute.",
                    "category": "execution",
                },
                {
                    "name": "grd-help",
                    "description": "Help.",
                    "category": "help",
                },
            ],
            "count": 2,
            "categories": ["execution", "help"],
        },
    )


def test_skills_server_error_response_uses_strict_stable_envelope() -> None:
    from grd.mcp.servers.skills_server import route_skill

    with patch("grd.mcp.servers.skills_server._load_skill_index", side_effect=GRDError("registry offline")):
        result = route_skill("plan the next phase")

    _assert_stable_envelope(result, {"error": "registry offline"})


def test_skills_server_unexpected_exception_uses_strict_stable_error_envelope() -> None:
    from grd.mcp.servers.skills_server import get_skill

    with patch("grd.mcp.servers.skills_server._resolve_skill", side_effect=RuntimeError("unexpected boom")):
        result = get_skill("grd-help")

    _assert_stable_envelope(result, {"error": "unexpected boom"})
