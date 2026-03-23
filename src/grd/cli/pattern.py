"""Error pattern library subcommands."""

from __future__ import annotations

from pathlib import Path

import typer

from grd.cli._helpers import _get_cwd, _output, console

pattern_app = typer.Typer(help="Error pattern library (8 categories, 13 domains)")


def _resolve_patterns_root() -> Path:
    """Resolve pattern library root respecting GRD_PATTERNS_ROOT env var.

    Uses the same resolution order as grd.core.patterns.patterns_root:
    GRD_PATTERNS_ROOT env > GRD_DATA_DIR env > ~/.grd/learned-patterns.
    """
    from grd.core.patterns import patterns_root

    return patterns_root(specs_root=_get_cwd())


@pattern_app.command("init")
def pattern_init() -> None:
    """Initialize the error pattern library."""
    from grd.core.patterns import pattern_init

    _output({"path": str(pattern_init(root=_resolve_patterns_root()))})


@pattern_app.command("add")
def pattern_add(
    domain: str | None = typer.Option(None, "--domain", help="Physics domain"),
    category: str | None = typer.Option(None, "--category", help="Error category"),
    severity: str | None = typer.Option(None, "--severity", help="Severity level"),
    title: str | None = typer.Option(None, "--title", help="Pattern title"),
    description: str | None = typer.Option(None, "--description", help="Pattern description"),
    detection: str | None = typer.Option(None, "--detection", help="How to detect"),
    prevention: str | None = typer.Option(None, "--prevention", help="How to prevent"),
    example: str | None = typer.Option(None, "--example", help="Example"),
    test_value: str | None = typer.Option(None, "--test-value", help="Test value"),
) -> None:
    """Add a new error pattern."""
    from grd.core.patterns import pattern_add

    _output(
        pattern_add(
            domain=domain or "",
            title=title or "",
            category=category or "conceptual-error",
            severity=severity or "medium",
            description=description or "",
            detection=detection or "",
            prevention=prevention or "",
            example=example or "",
            test_value=test_value or "",
            root=_resolve_patterns_root(),
        )
    )


def _pattern_table(patterns: list, title: str = "Error Patterns") -> None:
    """Render a list of pattern entries as a Rich table."""
    from rich.table import Table

    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("ID")
    table.add_column("Domain")
    table.add_column("Category")
    table.add_column("Severity")
    table.add_column("Title")
    table.add_column("Confidence")
    for p in patterns:
        entry = p if isinstance(p, dict) else (p.model_dump() if hasattr(p, "model_dump") else vars(p))
        sev = entry.get("severity", "")
        sev_styled = {"critical": "[red]critical[/]", "high": "[yellow]high[/]", "medium": "medium", "low": "[dim]low[/]"}.get(sev, sev)
        table.add_row(
            entry.get("id", ""),
            entry.get("domain", ""),
            entry.get("category", ""),
            sev_styled,
            entry.get("title", ""),
            entry.get("confidence", ""),
        )
    console.print(table)


@pattern_app.command("list")
def pattern_list(
    domain: str | None = typer.Option(None, "--domain", help="Filter by domain"),
    category: str | None = typer.Option(None, "--category", help="Filter by category"),
    severity: str | None = typer.Option(None, "--severity", help="Filter by severity"),
) -> None:
    """List error patterns with optional filters."""
    from grd.cli._helpers import _raw
    from grd.core.patterns import pattern_list

    result = pattern_list(domain=domain, category=category, severity=severity, root=_resolve_patterns_root())
    if _raw:
        _output(result)
        return

    if not result.patterns:
        console.print("[dim]No patterns found. Use 'grd pattern seed' to bootstrap patterns.[/]")
        return
    _pattern_table(result.patterns, title=f"Error Patterns ({result.count} total)")


@pattern_app.command("search")
def pattern_search(
    query: list[str] = typer.Argument(..., help="Search query"),
) -> None:
    """Search error patterns by text."""
    from grd.cli._helpers import _raw
    from grd.core.patterns import pattern_search

    result = pattern_search(" ".join(query), root=_resolve_patterns_root())
    if _raw:
        _output(result)
        return

    if not result.matches:
        console.print(f"[dim]No patterns matched '{result.query}'.[/]")
        return
    _pattern_table(result.matches, title=f"Search results for '{result.query}' ({result.count} matches)")


@pattern_app.command("promote")
def pattern_promote(
    pattern_id: str = typer.Argument(..., help="Pattern ID to promote"),
) -> None:
    """Promote a pattern's confidence level (single_observation -> confirmed -> systematic)."""
    from grd.core.patterns import pattern_promote

    _output(pattern_promote(pattern_id, root=_resolve_patterns_root()))


@pattern_app.command("seed")
def pattern_seed(
    domain: str | None = typer.Option(None, "--domain", help="Domain pack to seed patterns from (default: active domain)"),
) -> None:
    """Seed the pattern library with common error patterns for the active domain."""
    from grd.core.patterns import pattern_seed

    _output(pattern_seed(root=_resolve_patterns_root(), domain_name=domain))
