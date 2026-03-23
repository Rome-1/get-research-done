"""Intermediate result tracking subcommands."""

from __future__ import annotations

import typer

from grd.cli._helpers import _error, _get_cwd, _load_state_dict, _output, _parse_meta_options, console

result_app = typer.Typer(help="Intermediate results with dependency tracking")


@result_app.command("add")
def result_add(
    id: str | None = typer.Option(None, "--id", help="Result ID"),
    equation: str | None = typer.Option(None, "--equation", help="LaTeX equation"),
    description: str | None = typer.Option(None, "--description", help="Description"),
    units: str | None = typer.Option(None, "--units", help="Physical units"),
    validity: str | None = typer.Option(None, "--validity", help="Validity range"),
    phase: str | None = typer.Option(None, "--phase", help="Phase number"),
    depends_on: str | None = typer.Option(None, "--depends-on", help="Comma-separated dependency IDs"),
    verified: bool = typer.Option(False, "--verified", help="Mark as verified"),
    meta: list[str] | None = typer.Option(None, "--meta", help="Domain metadata as key=value (repeatable)"),
) -> None:
    """Add an intermediate result to the results registry."""
    import json as _json

    from grd.core.constants import ProjectLayout
    from grd.core.results import result_add
    from grd.core.state import save_state_json_locked
    from grd.core.utils import file_lock

    deps = depends_on.split(",") if depends_on else []
    metadata = _parse_meta_options(meta)
    cwd = _get_cwd()
    state_path = ProjectLayout(cwd).state_json

    with file_lock(state_path):
        try:
            state = _json.loads(state_path.read_text(encoding="utf-8"))
        except OSError:
            state = {}
        except _json.JSONDecodeError as e:
            _error(f"Malformed state.json: {e}")
        res = result_add(
            state,
            result_id=id,
            equation=equation,
            description=description,
            units=units,
            validity=validity,
            phase=phase,
            depends_on=deps,
            verified=verified,
            metadata=metadata or None,
        )
        save_state_json_locked(cwd, state)
    _output(res)


@result_app.command("list")
def result_list(
    phase: str | None = typer.Option(None, "--phase", help="Filter by phase"),
    verified: bool = typer.Option(False, "--verified", help="Show only verified"),
    unverified: bool = typer.Option(False, "--unverified", help="Show only unverified"),
) -> None:
    """List intermediate results."""
    from grd.core.results import result_list

    if verified and unverified:
        _error("--verified and --unverified are mutually exclusive")
    results = result_list(_load_state_dict(), phase=phase, verified=verified, unverified=unverified)
    if not results:
        from grd.cli._helpers import _raw

        if _raw:
            _output(results)
        else:
            console.print("[dim]No results found. Use 'grd result add' to register intermediate results.[/]")
        return
    _output(results)


@result_app.command("deps")
def result_deps(
    result_id: str = typer.Argument(..., help="Result ID"),
) -> None:
    """Show BFS dependency graph for a result."""
    from grd.core.results import result_deps

    _output(result_deps(_load_state_dict(), result_id))


@result_app.command("verify")
def result_verify(
    result_id: str = typer.Argument(..., help="Result ID to mark verified"),
) -> None:
    """Mark a result as verified."""
    import json as _json

    from grd.core.constants import ProjectLayout
    from grd.core.results import result_verify
    from grd.core.state import save_state_json_locked
    from grd.core.utils import file_lock

    cwd = _get_cwd()
    state_path = ProjectLayout(cwd).state_json

    with file_lock(state_path):
        try:
            state = _json.loads(state_path.read_text(encoding="utf-8"))
        except OSError:
            state = {}
        except _json.JSONDecodeError as e:
            _error(f"Malformed state.json: {e}")
        res = result_verify(state, result_id)
        save_state_json_locked(cwd, state)
    _output(res)


@result_app.command("update")
def result_update(
    result_id: str = typer.Argument(..., help="Result ID to update"),
    equation: str | None = typer.Option(None, "--equation", help="LaTeX equation"),
    description: str | None = typer.Option(None, "--description", help="Description"),
    units: str | None = typer.Option(None, "--units", help="Physical units"),
    validity: str | None = typer.Option(None, "--validity", help="Validity range"),
    phase: str | None = typer.Option(None, "--phase", help="Phase number"),
    depends_on: str | None = typer.Option(None, "--depends-on", help="Comma-separated dependency IDs"),
    verified: bool | None = typer.Option(None, "--verified/--no-verified", help="Mark as verified or un-verify"),
    meta: list[str] | None = typer.Option(None, "--meta", help="Domain metadata as key=value (repeatable)"),
) -> None:
    """Update an existing result."""
    import json as _json

    from grd.core.constants import ProjectLayout
    from grd.core.results import result_update
    from grd.core.state import save_state_json_locked
    from grd.core.utils import file_lock

    opts: dict[str, object] = {}
    if equation is not None:
        opts["equation"] = equation
    if description is not None:
        opts["description"] = description
    if units is not None:
        opts["units"] = units
    if validity is not None:
        opts["validity"] = validity
    if phase is not None:
        opts["phase"] = phase
    if depends_on is not None:
        opts["depends_on"] = depends_on.split(",")
    if verified is not None:
        opts["verified"] = verified
    metadata = _parse_meta_options(meta)
    if metadata:
        opts["metadata"] = metadata

    cwd = _get_cwd()
    state_path = ProjectLayout(cwd).state_json

    with file_lock(state_path):
        try:
            state = _json.loads(state_path.read_text(encoding="utf-8"))
        except OSError:
            state = {}
        except _json.JSONDecodeError as e:
            _error(f"Malformed state.json: {e}")
        _fields, updated = result_update(state, result_id, **opts)
        save_state_json_locked(cwd, state)
    _output(updated)
