"""Tests for ``grd lean demo`` (ge-e2c1 / P1).

Contract from the bead:
  (a) screen-shareable
  (b) completes in <5 min wall
  (c) ``--dry-run`` labels every mocked / skipped stage
  (d) only flags are ``--dry-run`` and ``--template``

These tests enforce the contract directly: a single click-through of the
dry-run must finish in well under 5 minutes (we budget 30 s as a canary),
every stage carries a visible status label, dry-run writes nothing to disk,
and live mode performs exactly one filesystem side effect — stamping the
template.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from grd.cli import app
from grd.cli.lean import EXIT_INPUT_ERROR
from grd.core.lean.demo import DEFAULT_TEMPLATE, DemoResult, run_demo

runner = CliRunner()


# ─── Core: run_demo ─────────────────────────────────────────────────────────


def test_run_demo_dry_run_writes_nothing(tmp_path: Path) -> None:
    before = sorted(tmp_path.rglob("*"))
    result = run_demo(tmp_path, dry_run=True)
    after = sorted(tmp_path.rglob("*"))
    assert before == after, "dry-run must not touch the filesystem"
    assert result.dry_run is True
    assert result.project_dir is None
    assert result.stamp_result is None


def test_run_demo_live_stamps_exactly_once(tmp_path: Path) -> None:
    result = run_demo(tmp_path, dry_run=False)
    assert result.dry_run is False
    assert result.project_dir is not None
    project_dir = Path(result.project_dir)
    assert project_dir.is_dir()
    # The stamp drops the four canonical simple-mechanics files.
    stamped = {p.name for p in (project_dir / ".grd").iterdir()}
    assert stamped >= {"PROJECT.md", "CONVENTIONS.md", "ROADMAP.md", "state.json"}


def test_run_demo_emits_five_stages_in_section_7_order(tmp_path: Path) -> None:
    result = run_demo(tmp_path, dry_run=True)
    assert [s.name for s in result.stages] == [
        "new-project",
        "lean-bootstrap",
        "progress-pre",
        "verify-claim",
        "progress-post",
    ]


def test_run_demo_every_stage_has_status_label(tmp_path: Path) -> None:
    """(c) from the bead: no stage may ship without a label."""
    result = run_demo(tmp_path, dry_run=True)
    for stage in result.stages:
        assert stage.status in {"real", "mock", "skipped"}


def test_run_demo_skipped_stages_carry_run_live_note(tmp_path: Path) -> None:
    """Every SKIPPED stage must tell the viewer how to run it live."""
    result = run_demo(tmp_path, dry_run=True)
    for stage in result.stages:
        if stage.status == "skipped":
            assert stage.note, f"{stage.name}: SKIPPED stage must name a live command"


def test_run_demo_never_claims_live_verify_claim_ran(tmp_path: Path) -> None:
    """Don't lie: the live LLM + Lean pipeline is always SKIPPED.

    Running it live exceeds the 5-min budget and costs API tokens; the
    demo must mark it skipped unambiguously.
    """
    result = run_demo(tmp_path, dry_run=True)
    (verify_claim,) = [s for s in result.stages if s.name == "verify-claim"]
    assert verify_claim.status == "skipped"
    assert "verify-claim" in (verify_claim.note or "")


def test_run_demo_bootstrap_always_skipped(tmp_path: Path) -> None:
    """The installer is a first-run-only affair; never auto-run in the demo."""
    for dry in (True, False):
        result = run_demo(tmp_path / f"dry-{dry}", dry_run=dry)
        (boot,) = [s for s in result.stages if s.name == "lean-bootstrap"]
        assert boot.status == "skipped"


def test_run_demo_rejects_unknown_template(tmp_path: Path) -> None:
    with pytest.raises(ValueError) as excinfo:
        run_demo(tmp_path, template="does-not-exist", dry_run=True)
    assert "does-not-exist" in str(excinfo.value)


def test_run_demo_completes_well_under_5min(tmp_path: Path) -> None:
    """(b) from the bead: 5-min budget. We budget 30s as a canary.

    Live mode includes the single real stamp; dry-run is pure computation.
    Both should finish in a fraction of a second — 30 s gives huge headroom
    before CI would flag regression.
    """
    started = time.monotonic()
    run_demo(tmp_path, dry_run=False)
    elapsed = time.monotonic() - started
    assert elapsed < 30.0, f"demo took {elapsed:.1f}s — blowing 5-min contract"


def test_run_demo_narration_matches_section_7_fixture(tmp_path: Path) -> None:
    """(a) screen-shareable: the fixture must match the published §7 text."""
    result = run_demo(tmp_path, dry_run=True)
    verify_claim = next(s for s in result.stages if s.name == "verify-claim")
    # Spot-check the most visible lines of the §7 transcript — if §7 changes,
    # this fails loudly and points the updater at demo.py.
    assert "energy_conserved" in verify_claim.narration
    assert "Faithfulness: ACCEPT" in verify_claim.narration
    progress_post = next(s for s in result.stages if s.name == "progress-post")
    assert "leanok" in progress_post.narration
    assert "blueprint" in progress_post.narration


# ─── CLI: grd lean demo ─────────────────────────────────────────────────────


def test_cli_demo_dry_run_prints_all_status_labels(tmp_path: Path) -> None:
    result = runner.invoke(app, ["--cwd", str(tmp_path), "lean", "demo", "--dry-run"])
    assert result.exit_code == 0, result.stdout
    # Labels must all appear so a screen-share viewer can see what's real.
    assert "[MOCK]" in result.stdout
    assert "[SKIPPED]" in result.stdout
    # Every stage's command line must appear.
    for cmd_fragment in (
        "new-project --template simple-mechanics",
        "/grd:lean-bootstrap --for physicist",
        "/grd:verify-claim",
        "/grd:progress",
    ):
        assert cmd_fragment in result.stdout


def test_cli_demo_dry_run_touches_no_files(tmp_path: Path) -> None:
    before = sorted(tmp_path.rglob("*"))
    result = runner.invoke(app, ["--cwd", str(tmp_path), "lean", "demo", "--dry-run"])
    after = sorted(tmp_path.rglob("*"))
    assert result.exit_code == 0
    assert before == after


def test_cli_demo_live_stamps_template(tmp_path: Path) -> None:
    result = runner.invoke(app, ["--cwd", str(tmp_path), "lean", "demo"])
    assert result.exit_code == 0, result.stdout
    assert (tmp_path / ".grd" / "demo" / DEFAULT_TEMPLATE / ".grd" / "PROJECT.md").exists()


def test_cli_demo_raw_emits_valid_json(tmp_path: Path) -> None:
    result = runner.invoke(app, ["--raw", "--cwd", str(tmp_path), "lean", "demo", "--dry-run"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["template"] == DEFAULT_TEMPLATE
    assert payload["dry_run"] is True
    assert len(payload["stages"]) == 5
    assert {s["status"] for s in payload["stages"]} <= {"real", "mock", "skipped"}


def test_cli_demo_rejects_unknown_template(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "lean", "demo", "--template", "no-such-template"],
    )
    assert result.exit_code == EXIT_INPUT_ERROR, result.stdout


def test_cli_demo_only_accepts_two_flags(tmp_path: Path) -> None:
    """(d) from the bead: no flags other than --dry-run and --template."""
    result = runner.invoke(app, ["--cwd", str(tmp_path), "lean", "demo", "--help"])
    assert result.exit_code == 0, result.stdout
    help_text = result.stdout
    # These two must be present.
    assert "--dry-run" in help_text
    assert "--template" in help_text
    # And no third-party flag has crept in.
    forbidden_flags = ["--verbose", "--events", "--json", "--force", "--yes"]
    for flag in forbidden_flags:
        assert flag not in help_text, f"unexpected flag {flag} in demo help"


def test_cli_demo_has_help_headline(tmp_path: Path) -> None:
    result = runner.invoke(app, ["lean", "demo", "--help"])
    assert result.exit_code == 0
    # Rome-persona framing must show up in help so `grd lean --help` makes
    # the entry point obvious.
    assert "demo" in result.stdout.lower()


def test_cli_demo_listed_in_lean_subcommands() -> None:
    result = runner.invoke(app, ["lean", "--help"])
    assert result.exit_code == 0
    assert "demo" in result.stdout


def test_demoresult_dataclass_serializes_for_raw_output(tmp_path: Path) -> None:
    result = run_demo(tmp_path, dry_run=True)
    assert isinstance(result, DemoResult)
    # Every stage is frozen so downstream callers can trust it.
    import dataclasses

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.stages[0].status = "real"  # type: ignore[misc]
