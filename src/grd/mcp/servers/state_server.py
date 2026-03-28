"""MCP server for GRD project state management.

Thin MCP wrapper around grd.core.state, grd.core.config, and
grd.core.health. Exposes state queries, phase info, progress, and
health validation as MCP tools for solver agents.

Usage:
    python -m grd.mcp.servers.state_server
    # or via entry point:
    grd-mcp-state
"""

import logging
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from grd.core.config import load_config
from grd.core.errors import GRDError
from grd.core.health import run_health
from grd.core.observability import grd_span
from grd.core.phases import progress_render
from grd.core.state import (
    load_state_json,
    state_advance_plan,
    state_validate,
)
from grd.core.utils import is_phase_complete
from grd.mcp.servers import stable_mcp_error, stable_mcp_response

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(name)s %(levelname)s: %(message)s")
logger = logging.getLogger("grd-state")

mcp = FastMCP("grd-state")


def _resolve_project_dir(project_dir: str) -> Path | None:
    """Return an absolute project root path or ``None`` when the contract is violated."""
    cwd = Path(project_dir)
    if not cwd.is_absolute():
        return None
    return cwd


@mcp.tool()
def get_state(project_dir: str) -> dict:
    """Get the current project state.

    Returns the structured project state from `state.json`.

    Args:
        project_dir: Absolute path to the project root directory.
    """
    cwd = _resolve_project_dir(project_dir)
    if cwd is None:
        return stable_mcp_error("project_dir must be an absolute path")
    with grd_span("mcp.state.get", phase=""):
        try:
            state_obj = load_state_json(cwd)
            if state_obj is None:
                return stable_mcp_error("No project state found. Run 'grd init' to create STATE.md.")
            return stable_mcp_response(state_obj)
        except (GRDError, OSError, ValueError, TimeoutError) as exc:
            return stable_mcp_error(exc)
        except Exception as exc:  # pragma: no cover - defensive envelope
            return stable_mcp_error(exc)


@mcp.tool()
def get_phase_info(project_dir: str, phase: str) -> dict:
    """Get detailed information about a specific phase.

    Args:
        project_dir: Absolute path to the project root directory.
        phase: Phase number (e.g., "01", "02.1").
    """
    from grd.core.phases import find_phase

    cwd = _resolve_project_dir(project_dir)
    if cwd is None:
        return stable_mcp_error("project_dir must be an absolute path")
    with grd_span("mcp.state.phase_info", phase=phase):
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
        except (GRDError, OSError, ValueError, TimeoutError) as exc:
            return stable_mcp_error(exc)
        except Exception as exc:  # pragma: no cover - defensive envelope
            return stable_mcp_error(exc)


@mcp.tool()
def advance_plan(project_dir: str) -> dict:
    """Advance the project state to the next plan.

    Updates the current plan counter and related state fields.

    Args:
        project_dir: Absolute path to the project root directory.
    """
    cwd = _resolve_project_dir(project_dir)
    if cwd is None:
        return stable_mcp_error("project_dir must be an absolute path")
    with grd_span("mcp.state.advance_plan"):
        try:
            return stable_mcp_response(state_advance_plan(cwd).model_dump())
        except (GRDError, OSError, ValueError, TimeoutError) as exc:
            return stable_mcp_error(exc)
        except Exception as exc:  # pragma: no cover - defensive envelope
            return stable_mcp_error(exc)


@mcp.tool()
def get_progress(project_dir: str) -> dict:
    """Get overall project progress summary.

    Returns the computed progress summary without surfacing checkpoint shelf
    artifacts. Works even when STATE.md is missing.

    Args:
        project_dir: Absolute path to the project root directory.
    """
    cwd = _resolve_project_dir(project_dir)
    if cwd is None:
        return stable_mcp_error("project_dir must be an absolute path")
    with grd_span("mcp.state.progress"):
        try:
            return stable_mcp_response(progress_render(cwd, "json").model_dump())
        except (GRDError, OSError, ValueError, TimeoutError) as exc:
            return stable_mcp_error(exc)
        except Exception as exc:  # pragma: no cover - defensive envelope
            return stable_mcp_error(exc)


@mcp.tool()
def validate_state(project_dir: str) -> dict:
    """Run comprehensive state validation checks.

    Validates state.json against STATE.md, checks schema completeness,
    convention lock, phase format, and more. Returns issues and warnings.

    Args:
        project_dir: Absolute path to the project root directory.
    """
    cwd = _resolve_project_dir(project_dir)
    if cwd is None:
        return stable_mcp_error("project_dir must be an absolute path")
    with grd_span("mcp.state.validate"):
        try:
            result = state_validate(cwd)
            return stable_mcp_response(result.model_dump())
        except (GRDError, OSError, ValueError, TimeoutError) as exc:
            return stable_mcp_error(exc)
        except Exception as exc:  # pragma: no cover - defensive envelope
            return stable_mcp_error(exc)


@mcp.tool()
def run_health_check(project_dir: str, fix: bool = False) -> dict:
    """Run the full project health dashboard.

    Checks environment, project structure, storage-path policy, state validity,
    compaction, roadmap consistency, orphans, conventions, frontmatter,
    return envelopes, config, checkpoint tags, and git status.

    Args:
        project_dir: Absolute path to the project root directory.
        fix: If True, attempt auto-fixes for common issues.
    """
    cwd = _resolve_project_dir(project_dir)
    if cwd is None:
        return stable_mcp_error("project_dir must be an absolute path")
    with grd_span("mcp.state.health", fix=str(fix)):
        try:
            report = run_health(cwd, fix=fix)
            return stable_mcp_response(report.model_dump())
        except (GRDError, OSError, ValueError, TimeoutError) as exc:
            return stable_mcp_error(exc)
        except Exception as exc:  # pragma: no cover - defensive envelope
            return stable_mcp_error(exc)


@mcp.tool()
def get_config(project_dir: str) -> dict:
    """Get the project GRD configuration.

    Returns the resolved config including model profile, autonomy mode,
    research mode, workflow toggles, and branching strategy.

    Args:
        project_dir: Absolute path to the project root directory.
    """
    cwd = _resolve_project_dir(project_dir)
    if cwd is None:
        return stable_mcp_error("project_dir must be an absolute path")
    with grd_span("mcp.state.config"):
        try:
            config = load_config(cwd)
            return stable_mcp_response(config.model_dump())
        except (GRDError, OSError, ValueError, TimeoutError) as exc:
            return stable_mcp_error(exc)
        except Exception as exc:  # pragma: no cover - defensive envelope
            return stable_mcp_error(exc)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the grd-state MCP server."""
    from grd.mcp.servers import run_mcp_server

    run_mcp_server(mcp, "GRD State MCP Server")


if __name__ == "__main__":
    main()
