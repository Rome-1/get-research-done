"""Shared project re-entry resolution for recovery-oriented GPD surfaces.

This layer sits above low-level root resolution and recent-project discovery.
It answers one question: given the current workspace, can GPD safely recover a
project root to continue from, and if not, why not?
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from gpd.core.constants import ProjectLayout
from gpd.core.recent_projects import list_recent_projects
from gpd.core.root_resolution import (
    RootResolutionConfidence,
    normalize_workspace_hint,
    resolve_project_roots,
)

__all__ = [
    "ProjectReentryCandidate",
    "ProjectReentryResolution",
    "recoverable_project_context",
    "resolve_project_reentry",
]


class ProjectReentryCandidate(BaseModel):
    """One possible project root for projectless recovery."""

    model_config = ConfigDict(frozen=True)

    source: str
    project_root: str
    available: bool
    recoverable: bool
    resumable: bool
    confidence: str
    reason: str
    state_exists: bool = False
    roadmap_exists: bool = False
    project_exists: bool = False
    resume_file: str | None = None
    resume_file_available: bool | None = None
    resume_file_reason: str | None = None
    last_session_at: str | None = None
    stopped_at: str | None = None
    auto_selectable: bool = False


class ProjectReentryResolution(BaseModel):
    """Shared re-entry decision payload for recovery/status commands."""

    model_config = ConfigDict(frozen=True)

    workspace_root: str | None = None
    project_root: str | None = None
    source: str | None = None
    mode: str = "no-recovery"
    auto_selected: bool = False
    requires_user_selection: bool = False
    has_current_workspace_candidate: bool = False
    has_recoverable_current_workspace: bool = False
    recoverable_candidates_count: int = 0
    candidates: list[ProjectReentryCandidate] = Field(default_factory=list)

    @property
    def resolved_project_root(self) -> Path | None:
        if not isinstance(self.project_root, str) or not self.project_root.strip():
            return None
        return Path(self.project_root).expanduser().resolve(strict=False)


def recoverable_project_context(project_root: Path) -> tuple[bool, bool, bool]:
    """Return whether a project root has enough durable state for recovery."""

    layout = ProjectLayout(project_root)
    state_exists = any(
        path.exists()
        for path in (
            layout.state_json,
            layout.state_json_backup,
            layout.state_md,
        )
    )
    roadmap_exists = layout.roadmap.exists()
    project_exists = layout.project_md.exists()
    return state_exists, roadmap_exists, project_exists


def _candidate_sort_key(candidate: ProjectReentryCandidate) -> tuple[int, int, int, str, str]:
    return (
        1 if candidate.recoverable else 0,
        1 if candidate.resumable else 0,
        1 if candidate.available else 0,
        candidate.last_session_at or "",
        candidate.project_root,
    )


def _normalize_recent_text(row: Mapping[str, object], *keys: str) -> str | None:
    for key in keys:
        value = row.get(key)
        if not isinstance(value, str):
            continue
        stripped = value.strip()
        if stripped:
            return stripped
    return None


def _candidate_from_recent_row(row: Mapping[str, object]) -> ProjectReentryCandidate | None:
    project_root_text = _normalize_recent_text(row, "project_root", "workspace_root", "cwd", "path")
    if project_root_text is None:
        return None

    project_root = Path(project_root_text).expanduser().resolve(strict=False)
    state_exists, roadmap_exists, project_exists = recoverable_project_context(project_root)
    available = bool(row.get("available", project_root.is_dir()))
    recoverable = available and (state_exists or roadmap_exists or project_exists)
    resumable = bool(row.get("resumable", False))
    resume_file = _normalize_recent_text(row, "resume_file")
    return ProjectReentryCandidate(
        source="recent_project",
        project_root=project_root.as_posix(),
        available=available,
        recoverable=recoverable,
        resumable=resumable,
        confidence="medium" if recoverable else "low",
        reason="recent project cache entry",
        state_exists=state_exists,
        roadmap_exists=roadmap_exists,
        project_exists=project_exists,
        resume_file=resume_file,
        resume_file_available=row.get("resume_file_available") if isinstance(row.get("resume_file_available"), bool) else None,
        resume_file_reason=_normalize_recent_text(row, "resume_file_reason"),
        last_session_at=_normalize_recent_text(row, "last_session_at", "last_seen_at", "last_event_at"),
        stopped_at=_normalize_recent_text(row, "stopped_at"),
    )


def _current_workspace_candidate(workspace: Path | None) -> ProjectReentryCandidate | None:
    resolution = resolve_project_roots(workspace)
    if resolution is None:
        return None

    project_root = resolution.project_root.expanduser().resolve(strict=False)
    state_exists, roadmap_exists, project_exists = recoverable_project_context(project_root)
    recoverable = state_exists or roadmap_exists or project_exists
    if not resolution.has_project_layout and not recoverable:
        return None

    if resolution.basis == "workspace" and resolution.has_project_layout and resolution.walk_up_steps > 0:
        reason = "workspace resolved to ancestor project root"
    elif resolution.has_project_layout and not project_exists and recoverable:
        reason = "workspace carries partial recoverable GPD state"
    elif resolution.has_project_layout:
        reason = "workspace already points at a GPD project"
    else:
        reason = "workspace carries partial recoverable GPD state"

    return ProjectReentryCandidate(
        source="current_workspace",
        project_root=project_root.as_posix(),
        available=project_root.is_dir(),
        recoverable=recoverable,
        resumable=False,
        confidence=resolution.confidence.value if isinstance(resolution.confidence, RootResolutionConfidence) else str(resolution.confidence),
        reason=reason,
        state_exists=state_exists,
        roadmap_exists=roadmap_exists,
        project_exists=project_exists,
    )


def resolve_project_reentry(
    workspace: Path | str | None,
    *,
    data_root: Path | None = None,
    recent_rows: Sequence[Mapping[str, object] | object] | None = None,
) -> ProjectReentryResolution:
    """Resolve the shared re-entry decision for one workspace."""

    workspace_root = normalize_workspace_hint(workspace)
    current_candidate = _current_workspace_candidate(workspace_root)

    seen_roots: set[str] = set()
    candidates: list[ProjectReentryCandidate] = []
    if current_candidate is not None:
        candidates.append(current_candidate)
        seen_roots.add(current_candidate.project_root)

    recent_project_rows = list(recent_rows) if recent_rows is not None else list_recent_projects(data_root)
    for row in recent_project_rows:
        row_payload = row.model_dump(mode="json") if hasattr(row, "model_dump") else row
        if not isinstance(row_payload, Mapping):
            continue
        candidate = _candidate_from_recent_row(row_payload)
        if candidate is None or candidate.project_root in seen_roots:
            continue
        candidates.append(candidate)
        seen_roots.add(candidate.project_root)

    recent_candidates = [candidate for candidate in candidates if candidate.source == "recent_project"]
    recoverable_recent = sorted(
        [candidate for candidate in recent_candidates if candidate.recoverable],
        key=_candidate_sort_key,
        reverse=True,
    )

    selected_project_root: str | None = None
    selected_source: str | None = None
    mode = "no-recovery"
    auto_selected = False
    requires_user_selection = False

    if current_candidate is not None:
        selected_project_root = current_candidate.project_root
        selected_source = current_candidate.source
        mode = "current-workspace"
    elif len(recoverable_recent) == 1:
        auto_candidate = recoverable_recent[0]
        selected_project_root = auto_candidate.project_root
        selected_source = auto_candidate.source
        mode = "auto-recent-project"
        auto_selected = True
    elif len(recoverable_recent) > 1:
        mode = "ambiguous-recent-projects"
        requires_user_selection = True

    auto_selectable_roots = {selected_project_root} if auto_selected and selected_project_root is not None else set()
    normalized_candidates = [
        candidate.model_copy(update={"auto_selectable": candidate.project_root in auto_selectable_roots})
        for candidate in sorted(candidates, key=_candidate_sort_key, reverse=True)
    ]

    return ProjectReentryResolution(
        workspace_root=workspace_root.as_posix() if workspace_root is not None else None,
        project_root=selected_project_root,
        source=selected_source,
        mode=mode,
        auto_selected=auto_selected,
        requires_user_selection=requires_user_selection,
        has_current_workspace_candidate=current_candidate is not None,
        has_recoverable_current_workspace=bool(current_candidate and current_candidate.recoverable),
        recoverable_candidates_count=sum(1 for candidate in normalized_candidates if candidate.recoverable),
        candidates=normalized_candidates,
    )
