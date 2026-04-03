"""MCP server for GPD project state management.

Thin MCP wrapper around gpd.core.state, gpd.core.config, and
gpd.core.health. Exposes state queries, phase info, progress, and
health validation as MCP tools for solver agents.

Usage:
    python -m gpd.mcp.servers.state_server
    # or via entry point:
    gpd-mcp-state
"""

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import ConfigDict, WithJsonSchema, create_model
from pydantic import ValidationError as PydanticValidationError

from gpd.core.config import load_config
from gpd.core.errors import GPDError
from gpd.core.health import run_health
from gpd.core.observability import gpd_span
from gpd.core.phases import progress_render
from gpd.core.state import (
    load_state_json,
    state_advance_plan,
    state_validate,
)
from gpd.core.utils import is_phase_complete
from gpd.mcp.servers import (
    ABSOLUTE_PROJECT_DIR_SCHEMA,
    configure_mcp_logging,
    resolve_absolute_project_dir,
    stable_mcp_error,
    stable_mcp_response,
)

logger = configure_mcp_logging("gpd-state")

mcp = FastMCP("gpd-state")

AbsoluteProjectDirInput = Annotated[str, WithJsonSchema(ABSOLUTE_PROJECT_DIR_SCHEMA)]


def _tighten_registered_tool_contracts() -> None:
    def _build_strict_call(original_call, allowed_keys):
        async def _strict_call_fn_with_arg_validation(fn, fn_is_async, arguments_to_validate, arguments_to_pass_directly):
            unknown_keys = sorted(str(key) for key in arguments_to_validate if key not in allowed_keys)
            if unknown_keys:
                return stable_mcp_error(f"Unsupported arguments: {', '.join(unknown_keys)}")
            try:
                return await original_call(fn, fn_is_async, arguments_to_validate, arguments_to_pass_directly)
            except PydanticValidationError as exc:
                return stable_mcp_error(exc)

        return _strict_call_fn_with_arg_validation

    for tool in mcp._tool_manager.list_tools():  # type: ignore[attr-defined]
        arg_model = tool.fn_metadata.arg_model
        strict_model = create_model(
            f"{arg_model.__name__}Strict",
            __base__=arg_model,
            __config__=ConfigDict(extra="forbid", arbitrary_types_allowed=True),
        )
        tool.parameters = strict_model.model_json_schema(by_alias=True)
        allowed_keys = {
            key
            for field_name, field_info in arg_model.model_fields.items()
            for key in (field_name, field_info.alias)
            if key is not None
        }
        original_call = tool.fn_metadata.call_fn_with_arg_validation
        object.__setattr__(tool.fn_metadata, "call_fn_with_arg_validation", _build_strict_call(original_call, allowed_keys))


@mcp.tool()
def get_state(project_dir: AbsoluteProjectDirInput) -> dict:
    """Get the current project state.

    Returns the structured project state from `state.json`.

    Args:
        project_dir: Absolute path to the project root directory.
    """
    cwd = resolve_absolute_project_dir(project_dir)
    if cwd is None:
        return stable_mcp_error("project_dir must be an absolute path")
    with gpd_span("mcp.state.get", phase=""):
        try:
            state_obj = load_state_json(cwd)
            if state_obj is None:
                return stable_mcp_error("No project state found. Run 'gpd init' to create STATE.md.")
            return stable_mcp_response(state_obj)
        except (GPDError, OSError, ValueError, TimeoutError) as exc:
            return stable_mcp_error(exc)
        except Exception as exc:  # pragma: no cover - defensive envelope
            return stable_mcp_error(exc)


@mcp.tool()
def get_phase_info(project_dir: AbsoluteProjectDirInput, phase: str) -> dict:
    """Get detailed information about a specific phase.

    Args:
        project_dir: Absolute path to the project root directory.
        phase: Phase number (e.g., "01", "02.1").
    """
    from gpd.core.phases import find_phase

    cwd = resolve_absolute_project_dir(project_dir)
    if cwd is None:
        return stable_mcp_error("project_dir must be an absolute path")
    with gpd_span("mcp.state.phase_info", phase=phase):
        try:
            info = find_phase(cwd, phase)
            if info is None:
                return stable_mcp_error(f"Phase {phase} not found")
            plan_count = len(info.plans)
            summary_count = len(info.summaries)
            return stable_mcp_response(
                {
                    "phase_number": info.phase_number,
                    "phase_name": info.phase_name,
                    "directory": info.directory,
                    "phase_slug": info.phase_slug,
                    "plan_count": plan_count,
                    "summary_count": summary_count,
                    "complete": is_phase_complete(plan_count, summary_count),
                }
            )
        except (GPDError, OSError, ValueError, TimeoutError) as exc:
            return stable_mcp_error(exc)
        except Exception as exc:  # pragma: no cover - defensive envelope
            return stable_mcp_error(exc)


@mcp.tool()
def advance_plan(project_dir: AbsoluteProjectDirInput) -> dict:
    """Advance the project state to the next plan.

    Updates the current plan counter and related state fields.

    Args:
        project_dir: Absolute path to the project root directory.
    """
    cwd = resolve_absolute_project_dir(project_dir)
    if cwd is None:
        return stable_mcp_error("project_dir must be an absolute path")
    with gpd_span("mcp.state.advance_plan"):
        try:
            return stable_mcp_response(state_advance_plan(cwd).model_dump())
        except (GPDError, OSError, ValueError, TimeoutError) as exc:
            return stable_mcp_error(exc)
        except Exception as exc:  # pragma: no cover - defensive envelope
            return stable_mcp_error(exc)


