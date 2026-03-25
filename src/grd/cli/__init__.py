"""Unified GRD CLI -- entry point for core workflow and MCP tooling.

Delegates to ``grd.core.*`` modules for all command implementations.

Usage::

    grd state load
    grd phase list
    grd health --fix
    grd init execute-phase 42

All commands support ``--raw`` for JSON output and ``--cwd`` for working directory override.
"""

from __future__ import annotations

import os  # noqa: F401 — re-exported for test monkeypatching
import sys

import typer

from grd.cli._helpers import (
    _format_install_header_lines,
    _get_cwd,  # noqa: F401 — re-exported for test patching
    _maybe_reexec_from_checkout,
    _normalize_global_cli_options,
    _render_install_option_line,
    _resolve_cli_cwd_from_argv,  # noqa: F401 — re-exported for test patching
    _runtime_override_help,  # noqa: F401 — re-exported for test patching
    app,
)
from grd.cli.commands import (  # noqa: E402
    approx_app,
    calculation_app,
    config_app,
    context_app,
    init_app,
    json_app,
    milestone_app,
    observe_app,
    query_app,
    question_app,
    roadmap_app,
    trace_app,
    uncertainty_app,
)
from grd.cli.convention import convention_app  # noqa: E402
from grd.cli.domain import domain_app  # noqa: E402
from grd.cli.frontmatter import frontmatter_app  # noqa: E402
from grd.cli.pattern import pattern_app  # noqa: E402
from grd.cli.phase import phase_app  # noqa: E402
from grd.cli.result import result_app  # noqa: E402

# ─── Import submodules to register their commands on `app` ──────────────────
# Submodules that define their own typer apps are wired below via add_typer.
# Submodules that register directly on `app` (via `@app.command(...)`) just
# need to be imported so the decorators execute.
from grd.cli.state import state_app  # noqa: E402
from grd.cli.validate import validate_app  # noqa: E402
from grd.cli.verify import verify_app  # noqa: E402

# ─── Register subcommand groups ─────────────────────────────────────────────

app.add_typer(state_app, name="state")
app.add_typer(phase_app, name="phase")
app.add_typer(convention_app, name="convention")
app.add_typer(result_app, name="result")
app.add_typer(verify_app, name="verify")
app.add_typer(frontmatter_app, name="frontmatter")
app.add_typer(pattern_app, name="pattern")
app.add_typer(validate_app, name="validate")
app.add_typer(query_app, name="query")
app.add_typer(roadmap_app, name="roadmap")
app.add_typer(milestone_app, name="milestone")
app.add_typer(context_app, name="context")
app.add_typer(init_app, name="init", hidden=True)  # backward-compatible alias
app.add_typer(domain_app, name="domain")
app.add_typer(approx_app, name="approximation")
app.add_typer(uncertainty_app, name="uncertainty")
app.add_typer(question_app, name="question")
app.add_typer(calculation_app, name="calculation")
app.add_typer(config_app, name="config")
app.add_typer(json_app, name="json")
app.add_typer(trace_app, name="trace")
app.add_typer(observe_app, name="observe")

# ─── Import side-effect submodules that register directly on `app` ──────────
# paper.py and install.py use @app.command() decorators, so importing them
# is sufficient to register their commands.

import grd.cli.commands  # noqa: F401, E402 — registers @app.command() entries
import grd.cli.install  # noqa: F401, E402
import grd.cli.paper  # noqa: F401, E402
from grd.cli.install import _install_single_runtime  # noqa: F401, E402 — re-exported for tests

# ─── Top-level aliases ─────────────────────────────────────────────────────


@app.command("search")
def search(
    provides: str | None = typer.Option(None, "--provides", help="Search by provides"),
    requires: str | None = typer.Option(None, "--requires", help="Search by requires"),
    affects: str | None = typer.Option(None, "--affects", help="Search by affects"),
    equation: str | None = typer.Option(None, "--equation", help="Search by equation"),
    text: str | None = typer.Option(None, "--text", help="Full-text search"),
    phase_range: str | None = typer.Option(None, "--phase-range", help="Phase range filter (e.g. 10-20)"),
) -> None:
    """Search across phases (alias for 'query search')."""
    from grd.cli._helpers import _output  # noqa: F811
    from grd.core.query import query as query_search

    _output(
        query_search(
            _get_cwd(),
            provides=provides,
            requires=requires,
            affects=affects,
            equation=equation,
            text=text,
            phase_range=phase_range,
        )
    )


def entrypoint() -> int | None:
    """Console-script and ``python -m`` entrypoint with checkout preference."""
    _maybe_reexec_from_checkout()
    return app(args=_normalize_global_cli_options(sys.argv[1:]))


# Re-export for backward compatibility
__all__ = [
    "app",
    "entrypoint",
    "_format_install_header_lines",
    "_render_install_option_line",
    "_install_single_runtime",
]


if __name__ == "__main__":
    raise SystemExit(entrypoint())
