"""Install and uninstall subcommands."""

from __future__ import annotations

import typer
from rich.table import Table

import grd.cli._helpers as _cli_helpers
from grd.cli._helpers import (
    _GRD_BANNER,
    _INSTALL_ACCENT_COLOR,
    _INSTALL_LOGO_COLOR,
    _INSTALL_META_COLOR,
    _INSTALL_TITLE_COLOR,
    _error,
    _format_display_path,
    _format_install_header_lines,
    _format_runtime_list,
    _get_cwd,
    _output,
    _render_install_choice_prompt,
    _render_install_option_line,
    _resolve_cli_target_dir,
    _unique_preserving_order,
    app,
    console,
)


def _prompt_runtimes(*, action: str = "install") -> list[str]:
    """Interactive runtime selection. Returns list of selected runtime names."""
    from rich.prompt import Prompt

    from grd.adapters import get_adapter, list_runtimes

    runtimes = list_runtimes()
    adapters = {runtime: get_adapter(runtime) for runtime in runtimes}
    label_width = max(len(adapter.display_name) for adapter in adapters.values())
    all_label = "All runtimes"
    label_width = max(label_width, len(all_label))
    console.print(f"\n[bold {_INSTALL_TITLE_COLOR}]Select runtime(s) to {action}[/]\n")
    for i, rt in enumerate(runtimes, 1):
        adapter = adapters[rt]
        console.print(_render_install_option_line(i, adapter.display_name, rt, label_width=label_width))
    console.print(_render_install_option_line(len(runtimes) + 1, all_label, label_width=label_width))

    console.print()
    choice = Prompt.ask(_render_install_choice_prompt(), default="1", show_default=False)

    try:
        idx = int(choice)
    except ValueError:
        normalized = choice.strip().casefold()
        exact_matches = [
            runtime_name
            for runtime_name, adapter in adapters.items()
            if normalized
            in {
                runtime_name.casefold(),
                adapter.display_name.casefold(),
                *(alias.casefold() for alias in adapter.selection_aliases),
            }
        ]
        if len(exact_matches) == 1:
            return exact_matches

        fuzzy_matches = [
            runtime_name
            for runtime_name, adapter in adapters.items()
            if normalized
            and any(
                normalized in candidate
                for candidate in (
                    runtime_name.casefold(),
                    adapter.display_name.casefold(),
                    *(alias.casefold() for alias in adapter.selection_aliases),
                )
            )
        ]
        if len(fuzzy_matches) == 1:
            return fuzzy_matches
        if len(fuzzy_matches) > 1:
            _error(f"Ambiguous selection: {choice!r}. Matches: {', '.join(fuzzy_matches)}")
        _error(f"Invalid selection: {choice!r}")
        return []  # unreachable

    if idx == len(runtimes) + 1:
        return runtimes
    if 1 <= idx <= len(runtimes):
        return [runtimes[idx - 1]]

    _error(f"Invalid selection: {idx}")
    return []  # unreachable


def _location_example(runtimes: list[str], *, is_global: bool) -> str:
    """Return a representative install location example for the selected runtime set."""
    if len(runtimes) != 1:
        return "one config dir per runtime"

    from grd.adapters import get_adapter

    adapter = get_adapter(runtimes[0])
    target = adapter.resolve_target_dir(is_global, _get_cwd())
    return _format_display_path(target)


def _prompt_location(runtimes: list[str], *, action: str = "install") -> bool:
    """Interactive location selection. Returns True for global, False for local."""
    from rich.prompt import Prompt

    label = "Install" if action == "install" else "Uninstall"
    local_example = _location_example(runtimes, is_global=False)
    global_example = _location_example(runtimes, is_global=True)
    label_width = max(len("Local"), len("Global"))
    console.print(f"\n[bold {_INSTALL_TITLE_COLOR}]{label} location[/]\n")
    console.print(
        _render_install_option_line(1, "Local", "current project only", local_example, label_width=label_width)
    )
    console.print(_render_install_option_line(2, "Global", "all projects", global_example, label_width=label_width))

    console.print()
    choice = Prompt.ask(_render_install_choice_prompt(), default="1", show_default=False)
    normalized = choice.strip().lower()
    if normalized in {"1", "local"}:
        return False
    if normalized in {"2", "global"}:
        return True
    _error(f"Invalid selection: {choice!r}")
    return False  # unreachable


