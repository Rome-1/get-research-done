"""Phase lifecycle subcommands."""

from __future__ import annotations

import typer

from grd.cli._helpers import _error, _get_cwd, _output

phase_app = typer.Typer(help="Phase lifecycle (add, remove, complete, etc.)")


@phase_app.command("list")
def phase_list(
    file_type: str | None = typer.Option(None, "--type", help="File type filter"),
    phase: str | None = typer.Option(None, "--phase", help="Phase filter"),
) -> None:
    """List phases and their files."""
    from grd.core.phases import list_phase_files, list_phases

    if file_type or phase:
        _output(list_phase_files(_get_cwd(), file_type=file_type or "plan", phase=phase))
    else:
        _output(list_phases(_get_cwd()))


@phase_app.command("add")
def phase_add(
    description: list[str] = typer.Argument(..., help="Phase description"),
) -> None:
    """Add a new phase to the end of the roadmap."""
    from grd.core.phases import phase_add

    _output(phase_add(_get_cwd(), " ".join(description)))


@phase_app.command("insert")
def phase_insert(
    after_phase: str = typer.Argument(..., help="Phase number to insert after"),
    description: list[str] = typer.Argument(..., help="Phase description"),
) -> None:
    """Insert a new phase after an existing one."""
    from grd.core.phases import phase_insert

    _output(phase_insert(_get_cwd(), after_phase, " ".join(description)))


@phase_app.command("remove")
def phase_remove(
    phase_num: str = typer.Argument(..., help="Phase number to remove"),
    force: bool = typer.Option(False, "--force", help="Force removal even if completed"),
) -> None:
    """Remove a phase from the roadmap."""
    from grd.core.phases import phase_remove

    _output(phase_remove(_get_cwd(), phase_num, force=force))


@phase_app.command("complete")
def phase_complete(
    phase_num: str = typer.Argument(..., help="Phase number to mark complete"),
    override_formalization: str | None = typer.Option(
        None,
        "--override-formalization",
        help=(
            "Brief justification to bypass the needs_formalization gate "
            "(records a Decision in state.json). Use only when Lean verification "
            "is legitimately out of scope for this phase-close."
        ),
    ),
) -> None:
    """Mark a phase as complete."""
    from grd.core.phases import phase_complete

    _output(phase_complete(_get_cwd(), phase_num, override_formalization=override_formalization))


@phase_app.command("index")
def phase_plan_index(
    phase_num: str = typer.Argument(..., help="Phase number"),
) -> None:
    """Show plan index for a phase (plans, waves, dependencies)."""
    from grd.core.phases import phase_plan_index

    _output(phase_plan_index(_get_cwd(), phase_num))


@phase_app.command("find")
def phase_find(
    phase_num: str = typer.Argument(..., help="Phase number to find"),
) -> None:
    """Find a phase directory and its metadata."""
    from grd.core.phases import find_phase

    result = find_phase(_get_cwd(), phase_num)
    if result is None:
        _error(f"Phase {phase_num} not found")
    _output(result)


@phase_app.command("next-decimal")
def phase_next_decimal(
    base_phase: str = typer.Argument(..., help="Base phase number"),
) -> None:
    """Get the next available decimal phase number (e.g. 42 -> 42.1)."""
    from grd.core.phases import next_decimal_phase

    _output(next_decimal_phase(_get_cwd(), base_phase))


@phase_app.command("validate-waves")
def phase_validate_waves(
    phase_num: str = typer.Argument(..., help="Phase number to validate"),
) -> None:
    """Validate wave dependencies within a phase."""
    from grd.core.phases import validate_phase_waves

    result = validate_phase_waves(_get_cwd(), phase_num)
    _output(result)
    validation = getattr(result, "validation", None)
    if getattr(validation, "valid", True) is False:
        raise typer.Exit(code=1)
