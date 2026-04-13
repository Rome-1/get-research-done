"""Verification suite subcommands."""

from __future__ import annotations

from pathlib import Path

import typer

from grd.cli._helpers import _get_cwd, _output

verify_app = typer.Typer(help="Verification checks on plans, summaries, and artifacts")


@verify_app.command("summary")
def verify_summary(
    path: str = typer.Argument(..., help="Path to SUMMARY.md"),
    check_count: int = typer.Option(2, "--check-count", help="Max file references to spot-check for existence"),
) -> None:
    """Verify a SUMMARY.md file."""
    from grd.core.frontmatter import verify_summary

    result = verify_summary(_get_cwd(), Path(path), check_file_count=check_count)
    _output(result)
    if not result.passed:
        raise typer.Exit(code=1)


@verify_app.command("plan")
def verify_plan(
    path: str = typer.Argument(..., help="Path to plan file"),
) -> None:
    """Verify plan file structure."""
    from grd.core.frontmatter import verify_plan_structure

    result = verify_plan_structure(_get_cwd(), Path(path))
    _output(result)
    if not result.valid:
        raise typer.Exit(code=1)


@verify_app.command("phase")
def verify_phase(
    phase: str = typer.Argument(..., help="Phase number"),
) -> None:
    """Verify phase completeness (all plans have summaries, etc.)."""
    from grd.core.frontmatter import verify_phase_completeness

    result = verify_phase_completeness(_get_cwd(), phase)
    _output(result)
    if not result.complete:
        raise typer.Exit(code=1)


@verify_app.command("references")
def verify_references(
    path: str = typer.Argument(..., help="Path to file"),
) -> None:
    """Verify all internal references resolve."""
    from grd.core.frontmatter import verify_references

    result = verify_references(_get_cwd(), Path(path))
    _output(result)
    if not result.valid:
        raise typer.Exit(code=1)


@verify_app.command("commits")
def verify_commits(
    hashes: list[str] = typer.Argument(..., help="Commit hashes to verify"),
) -> None:
    """Verify that commit hashes exist in git history."""
    from grd.core.frontmatter import verify_commits

    result = verify_commits(_get_cwd(), hashes)
    _output(result)
    if not result.all_valid:
        raise typer.Exit(code=1)


@verify_app.command("artifacts")
def verify_artifacts(
    plan_path: str = typer.Argument(..., help="Path to plan file"),
) -> None:
    """Verify all artifacts referenced in a plan exist."""
    from grd.core.frontmatter import verify_artifacts

    result = verify_artifacts(_get_cwd(), Path(plan_path))
    _output(result)
    if not result.all_passed:
        raise typer.Exit(code=1)


@verify_app.command("formal-coverage")
def verify_formal_coverage(
    state_path: str | None = typer.Option(
        None, "--state", help="Path to state.json (defaults to project state)"
    ),
    total_claims: int | None = typer.Option(
        None,
        "--total-claims",
        help="Total claim count to use as blueprint completion denominator",
    ),
) -> None:
    """Report formal proof coverage (checks 5.20/5.21) from state.json."""
    import json

    from grd.core.constants import ProjectLayout
    from grd.core.verification_coverage import formal_proof_coverage_from_state

    if state_path:
        target = Path(state_path)
        if not target.is_absolute():
            target = _get_cwd() / target
    else:
        target = ProjectLayout(_get_cwd()).state_json

    try:
        raw = target.read_text(encoding="utf-8")
    except OSError:
        data: object = {}
    else:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise typer.BadParameter(f"Malformed state.json at {target}: {exc}") from exc

    result = formal_proof_coverage_from_state(data, total_claims=total_claims)
    _output(result)