def _install_single_runtime(
    runtime_name: str,
    *,
    is_global: bool,
    target_dir_override: str | None = None,
) -> dict[str, object]:
    """Install GRD for a single runtime. Returns install result dict."""
    from grd.adapters import get_adapter
    from grd.version import resolve_install_grd_root

    adapter = get_adapter(runtime_name)
    grd_root = resolve_install_grd_root(_get_cwd())

    if target_dir_override:
        dest = _resolve_cli_target_dir(target_dir_override)
    else:
        dest = adapter.resolve_target_dir(is_global, _get_cwd())

    return adapter.install(
        grd_root,
        dest,
        is_global=is_global,
        explicit_target=target_dir_override is not None,
    )


def _print_install_summary(results: list[tuple[str, dict[str, object]]]) -> None:
    """Print a rich summary table of install results."""
    from grd.adapters import get_adapter

    console.print()
    table = Table(
        title="Install Summary",
        title_style=f"italic {_INSTALL_ACCENT_COLOR}",
        show_header=True,
        header_style=f"bold {_INSTALL_ACCENT_COLOR}",
    )
    table.add_column("Runtime", style="bold")
    table.add_column("Target")
    table.add_column("Status")

    for runtime_name, result in results:
        adapter = get_adapter(runtime_name)
        target = _format_display_path(result.get("target"))
        agents = result.get("agents", 0)
        commands = result.get("commands", 0)
        table.add_row(
            adapter.display_name,
            target,
            f"[green]\u2713[/] {agents} agents, {commands} commands",
        )

    console.print(table)

    # Post-install next steps
    if results:
        next_step_entries: list[tuple[str, str, str, str, str]] = []
        seen_runtime_names: set[str] = set()
        for runtime_name, _result in results:
            if runtime_name in seen_runtime_names:
                continue
            seen_runtime_names.add(runtime_name)
            adapter = get_adapter(runtime_name)
            next_step_entries.append(
                (
                    adapter.display_name,
                    adapter.launch_command,
                    adapter.help_command,
                    adapter.new_project_command,
                    adapter.map_research_command,
                )
            )

        console.print()
        console.print("[bold]Next steps[/]")
        if len(next_step_entries) == 1:
            display_name, launch_command, help_command, new_project_command, map_research_command = next_step_entries[0]
            console.print(
                f"1. Open [bold]{display_name}[/] from your system terminal "
                f"([{_INSTALL_ACCENT_COLOR} bold]{launch_command}[/]).",
                soft_wrap=True,
            )
            console.print(
                f"2. Run [{_INSTALL_ACCENT_COLOR} bold]{help_command}[/] for the command list.",
                soft_wrap=True,
            )
            console.print(
                "3. Start with "
                f"[{_INSTALL_ACCENT_COLOR} bold]{new_project_command}[/] for a new project "
                "or "
                f"[{_INSTALL_ACCENT_COLOR} bold]{map_research_command}[/] for existing work.",
                soft_wrap=True,
            )
        else:
            for (
                display_name,
                launch_command,
                help_command,
                new_project_command,
                map_research_command,
            ) in next_step_entries:
                console.print(
                    f"- {display_name} "
                    f"([{_INSTALL_ACCENT_COLOR} bold]{launch_command}[/]), then "
                    f"[{_INSTALL_ACCENT_COLOR} bold]{help_command}[/], then "
                    f"[{_INSTALL_ACCENT_COLOR} bold]{new_project_command}[/] "
                    f"or [{_INSTALL_ACCENT_COLOR} bold]{map_research_command}[/]",
                    soft_wrap=True,
                )
        console.print()


