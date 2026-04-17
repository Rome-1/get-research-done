"""Phase 11 regressions for the durable child-return continuation boundary."""

from __future__ import annotations

import json
from pathlib import Path

from grd.core.commands import cmd_apply_return_updates
from grd.core.return_contract import validate_grd_return_markdown
from grd.core.state import default_state_dict, generate_state_markdown


def _write_project_state(tmp_path: Path) -> Path:
    grd_dir = tmp_path / "GRD"
    grd_dir.mkdir()
    state = default_state_dict()
    (grd_dir / "state.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    (grd_dir / "STATE.md").write_text(generate_state_markdown(state), encoding="utf-8")
    return grd_dir


def _wrap_return_block(yaml_body: str) -> str:
    return f"```yaml\ngrd_return:\n{yaml_body}```\n"


def test_validate_and_apply_the_same_durable_continuation_payload(tmp_path: Path) -> None:
    grd_dir = _write_project_state(tmp_path)
    return_file = tmp_path / "durable_return.md"
    return_file.write_text(
        _wrap_return_block(
            "  status: checkpoint\n"
            "  files_written: [GRD/state.json]\n"
            "  issues: []\n"
            "  next_actions: [/grd:resume-work]\n"
            "  continuation_update:\n"
            "    handoff:\n"
            "      recorded_at: 2026-04-08T12:00:00Z\n"
            "      recorded_by: execute-plan\n"
            "      stopped_at: Completed phase 01\n"
            "      resume_file: GRD/phases/01-test-phase/.continue-here.md\n"
            "    bounded_segment:\n"
            "      resume_file: GRD/phases/01-test-phase/.continue-here.md\n"
            "      phase: 01\n"
            "      plan: 01\n"
            "      segment_id: seg-01\n"
            "      segment_status: paused\n"
            "      checkpoint_reason: segment_boundary\n"
        ),
        encoding="utf-8",
    )

    validation = validate_grd_return_markdown(return_file.read_text(encoding="utf-8"))
    assert validation.passed is True
    assert validation.fields["continuation_update"]["handoff"]["recorded_by"] == "execute-plan"
    assert validation.fields["continuation_update"]["bounded_segment"]["segment_id"] == "seg-01"

    result = cmd_apply_return_updates(tmp_path, return_file)

    assert result.passed is True
    assert result.applied_continuation_operations == ["record_session", "set_bounded_segment"]

    updated_state = json.loads((grd_dir / "state.json").read_text(encoding="utf-8"))
    assert updated_state["continuation"]["handoff"]["recorded_by"] == "state_record_session"
    assert updated_state["continuation"]["bounded_segment"]["segment_id"] == "seg-01"
