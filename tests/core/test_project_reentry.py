from __future__ import annotations

from pathlib import Path

from gpd.core.project_reentry import resolve_project_reentry


def _make_gpd_workspace(
    root: Path,
    *,
    project: bool = False,
    roadmap: bool = False,
    state: bool = False,
) -> Path:
    gpd_dir = root / "GPD"
    gpd_dir.mkdir(parents=True, exist_ok=True)
    if project:
        (gpd_dir / "PROJECT.md").write_text("# Project\n", encoding="utf-8")
    if roadmap:
        (gpd_dir / "ROADMAP.md").write_text("# Roadmap\n", encoding="utf-8")
    if state:
        (gpd_dir / "STATE.md").write_text("# State\n", encoding="utf-8")
    return root


def _recent_row(project_root: Path, *, last_session_at: str, resumable: bool = True) -> dict[str, object]:
    return {
        "project_root": project_root.resolve(strict=False).as_posix(),
        "last_session_at": last_session_at,
        "stopped_at": "Phase 02",
        "resume_file": "GPD/phases/02/.continue-here.md",
        "resume_file_available": True,
        "resume_file_reason": None,
        "available": True,
        "resumable": resumable,
    }


def test_resolve_project_reentry_prefers_current_workspace_recovery(tmp_path: Path) -> None:
    workspace = _make_gpd_workspace(tmp_path / "workspace", project=True)

    resolution = resolve_project_reentry(workspace, recent_rows=[])

    assert resolution.mode == "current-workspace"
    assert resolution.source == "current_workspace"
    assert resolution.auto_selected is False
    assert resolution.requires_user_selection is False
    assert resolution.has_current_workspace_candidate is True
    assert resolution.has_recoverable_current_workspace is True
    assert resolution.project_root == workspace.resolve(strict=False).as_posix()
    assert resolution.recoverable_candidates_count == 1
    assert len(resolution.candidates) == 1
    assert resolution.candidates[0].source == "current_workspace"
    assert resolution.candidates[0].recoverable is True
    assert resolution.candidates[0].project_exists is True


def test_resolve_project_reentry_walks_up_to_ancestor_project_root(tmp_path: Path) -> None:
    project = _make_gpd_workspace(tmp_path / "project", project=True)
    nested = project / "src" / "notes"
    nested.mkdir(parents=True)

    resolution = resolve_project_reentry(nested, recent_rows=[])

    assert resolution.mode == "current-workspace"
    assert resolution.source == "current_workspace"
    assert resolution.has_current_workspace_candidate is True
    assert resolution.has_recoverable_current_workspace is True
    assert resolution.project_root == project.resolve(strict=False).as_posix()
    assert resolution.recoverable_candidates_count == 1
    assert len(resolution.candidates) == 1
    assert resolution.candidates[0].reason == "workspace resolved to ancestor project root"
    assert resolution.candidates[0].project_root == project.resolve(strict=False).as_posix()


def test_resolve_project_reentry_surfaces_partial_recoverable_workspace(tmp_path: Path) -> None:
    workspace = _make_gpd_workspace(tmp_path / "workspace", roadmap=True, state=True)

    resolution = resolve_project_reentry(workspace, recent_rows=[])

    assert resolution.mode == "current-workspace"
    assert resolution.source == "current_workspace"
    assert resolution.has_current_workspace_candidate is True
    assert resolution.has_recoverable_current_workspace is True
    assert resolution.project_root == workspace.resolve(strict=False).as_posix()
    assert resolution.recoverable_candidates_count == 1
    assert len(resolution.candidates) == 1
    assert resolution.candidates[0].reason == "workspace carries partial recoverable GPD state"
    assert resolution.candidates[0].project_exists is False
    assert resolution.candidates[0].roadmap_exists is True
    assert resolution.candidates[0].state_exists is True


def test_resolve_project_reentry_auto_selects_unique_recoverable_recent_project(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    project = _make_gpd_workspace(tmp_path / "recent-project", project=True)

    resolution = resolve_project_reentry(
        workspace,
        recent_rows=[
            _recent_row(
                project,
                last_session_at="2026-03-28T12:00:00+00:00",
            )
        ],
    )

    assert resolution.mode == "auto-recent-project"
    assert resolution.source == "recent_project"
    assert resolution.auto_selected is True
    assert resolution.requires_user_selection is False
    assert resolution.has_current_workspace_candidate is False
    assert resolution.has_recoverable_current_workspace is False
    assert resolution.project_root == project.resolve(strict=False).as_posix()
    assert resolution.recoverable_candidates_count == 1
    assert len(resolution.candidates) == 1
    assert resolution.candidates[0].source == "recent_project"
    assert resolution.candidates[0].auto_selectable is True
    assert resolution.candidates[0].recoverable is True


def test_resolve_project_reentry_requires_user_selection_for_ambiguous_recent_projects(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    first = _make_gpd_workspace(tmp_path / "recent-a", project=True)
    second = _make_gpd_workspace(tmp_path / "recent-b", project=True)

    resolution = resolve_project_reentry(
        workspace,
        recent_rows=[
            _recent_row(first, last_session_at="2026-03-28T12:00:00+00:00"),
            _recent_row(second, last_session_at="2026-03-28T13:00:00+00:00"),
        ],
    )

    assert resolution.mode == "ambiguous-recent-projects"
    assert resolution.source is None
    assert resolution.auto_selected is False
    assert resolution.requires_user_selection is True
    assert resolution.project_root is None
    assert resolution.recoverable_candidates_count == 2
    assert len(resolution.candidates) == 2
    assert all(candidate.source == "recent_project" for candidate in resolution.candidates)
    assert all(candidate.auto_selectable is False for candidate in resolution.candidates)


def test_resolve_project_reentry_dedupes_current_workspace_and_recent_project_rows(tmp_path: Path) -> None:
    workspace = _make_gpd_workspace(tmp_path / "workspace", project=True)

    resolution = resolve_project_reentry(
        workspace,
        recent_rows=[
            _recent_row(
                workspace,
                last_session_at="2026-03-28T12:00:00+00:00",
            )
        ],
    )

    assert resolution.mode == "current-workspace"
    assert resolution.source == "current_workspace"
    assert resolution.project_root == workspace.resolve(strict=False).as_posix()
    assert resolution.recoverable_candidates_count == 1
    assert len(resolution.candidates) == 1
    assert resolution.candidates[0].source == "current_workspace"
