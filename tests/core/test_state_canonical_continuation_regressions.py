from __future__ import annotations

import json
from pathlib import Path

from gpd.core.state import (
    _blank_session_payload,
    default_state_dict,
    generate_state_markdown,
    load_state_json,
    save_state_json,
    save_state_markdown,
    state_load,
    sync_state_json,
)


def test_save_state_json_does_not_backfill_canonical_continuation_from_session_only_fields(
    tmp_path: Path, state_project_factory
) -> None:
    cwd = state_project_factory(tmp_path)
    state = json.loads((cwd / "GPD" / "state.json").read_text(encoding="utf-8"))
    state["session"].update(
        {
            "last_date": "2026-04-01T12:00:00+00:00",
            "stopped_at": "Legacy stop",
            "resume_file": "legacy-session.md",
            "hostname": "legacy-host",
            "platform": "LegacyOS",
        }
    )

    save_state_json(cwd, state)

    stored = load_state_json(cwd)
    assert stored is not None
    assert stored["continuation"]["handoff"] == {
        "recorded_at": None,
        "stopped_at": None,
        "resume_file": None,
        "recorded_by": None,
        "last_result_id": None,
    }
    assert stored["continuation"]["machine"] == {
        "recorded_at": None,
        "hostname": None,
        "platform": None,
    }
    assert stored["session"] == _blank_session_payload()


def test_state_load_ignores_backup_only_session_values_when_canonical_continuation_is_blank(
    tmp_path: Path, state_project_factory
) -> None:
    cwd = state_project_factory(tmp_path)
    gpd_dir = cwd / "GPD"
    primary_path = gpd_dir / "state.json"
    backup_path = gpd_dir / "state.json.bak"

    backup_state = default_state_dict()
    backup_state["session"].update(
        {
            "last_date": "2026-04-01T12:00:00+00:00",
            "stopped_at": "Backup-only stop",
            "resume_file": "backup-only.md",
            "hostname": "backup-host",
            "platform": "BackupOS",
        }
    )
    backup_path.write_text(json.dumps(backup_state, indent=2) + "\n", encoding="utf-8")

    primary_state = default_state_dict()
    primary_state["session"] = "malformed"
    primary_path.write_text(json.dumps(primary_state, indent=2) + "\n", encoding="utf-8")

    result = state_load(cwd)

    assert result.state["continuation"]["handoff"]["resume_file"] is None
    assert result.state["continuation"]["machine"]["hostname"] is None
    assert result.state["session"] == _blank_session_payload()


def test_save_state_markdown_does_not_backfill_canonical_continuation_from_markdown_session_on_blank_workspace(
    tmp_path: Path,
) -> None:
    legacy_state = default_state_dict()
    legacy_state["session"].update(
        {
            "last_date": "2026-04-01T12:00:00+00:00",
            "stopped_at": "Legacy stop",
            "resume_file": "GPD/phases/03-analysis/.continue-here.md",
            "hostname": "legacy-host",
            "platform": "LegacyOS",
        }
    )
    resume_path = tmp_path / "GPD" / "phases" / "03-analysis" / ".continue-here.md"
    resume_path.parent.mkdir(parents=True, exist_ok=True)
    resume_path.write_text("resume\n", encoding="utf-8")

    result = save_state_markdown(tmp_path, generate_state_markdown(legacy_state))
    stored = load_state_json(tmp_path)

    assert result["continuation"]["handoff"]["resume_file"] is None
    assert result["continuation"]["machine"]["hostname"] is None
    assert result["session"] == _blank_session_payload()
    assert stored is not None
    assert stored["continuation"]["handoff"]["resume_file"] is None
    assert stored["continuation"]["machine"]["hostname"] is None
    assert stored["session"] == _blank_session_payload()


def test_sync_state_json_does_not_backfill_canonical_continuation_from_markdown_session_on_blank_workspace(
    tmp_path: Path,
) -> None:
    legacy_state = default_state_dict()
    legacy_state["session"].update(
        {
            "last_date": "2026-04-01T12:00:00+00:00",
            "stopped_at": "Legacy stop",
            "resume_file": "GPD/phases/03-analysis/.continue-here.md",
            "hostname": "legacy-host",
            "platform": "LegacyOS",
        }
    )
    resume_path = tmp_path / "GPD" / "phases" / "03-analysis" / ".continue-here.md"
    resume_path.parent.mkdir(parents=True, exist_ok=True)
    resume_path.write_text("resume\n", encoding="utf-8")

    result = sync_state_json(tmp_path, generate_state_markdown(legacy_state))
    stored = load_state_json(tmp_path)

    assert result["continuation"]["handoff"]["resume_file"] is None
    assert result["continuation"]["machine"]["hostname"] is None
    assert result["session"] == _blank_session_payload()
    assert stored is not None
    assert stored["continuation"]["handoff"]["resume_file"] is None
    assert stored["continuation"]["machine"]["hostname"] is None
    assert stored["session"] == _blank_session_payload()