def _validate_all_runtime_selection(action: str, runtimes: list[str] | None, use_all: bool) -> None:
    """Reject ambiguous runtime selection between explicit args and --all."""
    if use_all and runtimes:
        _error(f"Cannot combine explicit runtimes with --all for {action}")


def _validate_target_dir_runtime_selection(action: str, runtimes: list[str], target_dir: str | None) -> None:
    """Reject explicit target-dir usage when multiple runtimes are selected."""
    if target_dir and len(runtimes) != 1:
        _error(f"--target-dir requires exactly one runtime for {action}")


@app.command("install")
def install(
    runtimes: list[str] | None = typer.Argument(
        None,
        help="Runtime(s) to install. Omit for interactive selection.",
    ),
    install_all: bool = typer.Option(False, "--all", help="Install for all supported runtimes"),
    local_install: bool = typer.Option(False, "--local", help="Install into the local runtime config dir"),
    global_install: bool = typer.Option(False, "--global", help="Install into the global runtime config dir"),
    target_dir: str | None = typer.Option(None, "--target-dir", help="Override target config directory"),
    force_statusline: bool = typer.Option(False, "--force-statusline", help="Overwrite existing statusline config"),
) -> None:
    """Install GRD skills, agents, and hooks into runtime config directories.

    Run without arguments for interactive mode. Specify runtime name(s) or --all for batch mode.

    Examples::

        grd install                        # interactive
        grd install <runtime>              # single runtime, local
        grd install <runtime-a> <runtime-b>
        grd install --all --global         # all runtimes, global
    """
    from rich.progress import Progress, SpinnerColumn, TextColumn

    from grd.adapters import get_adapter, list_runtimes

    if global_install and local_install:
        _error("Cannot specify both --global and --local")
        return  # unreachable
    _validate_all_runtime_selection("install", runtimes, install_all)

    # Resolve which runtimes to install
    selected: list[str]
    if install_all:
        selected = list_runtimes()
    elif runtimes:
        # Validate all runtime names
        supported = list_runtimes()
        for rt in runtimes:
            if rt not in supported:
                _error(f"Unknown runtime {rt!r}. Supported: {', '.join(supported)}")
                return  # unreachable
        selected = _unique_preserving_order(list(runtimes))
    else:
        # Interactive mode
        from grd.version import resolve_active_version

        console.print(_GRD_BANNER, style=f"bold {_INSTALL_LOGO_COLOR}")
        console.print()
        header_line, attribution_line = _format_install_header_lines(resolve_active_version(_get_cwd()))
        console.print(header_line, style=f"bold {_INSTALL_TITLE_COLOR}", markup=False, highlight=False)
        console.print(attribution_line, style=f"dim {_INSTALL_META_COLOR}", markup=False, highlight=False)
        console.print()
        selected = _prompt_runtimes()

    _validate_target_dir_runtime_selection("install", selected, target_dir)

    # Resolve location
    if target_dir:
        is_global = False  # --target-dir implies a specific path
    elif global_install:
        is_global = True
    elif local_install:
        is_global = False
    elif not runtimes and not install_all:
        # Interactive mode -- ask for location
        is_global = _prompt_location(selected)
    else:
        # Non-interactive default: local
        is_global = False

    location_label = "global" if is_global else "local"
    if not _cli_helpers._raw:
        console.print(f"\n[bold]Installing GRD ({location_label}) for: {_format_runtime_list(selected)}[/]\n")

    # Install each runtime with progress
    results: list[tuple[str, dict[str, object]]] = []
    failures: list[tuple[str, str]] = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        disable=_cli_helpers._raw,
    ) as progress:
        for rt in selected:
            adapter = get_adapter(rt)
            task = progress.add_task(f"Installing {adapter.display_name}...", total=None)
            try:
                result = _install_single_runtime(rt, is_global=is_global, target_dir_override=target_dir)
                adapter.finalize_install(result, force_statusline=force_statusline)
                results.append((rt, result))
                progress.update(task, description=f"[green]\u2713[/] {adapter.display_name}")
            except Exception as exc:
                failures.append((rt, str(exc)))
                progress.update(task, description=f"[red]\u2717[/] {adapter.display_name}: {exc}")

    if _cli_helpers._raw:
        _output(
            {
                "installed": [{"runtime": rt, **res} for rt, res in results],
                "failed": [{"runtime": rt, "error": err} for rt, err in failures],
            }
        )
    else:
        _print_install_summary(results)

    if failures:
        raise typer.Exit(code=1)


