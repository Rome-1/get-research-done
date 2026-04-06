"""Behavior-focused state regression coverage."""

from __future__ import annotations

from pathlib import Path

_SAMPLE_STATE_MD = """\
# Research State

## Project Reference

See: GPD/PROJECT.md (updated 2026-03-08)

**Core research question:** What is the mass gap in Yang-Mills theory?
**Current focus:** Lattice simulations

## Current Position

**Current Phase:** 2
**Current Phase Name:** Formulate Hamiltonian
**Total Phases:** 6
**Current Plan:** 1
**Total Plans in Phase:** 3
**Status:** Executing
**Last Activity:** 2026-03-08
**Last Activity Description:** Set up lattice parameters

**Progress:** [####......] 40%

## Active Calculations

None yet.

## Intermediate Results

None yet.

## Open Questions

None yet.

## Performance Metrics

| Label | Duration | Tasks | Files |
| ----- | -------- | ----- | ----- |

## Accumulated Context

### Decisions

None yet.

### Active Approximations

None yet.

**Convention Lock:**

No conventions locked yet.

### Propagated Uncertainties

None yet.

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

**Last session:** 2026-03-08T14:00:00+00:00
**Stopped at:** Phase 2 P1
**Resume file:** —
"""


def _make_state_md(tmp_path: Path) -> Path:
    gpd_dir = tmp_path / "GPD"
    gpd_dir.mkdir(parents=True)
    state_md = gpd_dir / "STATE.md"
    state_md.write_text(
        "# State\n\n"
        "## Current Position\n\n"
        "**Status:** Active\n\n"
        "### Decisions\nNone yet.\n\n"
        "### Blockers/Concerns\nNone.\n",
        encoding="utf-8",
    )
    (gpd_dir / "state.json").write_text("{}", encoding="utf-8")
    return state_md


def test_decision_newlines_are_sanitized(tmp_path: Path) -> None:
    from gpd.core.state import state_add_decision

    state_md = _make_state_md(tmp_path)
    result = state_add_decision(
        tmp_path,
        summary="Line one\nLine two\nLine three",
        phase="1",
        rationale="Because\nof\nthis",
    )

    assert result.added is True
    content = state_md.read_text(encoding="utf-8")
    assert "Line one Line two Line three" in content


def test_blocker_newlines_are_sanitized(tmp_path: Path) -> None:
    from gpd.core.state import state_add_blocker

    state_md = _make_state_md(tmp_path)
    result = state_add_blocker(tmp_path, "Problem\nwith\nspacing")

    assert result.added is True
    assert "Problem with spacing" in state_md.read_text(encoding="utf-8")

