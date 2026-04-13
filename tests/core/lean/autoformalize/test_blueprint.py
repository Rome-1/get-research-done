"""Tests for ``grd.core.lean.autoformalize.blueprint``.

Focuses on convention flattening, physics auto-detection, and override flags.
"""

from __future__ import annotations

import json
from pathlib import Path

from grd.core.lean.autoformalize.blueprint import extract_blueprint_context


def _write_state(project_root: Path, state: dict) -> None:
    grd_dir = project_root / ".grd"
    grd_dir.mkdir(parents=True, exist_ok=True)
    (grd_dir / "state.json").write_text(json.dumps(state))


def test_detects_physics_from_metric_signature(tmp_path: Path) -> None:
    _write_state(tmp_path, {"convention_lock": {"metric_signature": "(+,-,-,-)"}})
    ctx = extract_blueprint_context(claim="spacetime claim", project_root=tmp_path)
    assert ctx.physics is True
    assert ctx.conventions["metric_signature"] == "(+,-,-,-)"


def test_no_state_yields_no_conventions_and_math_path(tmp_path: Path) -> None:
    ctx = extract_blueprint_context(claim="for every prime p, p >= 2", project_root=tmp_path)
    assert ctx.physics is False
    assert ctx.conventions == {}
    assert ctx.claim == "for every prime p, p >= 2"


def test_physics_override_wins(tmp_path: Path) -> None:
    # No physics convention, but user forces physics=True.
    _write_state(tmp_path, {"convention_lock": {}})
    ctx = extract_blueprint_context(
        claim="any claim",
        project_root=tmp_path,
        physics_override=True,
    )
    assert ctx.physics is True


def test_physics_override_false_suppresses_autodetect(tmp_path: Path) -> None:
    _write_state(tmp_path, {"convention_lock": {"metric_signature": "(+,-,-,-)"}})
    ctx = extract_blueprint_context(
        claim="x",
        project_root=tmp_path,
        physics_override=False,
    )
    assert ctx.physics is False


def test_unset_values_are_dropped(tmp_path: Path) -> None:
    _write_state(
        tmp_path,
        {
            "convention_lock": {
                "metric_signature": "NOT-SPECIFIED",
                "fourier_convention": "",
                "natural_units": "ℏ=c=1",
            }
        },
    )
    ctx = extract_blueprint_context(claim="x", project_root=tmp_path)
    assert "metric_signature" not in ctx.conventions
    assert "fourier_convention" not in ctx.conventions
    assert ctx.conventions["natural_units"] == "ℏ=c=1"


def test_custom_conventions_merge_into_flat_dict(tmp_path: Path) -> None:
    _write_state(
        tmp_path,
        {
            "convention_lock": {
                "natural_units": "ℏ=c=1",
                "custom_conventions": {
                    "spin_convention": "left-handed",
                    "unused_key": "NOT-SPECIFIED",
                },
            }
        },
    )
    ctx = extract_blueprint_context(claim="x", project_root=tmp_path)
    assert ctx.conventions["spin_convention"] == "left-handed"
    assert "unused_key" not in ctx.conventions


def test_reads_project_name_when_available(tmp_path: Path) -> None:
    _write_state(tmp_path, {"project": {"name": "my-project"}, "convention_lock": {}})
    ctx = extract_blueprint_context(claim="x", project_root=tmp_path, phase="5")
    assert ctx.project_name == "my-project"
    assert ctx.phase == "5"