@app.command("uninstall")
def uninstall(
    runtimes: list[str] | None = typer.Argument(
        None,
        help="Runtime(s) to uninstall. Omit for interactive selection.",
    ),
    uninstall_all: bool = typer.Option(False, "--all", help="Uninstall from all runtimes"),
    local_uninstall: bool = typer.Option(False, "--local", help="Uninstall from local config"),
    global_uninstall: bool = typer.Option(False, "--global", help="Uninstall from global config"),
    target_dir: str | None = typer.Option(None, "--target-dir", help="Override target directory (testing)"),
) -> None:
    """Remove GRD skills, agents, and hooks from runtime config directories.

    Examples::

        grd uninstall <runtime> --local
        grd uninstall --all --global
    """
    from rich.prompt import Confirm

    from grd.adapters import get_adapter, list_runtimes

    if global_uninstall and local_uninstall:
        _error("Cannot specify both --global and --local")
        return
    _validate_all_runtime_selection("uninstall", runtimes, uninstall_all)

    # Resolve runtimes
    selected: list[str]
    if uninstall_all:
        selected = list_runtimes()
    elif runtimes:
        supported = list_runtimes()
        for rt in runtimes:
            if rt not in supported:
                _error(f"Unknown runtime {rt!r}. Supported: {', '.join(supported)}")
                return
        selected = _unique_preserving_order(list(runtimes))
    else:
        selected = _prompt_runtimes(action="uninstall")

    _validate_target_dir_runtime_selection("uninstall", selected, target_dir)

    # Resolve location (skip prompts when --target-dir is explicit)
    if target_dir:
        is_global = True  # irrelevant when target_dir is set
    elif not global_uninstall and not local_uninstall:
        is_global = _prompt_location(selected, action="uninstall")
    else:
        is_global = global_uninstall

    if not target_dir:
        location_label = "global" if is_global else "local"
        runtime_names = _format_runtime_list(selected)
        if not Confirm.ask(f"Remove GRD from {runtime_names} ({location_label})?", default=False):
            console.print("[dim]Cancelled.[/]")
            raise typer.Exit()

    removed_results: list[tuple[str, dict[str, object]]] = []
    for rt in selected:
        adapter = get_adapter(rt)
        target = (
            _resolve_cli_target_dir(target_dir) if target_dir else adapter.resolve_target_dir(is_global, _get_cwd())
        )
        if not target.is_dir():
            if not _cli_helpers._raw:
                console.print(
                    f"  [yellow]\u2298[/] {adapter.display_name} \u2014 not installed at {_format_display_path(target)}"
                )
            continue
        result = adapter.uninstall(target)
        removed_items = result.get("removed", [])
        if not _cli_helpers._raw:
            if removed_items:
                console.print(
                    f"  [green]\u2713[/] {adapter.display_name} \u2014 removed: {', '.join(str(r) for r in removed_items)}"
                )
            else:
                console.print(f"  [dim]\u2298[/] {adapter.display_name} \u2014 nothing to remove")
        removed_results.append((rt, result))

    if _cli_helpers._raw:
        _output({"uninstalled": [{"runtime": rt, **res} for rt, res in removed_results]})
