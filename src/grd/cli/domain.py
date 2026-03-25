"""Domain pack management subcommands."""

from __future__ import annotations

import typer

from grd.cli._helpers import _error, _get_cwd, _output, console

domain_app = typer.Typer(help="Domain pack discovery, info, and selection")


@domain_app.command("list")
def domain_list() -> None:
    """List all available domain packs."""
    import os

    from grd.domains.loader import list_available_domains, load_domain

    active = os.environ.get("GRD_DOMAIN", "physics")
    domains = list_available_domains()

    if not domains:
        _error("No domain packs found")

    from rich.table import Table

    table = Table(title="Available Domain Packs", show_header=True, header_style="bold cyan")
    table.add_column("Name")
    table.add_column("Description")
    table.add_column("Active", justify="center")

    for name in sorted(domains):
        if name.startswith("_"):
            continue
        ctx = load_domain(name)
        desc = ""
        if ctx and ctx.pack:
            desc = ctx.pack.description or ""
        marker = "[bold green]\u2713[/]" if name == active else ""
        table.add_row(name, desc, marker)

    console.print(table)


@domain_app.command("info")
def domain_info(
    name: str = typer.Argument(..., help="Domain pack name"),
) -> None:
    """Show detailed information about a domain pack."""
    from grd.domains.loader import load_domain

    ctx = load_domain(name, project_root=_get_cwd())
    if ctx is None:
        _error(f"Domain pack '{name}' not found")

    pack = ctx.pack
    info = {
        "name": pack.name,
        "description": pack.description or "",
        "version": pack.version or "",
        "convention_count": len(ctx.convention_fields) if ctx.convention_fields else 0,
        "seed_pattern_count": len(ctx.seed_patterns) if ctx.seed_patterns else 0,
    }
    if pack.result_metadata_fields:
        info["result_metadata_fields"] = [f["key"] for f in pack.result_metadata_fields]

    _output(info)


@domain_app.command("set")
def domain_set(
    name: str = typer.Argument(..., help="Domain pack name to activate"),
) -> None:
    """Set the active domain for the current project."""
    import json as _json

    from grd.core.constants import ProjectLayout
    from grd.core.state import save_state_json_locked
    from grd.core.utils import file_lock
    from grd.domains.loader import load_domain

    ctx = load_domain(name, project_root=_get_cwd())
    if ctx is None:
        from grd.domains.loader import list_available_domains

        available = list_available_domains()
        _error(f"Domain pack '{name}' not found. Available: {', '.join(available)}")

    cwd = _get_cwd()
    state_path = ProjectLayout(cwd).state_json

    with file_lock(state_path):
        try:
            state = _json.loads(state_path.read_text(encoding="utf-8"))
        except OSError:
            state = {}
        except _json.JSONDecodeError as e:
            _error(f"Malformed state.json: {e}")

        state["domain"] = name
        save_state_json_locked(cwd, state)

    _output({"domain": name, "status": "active"})
