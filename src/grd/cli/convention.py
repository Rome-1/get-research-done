"""Convention lock management subcommands."""

from __future__ import annotations

import typer

from grd.cli._helpers import _error, _get_cwd, _output, console, err_console

convention_app = typer.Typer(help="Convention lock (notation, units, sign conventions)")


def _load_lock():  # noqa: ANN202 — returns ConventionLock (imported inside)
    """Load ConventionLock from state.json in the current working directory."""
    import json

    from grd.contracts import ConventionLock
    from grd.core.constants import ProjectLayout

    state_path = ProjectLayout(_get_cwd()).state_json
    try:
        raw = json.loads(state_path.read_text(encoding="utf-8"))
    except OSError:
        return ConventionLock()
    except json.JSONDecodeError as e:
        _error(f"Malformed state.json: {e}")

    lock_data = raw.get("convention_lock", {})
    if not isinstance(lock_data, dict):
        return ConventionLock()
    return ConventionLock(**lock_data)


def _load_domain_ctx():  # noqa: ANN202
    """Load the DomainContext for the current project, or None."""
    import os

    from grd.domains.loader import load_domain

    domain_name = os.environ.get("GRD_DOMAIN", "physics")
    return load_domain(domain_name, project_root=_get_cwd())


@convention_app.command("set")
def convention_set(
    key: str = typer.Argument(..., help="Convention key"),
    value: str = typer.Argument(..., help="Convention value"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing convention"),
) -> None:
    """Set a convention in the convention lock."""
    import json as _json

    from grd.contracts import ConventionLock
    from grd.core.constants import ProjectLayout
    from grd.core.conventions import convention_set
    from grd.core.state import save_state_json_locked
    from grd.core.utils import file_lock

    cwd = _get_cwd()
    state_path = ProjectLayout(cwd).state_json

    # Perform the entire read-modify-write under a single file lock to avoid
    # the TOCTOU race that existed when _load_lock() ran before _save_lock().
    with file_lock(state_path):
        try:
            raw = _json.loads(state_path.read_text(encoding="utf-8"))
        except OSError:
            raw = {}
        except _json.JSONDecodeError as e:
            _error(f"Malformed state.json: {e}")

        lock_data = raw.get("convention_lock", {})
        if not isinstance(lock_data, dict):
            lock_data = {}
        lock = ConventionLock(**lock_data)

        result = convention_set(lock, key, value, force=force, domain_ctx=_load_domain_ctx())
        if result.updated and result.custom and not force:
            # Non-canonical key without --force: reject before persisting.
            pass
        elif result.updated:
            raw["convention_lock"] = lock.model_dump(exclude_none=True)
            save_state_json_locked(cwd, raw)

    # Show alias resolution feedback
    if result.key_alias_resolved:
        err_console.print(
            f"[dim]Resolved key alias:[/] '{result.key_alias_resolved}' → '{result.key}'",
            highlight=False,
        )
    if result.value_alias_resolved:
        err_console.print(
            f"[dim]Resolved value alias:[/] '{result.value_alias_resolved}' → '{result.value}'",
            highlight=False,
        )
    if result.custom:
        err_console.print(
            f"[yellow]Warning:[/] '{result.key}' is not a recognized convention for this domain. "
            "Use --force if this is intentional.",
            highlight=False,
        )
        if not force:
            _error(f"'{result.key}' is not a recognized convention. Use --force to set it anyway.")
    _output(result)


@convention_app.command("list")
def convention_list() -> None:
    """List all active conventions."""
    from grd.cli._helpers import _raw
    from grd.core.conventions import convention_list

    result = convention_list(_load_lock(), domain_ctx=_load_domain_ctx())
    if _raw:
        _output(result)
        return

    from rich.table import Table

    table = Table(
        title=f"Conventions ({result.set_count}/{result.total} set)",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Key")
    table.add_column("Label")
    table.add_column("Value")
    table.add_column("Status", justify="center")
    for entry in result.conventions.values():
        status = "[green]\u2713[/]" if entry.is_set else "[dim]unset[/]"
        val = entry.value or ""
        custom = " [dim](custom)[/]" if not entry.canonical else ""
        table.add_row(entry.key, entry.label + custom, val, status)
    console.print(table)


@convention_app.command("diff")
def convention_diff(
    phase1: str | None = typer.Argument(None, help="First phase"),
    phase2: str | None = typer.Argument(None, help="Second phase"),
) -> None:
    """Show convention differences between phases."""
    from grd.cli._helpers import _raw
    from grd.core.conventions import convention_diff_phases

    result = convention_diff_phases(_get_cwd(), phase1, phase2)
    if _raw:
        _output(result)
        return

    data = result.model_dump(mode="json", by_alias=True) if hasattr(result, "model_dump") else result
    if isinstance(data, dict) and not data.get("changed") and not data.get("added") and not data.get("removed"):
        console.print("[dim]No convention differences found.[/]")
        if not phase1 and not phase2:
            console.print(
                "[dim]Hint: Convention diff compares conventions across phases. Use 'grd phase add' to create phases first.[/]"
            )
        return
    _output(result)


@convention_app.command("check")
def convention_check() -> None:
    """Check convention consistency across phases."""
    from grd.core.conventions import convention_check

    _output(convention_check(_load_lock(), domain_ctx=_load_domain_ctx()))
