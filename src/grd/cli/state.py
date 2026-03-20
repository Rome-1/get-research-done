"""State management subcommands (STATE.md + state.json)."""

from __future__ import annotations

import typer

from grd.cli._helpers import _error, _get_cwd, _load_json_document, _output

state_app = typer.Typer(help="State management (STATE.md + state.json)")


@state_app.command("load")
def state_load() -> None:
    """Load and display current research state."""
    from grd.core.state import state_load

    _output(state_load(_get_cwd()))


@state_app.command("get")
def state_get(
    section: str | None = typer.Argument(None, help="State section to retrieve"),
) -> None:
    """Get a specific state section or the full state."""
    from grd.core.state import state_get

    _output(state_get(_get_cwd(), section))


@state_app.command("patch")
def state_patch(
    patches: list[str] = typer.Argument(..., help="Key-value pairs: key1 value1 key2 value2 ..."),
) -> None:
    """Patch multiple state fields at once."""
    from grd.core.state import state_patch

    if len(patches) % 2 != 0:
        _error("state patch requires key-value pairs (even number of arguments)")
    patch_dict: dict[str, str] = {}
    for i in range(0, len(patches), 2):
        key = patches[i].lstrip("-")
        if not key:
            _error(f"Invalid empty key after stripping dashes: {patches[i]!r}")
        patch_dict[key] = patches[i + 1]
    _output(state_patch(_get_cwd(), patch_dict))


@state_app.command("set-project-contract")
def state_set_project_contract_cmd(
    source: str = typer.Argument(..., help="Path to a JSON file containing the project contract, or '-' for stdin"),
) -> None:
    """Persist the canonical project contract into state.json."""
    from grd.core.contract_validation import validate_project_contract
    from grd.core.state import state_set_project_contract

    contract_data = _load_json_document(source)

    validation = validate_project_contract(contract_data, mode="approved")
    if not validation.valid:
        _output(validation)
        raise typer.Exit(code=1)

    result = state_set_project_contract(_get_cwd(), contract_data)
    _output(result)
    if not result.updated and result.reason and result.reason.startswith("Project contract failed scoping validation:"):
        raise typer.Exit(code=1)


@state_app.command("update")
def state_update(
    field: str = typer.Argument(..., help="Field name to update"),
    value: str = typer.Argument(..., help="New value"),
) -> None:
    """Update a single state field."""
    from grd.core.state import state_update

    _output(state_update(_get_cwd(), field, value))


@state_app.command("advance")
def state_advance() -> None:
    """Advance to the next plan in current phase."""
    from grd.core.state import state_advance_plan

    _output(state_advance_plan(_get_cwd()))


@state_app.command("compact")
def state_compact() -> None:
    """Archive old state entries to keep STATE.md concise."""
    from grd.core.state import state_compact

    _output(state_compact(_get_cwd()))


@state_app.command("snapshot")
def state_snapshot() -> None:
    """Return a fast read-only snapshot of current state for progress and routing."""
    from grd.core.state import state_snapshot

    _output(state_snapshot(_get_cwd()))


@state_app.command("validate")
def state_validate() -> None:
    """Validate state consistency and schema compliance."""
    from grd.core.state import state_validate

    result = state_validate(_get_cwd())
    _output(result)
    if hasattr(result, "valid") and not result.valid:
        raise typer.Exit(code=1)


@state_app.command("record-metric")
def state_record_metric(
    phase: str | None = typer.Option(None, "--phase", help="Phase number"),
    plan: str | None = typer.Option(None, "--plan", help="Plan name"),
    duration: str | None = typer.Option(None, "--duration", help="Duration"),
    tasks: str | None = typer.Option(None, "--tasks", help="Task count"),
    files: str | None = typer.Option(None, "--files", help="File count"),
) -> None:
    """Record execution metric for a phase/plan."""
    from grd.core.state import state_record_metric

    _output(state_record_metric(_get_cwd(), phase=phase, plan=plan, duration=duration, tasks=tasks, files=files))


@state_app.command("update-progress")
def state_update_progress() -> None:
    """Recalculate progress percentage from phase completion."""
    from grd.core.state import state_update_progress

    _output(state_update_progress(_get_cwd()))


@state_app.command("add-decision")
def state_add_decision(
    phase: str | None = typer.Option(None, "--phase", help="Phase number"),
    summary: str | None = typer.Option(None, "--summary", help="Decision summary"),
    rationale: str = typer.Option("", "--rationale", help="Decision rationale"),
) -> None:
    """Record a research decision."""
    from grd.core.state import state_add_decision

    _output(state_add_decision(_get_cwd(), phase=phase, summary=summary, rationale=rationale))


@state_app.command("add-blocker")
def state_add_blocker(
    text: str = typer.Option(..., "--text", help="Blocker description"),
) -> None:
    """Record a blocker."""
    from grd.core.state import state_add_blocker

    _output(state_add_blocker(_get_cwd(), text))


@state_app.command("resolve-blocker")
def state_resolve_blocker(
    text: str = typer.Option(..., "--text", help="Blocker description to resolve"),
) -> None:
    """Mark a blocker as resolved."""
    from grd.core.state import state_resolve_blocker

    _output(state_resolve_blocker(_get_cwd(), text))


@state_app.command("record-session")
def state_record_session(
    stopped_at: str | None = typer.Option(None, "--stopped-at", help="Stop timestamp"),
    resume_file: str | None = typer.Option(None, "--resume-file", help="Resume context file"),
) -> None:
    """Record a session boundary for context tracking."""
    from grd.core.state import state_record_session

    _output(state_record_session(_get_cwd(), stopped_at=stopped_at, resume_file=resume_file))
