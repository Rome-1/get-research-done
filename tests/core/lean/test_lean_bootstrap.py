"""Tests for grd.core.lean.bootstrap.

We stub ``_run`` (and friends) so the tests never touch the network or
modify the host. The orchestrator contract we care about:

  * stage results and persisted state line up
  * failures in one stage don't abort later stages
  * consent-gated stages honour prior-recorded answers
  * ``--dry-run`` leaves state annotated but doesn't invoke subprocesses
  * ``uninstall`` enumerates the right paths
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from grd.core.lean import bootstrap
from grd.core.lean.env import env_file_path, load_env
from grd.core.lean.protocol import BootstrapStageResult


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / ".grd").mkdir()
    return tmp_path


def _ok(name: str, **kw: object) -> BootstrapStageResult:
    return BootstrapStageResult(name=name, status="ok", **kw)  # type: ignore[arg-type]


# ─── Protocol / options ─────────────────────────────────────────────────────


def test_bootstrap_options_has_sensible_defaults() -> None:
    opts = bootstrap.BootstrapOptions()
    assert opts.yes is False
    assert opts.with_graphviz is False
    assert opts.with_tectonic is False
    assert opts.with_mathlib_cache is False
    assert opts.with_leandojo is False
    assert opts.dry_run is False
    assert opts.force is False


# ─── Dry-run end-to-end ─────────────────────────────────────────────────────


def test_dry_run_marks_every_required_stage_ok_without_subprocess(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Make detection return "nothing installed" so every stage has to proceed
    # to its dry-run branch. Same for pip-importability and PATH lookups so
    # the host's actual pdflatex / dot don't bleed into the test.
    monkeypatch.setattr(
        bootstrap,
        "detect_toolchain",
        lambda *, env=None: _empty_toolchain(),
    )
    monkeypatch.setattr(bootstrap, "_missing_pip_packages", lambda: list(bootstrap._PIP_PACKAGES))
    monkeypatch.setattr(bootstrap.shutil, "which", lambda _name: None)
    # Any accidental _run call should fail the test — dry-run must never shell out.
    monkeypatch.setattr(bootstrap, "_run", _explode)

    report = bootstrap.run_bootstrap(project, options=bootstrap.BootstrapOptions(dry_run=True))

    assert report.ok is True
    names = [s.name for s in report.stages]
    assert names == [
        "elan",
        "toolchain",
        "pantograph",
        "graphviz",
        "tectonic",
        "mathlib_cache",
        "leandojo",
    ]
    # Required stages all dry-run to ``ok``; opt-ins stay ``skipped_not_requested``.
    statuses = {s.name: s.status for s in report.stages}
    assert statuses["elan"] == "ok"
    assert statuses["toolchain"] == "ok"
    assert statuses["pantograph"] == "ok"
    assert statuses["graphviz"] == "skipped_not_requested"
    assert statuses["tectonic"] == "skipped_not_requested"
    assert statuses["mathlib_cache"] == "skipped_not_requested"
    assert statuses["leandojo"] == "skipped_not_requested"


def test_state_persisted_after_each_stage(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bootstrap, "detect_toolchain", lambda *, env=None: _empty_toolchain())
    monkeypatch.setattr(bootstrap, "_missing_pip_packages", lambda: list(bootstrap._PIP_PACKAGES))
    monkeypatch.setattr(bootstrap.shutil, "which", lambda _name: None)
    monkeypatch.setattr(bootstrap, "_run", _explode)

    bootstrap.run_bootstrap(project, options=bootstrap.BootstrapOptions(dry_run=True))

    persisted = load_env(project)
    assert persisted["schema_version"] == bootstrap.BOOTSTRAP_SCHEMA_VERSION
    assert persisted["in_progress"] is False
    assert isinstance(persisted["stages"], list)
    assert [s["name"] for s in persisted["stages"]] == [
        "elan",
        "toolchain",
        "pantograph",
        "graphviz",
        "tectonic",
        "mathlib_cache",
        "leandojo",
    ]
    assert isinstance(persisted["last_report"], dict)
    assert persisted["last_report"]["ok"] is True


# ─── Skip-when-installed ────────────────────────────────────────────────────


def test_elan_stage_skips_when_already_on_path(monkeypatch: pytest.MonkeyPatch, project: Path) -> None:
    tc = _toolchain(elan_path="/home/x/.elan/bin/elan", elan_version="elan 3.0.0")
    monkeypatch.setattr(bootstrap, "detect_toolchain", lambda *, env=None: tc)
    monkeypatch.setattr(bootstrap, "_run", _explode)

    result = bootstrap._stage_elan(bootstrap.BootstrapOptions())
    assert result.status == "skipped_already_installed"
    assert result.path == "/home/x/.elan/bin/elan"
    assert result.version == "elan 3.0.0"


def test_toolchain_stage_skips_when_lean_present(monkeypatch: pytest.MonkeyPatch, project: Path) -> None:
    tc = _toolchain(lean_path="/usr/bin/lean", lean_version="Lean 4.13.0")
    monkeypatch.setattr(bootstrap, "detect_toolchain", lambda *, env=None: tc)
    monkeypatch.setattr(bootstrap, "_run", _explode)

    result = bootstrap._stage_toolchain(bootstrap.BootstrapOptions(), project)
    assert result.status == "skipped_already_installed"
    assert result.version == "Lean 4.13.0"


def test_pantograph_stage_skips_when_all_packages_importable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap, "_missing_pip_packages", lambda: [])
    monkeypatch.setattr(bootstrap, "_run", _explode)

    result = bootstrap._stage_pantograph(bootstrap.BootstrapOptions())
    assert result.status == "skipped_already_installed"


# ─── Graphviz: degrade without user PM ─────────────────────────────────────


def test_graphviz_degrades_when_no_user_package_manager(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap.shutil, "which", lambda name: None)
    monkeypatch.setattr(bootstrap, "_has_user_package_manager", lambda: None)

    result = bootstrap._stage_graphviz(bootstrap.BootstrapOptions(with_graphviz=True))
    assert result.status == "degraded"
    assert "ASCII" in result.detail or "graphviz" in result.detail


def test_graphviz_skipped_not_requested_when_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bootstrap.shutil, "which", lambda name: None)

    result = bootstrap._stage_graphviz(bootstrap.BootstrapOptions(with_graphviz=False))
    assert result.status == "skipped_not_requested"


def test_graphviz_skipped_when_dot_already_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        bootstrap.shutil,
        "which",
        lambda name: "/usr/local/bin/dot" if name == "dot" else None,
    )

    result = bootstrap._stage_graphviz(bootstrap.BootstrapOptions(with_graphviz=True))
    assert result.status == "skipped_already_installed"
    assert result.path == "/usr/local/bin/dot"


# ─── Tectonic: prefers any existing LaTeX compiler ─────────────────────────


def test_tectonic_skipped_when_pdflatex_already_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        bootstrap.shutil,
        "which",
        lambda name: "/usr/bin/pdflatex" if name == "pdflatex" else None,
    )

    result = bootstrap._stage_tectonic(bootstrap.BootstrapOptions(with_tectonic=True))
    assert result.status == "skipped_already_installed"
    assert "pdflatex" in (result.path or "")


def test_tectonic_degrades_without_cargo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bootstrap.shutil, "which", lambda name: None)

    result = bootstrap._stage_tectonic(bootstrap.BootstrapOptions(with_tectonic=True))
    assert result.status == "degraded"
    assert "cargo" in result.detail


# ─── Consent-gated stages ──────────────────────────────────────────────────


def test_mathlib_cache_respects_prior_never_consent(monkeypatch: pytest.MonkeyPatch, project: Path) -> None:
    prior = {"consent": {"mathlib_cache": "never"}}
    monkeypatch.setattr(bootstrap, "_run", _explode)

    result = bootstrap._stage_mathlib_cache(
        bootstrap.BootstrapOptions(with_mathlib_cache=True, yes=True),
        project,
        prior,
    )
    assert result.status == "skipped_user_declined"
    assert "never" in result.detail


def test_mathlib_cache_requires_explicit_yes_without_prior_consent(
    monkeypatch: pytest.MonkeyPatch, project: Path
) -> None:
    monkeypatch.setattr(bootstrap, "_run", _explode)

    result = bootstrap._stage_mathlib_cache(
        bootstrap.BootstrapOptions(with_mathlib_cache=True, yes=False),
        project,
        {},
    )
    assert result.status == "skipped_user_declined"


def test_leandojo_stage_opt_in_flag_and_consent_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap, "_run", _explode)

    assert bootstrap._stage_leandojo(bootstrap.BootstrapOptions(), {}).status == "skipped_not_requested"
    assert (
        bootstrap._stage_leandojo(bootstrap.BootstrapOptions(with_leandojo=True), {}).status == "skipped_user_declined"
    )


# ─── Failure isolation ──────────────────────────────────────────────────────


def test_failed_elan_does_not_abort_pantograph(monkeypatch: pytest.MonkeyPatch, project: Path) -> None:
    """Stage 1 failure must not prevent stage 3 from trying.

    Non-blocking is the core promise from the PITCH — elan might transiently
    fail but we still want pantograph up so Python-side tooling works.
    """
    monkeypatch.setattr(bootstrap, "detect_toolchain", lambda *, env=None: _empty_toolchain())

    def stage_elan_fails(opts: bootstrap.BootstrapOptions) -> BootstrapStageResult:
        return BootstrapStageResult(name="elan", status="failed", detail="transient")

    def stage_toolchain_skips(opts: bootstrap.BootstrapOptions, root: Path) -> BootstrapStageResult:
        return BootstrapStageResult(name="toolchain", status="failed", detail="no elan")

    def stage_pantograph_ok(opts: bootstrap.BootstrapOptions) -> BootstrapStageResult:
        return _ok("pantograph", detail="installed")

    monkeypatch.setattr(bootstrap, "_stage_elan", stage_elan_fails)
    monkeypatch.setattr(bootstrap, "_stage_toolchain", stage_toolchain_skips)
    monkeypatch.setattr(bootstrap, "_stage_pantograph", stage_pantograph_ok)

    report = bootstrap.run_bootstrap(project, options=bootstrap.BootstrapOptions(dry_run=True))
    assert report.ok is False  # required stages failed
    pantograph_result = next(s for s in report.stages if s.name == "pantograph")
    assert pantograph_result.status == "ok"


def test_report_ok_is_true_when_only_optional_stages_skipped(monkeypatch: pytest.MonkeyPatch, project: Path) -> None:
    monkeypatch.setattr(bootstrap, "detect_toolchain", lambda *, env=None: _empty_toolchain())
    monkeypatch.setattr(bootstrap, "_missing_pip_packages", lambda: list(bootstrap._PIP_PACKAGES))
    monkeypatch.setattr(bootstrap.shutil, "which", lambda _name: None)
    monkeypatch.setattr(bootstrap, "_run", _explode)

    report = bootstrap.run_bootstrap(
        project,
        options=bootstrap.BootstrapOptions(dry_run=True),
    )
    assert report.ok is True


# ─── Uninstall ──────────────────────────────────────────────────────────────


def test_uninstall_dry_run_reports_paths_without_touching_disk(project: Path) -> None:
    # Create one of the target paths so we see it flip to ``would_remove``.
    lake = project / ".lake"
    lake.mkdir()

    out = bootstrap.uninstall(project, dry_run=True)
    assert out["dry_run"] is True
    actions = {p["path"]: p["action"] for p in out["paths"]}
    assert actions[str(lake)] == "would_remove"
    # Directory still exists — dry-run never rm'd it.
    assert lake.is_dir()


def test_uninstall_invokes_runner_for_existing_paths(project: Path) -> None:
    lake = project / ".lake"
    lake.mkdir()
    calls: list[list[str]] = []

    def runner(cmd: list[str]) -> tuple[int, str, str]:
        calls.append(cmd)
        return 0, "", ""

    out = bootstrap.uninstall(project, runner=runner)
    removed = [p for p in out["paths"] if p["action"] == "removed"]
    assert any(p["path"] == str(lake) for p in removed)
    assert calls, "runner must be invoked for at least the .lake directory"
    assert calls[0][0] == "rm"


def test_uninstall_marks_absent_paths_without_running_anything(project: Path) -> None:
    calls: list[list[str]] = []

    def runner(cmd: list[str]) -> tuple[int, str, str]:
        calls.append(cmd)
        return 0, "", ""

    out = bootstrap.uninstall(project, runner=runner)
    # Nothing exists under ``tmp_path`` so every path is ``absent``.
    assert all(p["action"] == "absent" for p in out["paths"])
    assert calls == []


# ─── Persistence details ────────────────────────────────────────────────────


def test_persist_preserves_prior_unknown_keys(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """If a future GRD writes extra keys, a current bootstrap run must keep them.

    Belt-and-braces forward-compat — otherwise a downgrade would silently
    wipe consent answers or other state that isn't in our schema yet.
    """
    prior = {"consent": {"mathlib_cache": "never"}, "custom_field_for_later": 42}
    env_file_path(project).write_text(json.dumps(prior), encoding="utf-8")

    monkeypatch.setattr(bootstrap, "detect_toolchain", lambda *, env=None: _empty_toolchain())
    monkeypatch.setattr(bootstrap, "_missing_pip_packages", lambda: list(bootstrap._PIP_PACKAGES))
    monkeypatch.setattr(bootstrap.shutil, "which", lambda _name: None)
    monkeypatch.setattr(bootstrap, "_run", _explode)
    bootstrap.run_bootstrap(project, options=bootstrap.BootstrapOptions(dry_run=True))

    persisted = load_env(project)
    assert persisted["consent"] == {"mathlib_cache": "never"}
    assert persisted["custom_field_for_later"] == 42


# ─── Helpers ────────────────────────────────────────────────────────────────


def _empty_toolchain() -> object:
    from grd.core.lean.env import ToolchainInfo

    return ToolchainInfo(
        lean_path=None,
        lean_version=None,
        elan_path=None,
        elan_version=None,
        lake_path=None,
        lake_version=None,
    )


def _toolchain(
    *,
    lean_path: str | None = None,
    lean_version: str | None = None,
    elan_path: str | None = None,
    elan_version: str | None = None,
) -> object:
    from grd.core.lean.env import ToolchainInfo

    return ToolchainInfo(
        lean_path=lean_path,
        lean_version=lean_version,
        elan_path=elan_path,
        elan_version=elan_version,
        lake_path=None,
        lake_version=None,
    )


def _explode(*_args: object, **_kwargs: object) -> tuple[int, str, str]:
    raise AssertionError("subprocess call not expected in this test")


# ─── Persona-aware bootstrap ─────────────────────────────────────────────────


def test_bootstrap_options_persona_defaults_none():
    opts = bootstrap.BootstrapOptions()
    assert opts.persona is None
    resolved = opts.with_persona_defaults()
    assert resolved is opts  # no-op when persona is None


def test_mathematician_persona_enables_mathlib_cache():
    opts = bootstrap.BootstrapOptions(persona="mathematician")
    resolved = opts.with_persona_defaults()
    assert resolved.with_mathlib_cache is True
    assert resolved.with_leandojo is False


def test_physicist_persona_enables_mathlib_cache():
    opts = bootstrap.BootstrapOptions(persona="physicist")
    resolved = opts.with_persona_defaults()
    assert resolved.with_mathlib_cache is True
    assert resolved.with_leandojo is False


def test_ml_researcher_persona_enables_leandojo():
    opts = bootstrap.BootstrapOptions(persona="ml-researcher")
    resolved = opts.with_persona_defaults()
    assert resolved.with_leandojo is True
    assert resolved.with_mathlib_cache is False


def test_explicit_flag_wins_over_persona_default():
    """User explicitly passes --with-mathlib-cache; persona default doesn't override."""
    opts = bootstrap.BootstrapOptions(
        persona="mathematician",
        with_mathlib_cache=True,  # already True — persona shouldn't break this
    )
    resolved = opts.with_persona_defaults()
    assert resolved.with_mathlib_cache is True


def test_valid_personas_contains_all_three():
    assert "mathematician" in bootstrap.VALID_PERSONAS
    assert "physicist" in bootstrap.VALID_PERSONAS
    assert "ml-researcher" in bootstrap.VALID_PERSONAS


def test_persona_stage_defaults_keys_match_valid_personas():
    for persona in bootstrap.VALID_PERSONAS:
        assert persona in bootstrap.PERSONA_STAGE_DEFAULTS