@mcp.tool()
def get_progress(project_dir: AbsoluteProjectDirInput) -> dict:
    """Get overall project progress summary.

    Returns the computed progress summary without surfacing checkpoint shelf
    artifacts. Works even when STATE.md is missing.

    Args:
        project_dir: Absolute path to the project root directory.
    """
    cwd = resolve_absolute_project_dir(project_dir)
    if cwd is None:
        return stable_mcp_error("project_dir must be an absolute path")
    with gpd_span("mcp.state.progress"):
        try:
            return stable_mcp_response(progress_render(cwd, "json").model_dump())
        except (GPDError, OSError, ValueError, TimeoutError) as exc:
            return stable_mcp_error(exc)
        except Exception as exc:  # pragma: no cover - defensive envelope
            return stable_mcp_error(exc)


@mcp.tool()
def validate_state(project_dir: AbsoluteProjectDirInput) -> dict:
    """Run comprehensive state validation checks.

    Validates state.json against STATE.md, checks schema completeness,
    convention lock, phase format, and more. Returns issues and warnings.

    Args:
        project_dir: Absolute path to the project root directory.
    """
    cwd = resolve_absolute_project_dir(project_dir)
    if cwd is None:
        return stable_mcp_error("project_dir must be an absolute path")
    with gpd_span("mcp.state.validate"):
        try:
            result = state_validate(cwd)
            return stable_mcp_response(result.model_dump())
        except (GPDError, OSError, ValueError, TimeoutError) as exc:
            return stable_mcp_error(exc)
        except Exception as exc:  # pragma: no cover - defensive envelope
            return stable_mcp_error(exc)


@mcp.tool()
def run_health_check(project_dir: AbsoluteProjectDirInput, fix: bool = False) -> dict:
    """Run the full project health dashboard.

    Checks environment, project structure, storage-path policy, state validity,
    compaction, roadmap consistency, orphans, conventions, frontmatter,
    return envelopes, config, checkpoint tags, and git status.

    Args:
        project_dir: Absolute path to the project root directory.
        fix: If True, attempt auto-fixes for common issues.
    """
    cwd = resolve_absolute_project_dir(project_dir)
    if cwd is None:
        return stable_mcp_error("project_dir must be an absolute path")
    with gpd_span("mcp.state.health", fix=str(fix)):
        try:
            report = run_health(cwd, fix=fix)
            return stable_mcp_response(report.model_dump())
        except (GPDError, OSError, ValueError, TimeoutError) as exc:
            return stable_mcp_error(exc)
        except Exception as exc:  # pragma: no cover - defensive envelope
            return stable_mcp_error(exc)


@mcp.tool()
def get_config(project_dir: AbsoluteProjectDirInput) -> dict:
    """Get the project GPD configuration.

    Returns the resolved config including model profile, autonomy mode,
    research mode, workflow toggles, and branching strategy.

    Args:
        project_dir: Absolute path to the project root directory.
    """
    cwd = resolve_absolute_project_dir(project_dir)
    if cwd is None:
        return stable_mcp_error("project_dir must be an absolute path")
    with gpd_span("mcp.state.config"):
        try:
            config = load_config(cwd)
            return stable_mcp_response(config.model_dump())
        except (GPDError, OSError, ValueError, TimeoutError) as exc:
            return stable_mcp_error(exc)
        except Exception as exc:  # pragma: no cover - defensive envelope
            return stable_mcp_error(exc)


@mcp.tool()
def emit_phase_event(
    project_dir: AbsoluteProjectDirInput,
    event_type: str,
    phase: str,
    agent_type: str = "",
    details: str = "",
) -> dict:
    """Emit a phase lifecycle event for frontend navigation.

    Call this tool at phase boundaries during pipeline execution to help
    the frontend build a navigable outline of the research session.

    Event types:
    - "phase.started": A new pipeline phase has begun (e.g., planning, execution)
    - "phase.completed": A pipeline phase has finished successfully
    - "phase.failed": A pipeline phase encountered an error
    - "agent.started": A subagent has been spawned for a specific task
    - "agent.completed": A subagent has finished its work
    - "checkpoint": A significant milestone within a phase

    Args:
        project_dir: Absolute path to the project root directory.
        event_type: One of "phase.started", "phase.completed", "phase.failed",
                    "agent.started", "agent.completed", "checkpoint".
        phase: Phase identifier (e.g., "formulate", "plan", "execute", "verify",
               "write", "review", or a phase number like "1", "2.1").
        agent_type: For agent events, the subagent type (e.g., "phase-researcher",
                    "planner", "plan-checker", "executor", "verifier").
        details: Optional human-readable description of the event.
    """
    from datetime import datetime, UTC

    cwd = resolve_absolute_project_dir(project_dir)
    if cwd is None:
        return stable_mcp_error("project_dir must be an absolute path")

    valid_types = {
        "phase.started", "phase.completed", "phase.failed",
        "agent.started", "agent.completed", "checkpoint",
    }
    if event_type not in valid_types:
        return stable_mcp_error(
            f"Invalid event_type: {event_type}. Must be one of: {', '.join(sorted(valid_types))}"
        )

    timestamp = datetime.now(tz=UTC).isoformat()

    return stable_mcp_response({
        "event_type": event_type,
        "phase": phase,
        "agent_type": agent_type or None,
        "details": details or None,
        "timestamp": timestamp,
        "project_dir": str(cwd),
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the gpd-state MCP server."""
    from gpd.mcp.servers import run_mcp_server

    run_mcp_server(mcp, "GPD State MCP Server")


_tighten_registered_tool_contracts()


if __name__ == "__main__":
    main()
