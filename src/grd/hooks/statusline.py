#!/usr/bin/env python3
"""Runtime-agnostic statusline hook for GRD.

Reads JSON from stdin, outputs an ANSI-formatted statusline to stdout.
Shows: GRD | model | path | current task | research position | context usage.
"""

import json
import math
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import grd.hooks.install_context as hook_layout
from grd.core.constants import ENV_GRD_DEBUG, PLANNING_DIR_NAME, STATE_JSON_FILENAME
from grd.core.observability import resolve_project_root

# Context bar thresholds (percentage of scaled usage)
_CONTEXT_REAL_LIMIT_PCT = 80
_CONTEXT_WARN_THRESHOLD = 63
_CONTEXT_HIGH_THRESHOLD = 81
_CONTEXT_CRITICAL_THRESHOLD = 95
_STATUS_LABEL = "GRD"
_CANONICAL_MODEL_KEYS = ("display_name", "name", "id")
_CANONICAL_CONTEXT_WINDOW_SIZE_KEYS = ("context_window_size",)
_CANONICAL_CONTEXT_REMAINING_KEYS = ("remaining_percentage", "remainingPercent", "remaining")


def _context_bar(remaining_pct: float) -> str:
    """Build an ANSI-colored context-usage bar (scaled to real limit)."""
    rem = round(remaining_pct)
    raw_used = max(0, min(100, 100 - rem))
    used = min(100, round((raw_used / _CONTEXT_REAL_LIMIT_PCT) * 100))

    filled = used // 10
    bar = "\u2588" * filled + "\u2591" * (10 - filled)

    if used < _CONTEXT_WARN_THRESHOLD:
        return f" \x1b[32m{bar} {used}%\x1b[0m"
    if used < _CONTEXT_HIGH_THRESHOLD:
        return f" \x1b[33m{bar} {used}%\x1b[0m"
    if used < _CONTEXT_CRITICAL_THRESHOLD:
        return f" \x1b[38;5;208m{bar} {used}%\x1b[0m"
    return f" \x1b[5;31m\U0001f480 {bar} {used}%\x1b[0m"


def _debug(msg: str) -> None:
    if os.environ.get(ENV_GRD_DEBUG):
        sys.stderr.write(f"[grd-debug] {msg}\n")


def _mapping(value: object) -> dict[str, object]:
    """Return *value* when it is a dict, otherwise an empty mapping."""
    return value if isinstance(value, dict) else {}


def _first_string(value: object, *keys: str) -> str:
    """Return the first non-empty string for *keys* from *value* when it is a mapping."""
    mapping = _mapping(value)
    for key in keys:
        candidate = mapping.get(key)
        if isinstance(candidate, str) and candidate:
            return candidate
    return ""


def _first_value(value: object, *keys: str) -> object | None:
    """Return the first present value for *keys* from *value* when it is a mapping."""
    mapping = _mapping(value)
    for key in keys:
        if key in mapping:
            return mapping.get(key)
    return None


def _merged_policy_keys(value: object, attribute: str, *, fallback: tuple[str, ...]) -> tuple[str, ...]:
    """Return policy-owned keys plus canonical fallbacks, deduplicated in order."""
    raw_keys = getattr(value, attribute, ())
    merged: list[str] = []
    for key in (*raw_keys, *fallback):
        if isinstance(key, str) and key and key not in merged:
            merged.append(key)
    return tuple(merged)


def _object_value(value: object, key: str) -> object | None:
    """Return *key* from either a mapping or an attribute-bearing object."""
    if isinstance(value, dict) and key in value:
        return value.get(key)
    if hasattr(value, key):
        return getattr(value, key)
    return None


def _object_string(value: object, key: str) -> str:
    """Return a non-empty string field from either a mapping or an object."""
    candidate = _object_value(value, key)
    return candidate if isinstance(candidate, str) and candidate else ""


def _workspace_mapping_prefers_local_statusline_lookup(
    data: dict[str, object],
    *,
    hook_payload: object,
) -> bool:
    """Keep alias-only workspace mappings anchored to the runtime-owned workspace."""
    return payload_uses_alias_only_workspace_mapping(data, hook_payload=hook_payload)


def _compact_age_label(value: object) -> str:
    """Return a short age label like ``45m`` from a human label like ``45m ago``."""
    if not isinstance(value, str):
        return ""
    label = value.strip()
    if not label:
        return ""
    if label.endswith(" ago"):
        return label[:-4]
    return label


def _hook_payload_policy(workspace_dir: str | None = None):
    """Return hook payload metadata for the active runtime or a merged fallback."""
    from grd.adapters.runtime_catalog import get_hook_payload_policy
    from grd.hooks.runtime_detect import RUNTIME_UNKNOWN, detect_active_runtime_with_grd_install

    workspace_path = resolve_project_root(workspace_dir) if workspace_dir else None
    runtime = detect_active_runtime_with_grd_install(cwd=workspace_path)
    return get_hook_payload_policy(None if runtime == RUNTIME_UNKNOWN else runtime)


def _format_context_window_size(value: object) -> str:
    """Return a compact context-window label like ``1M context``."""
    if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        return ""

    size = int(value)
    if size >= 1_000_000:
        scaled = size / 1_000_000
        suffix = "M"
    elif size >= 1_000:
        scaled = size / 1_000
        suffix = "k"
    else:
        return f"{size} context"

    if scaled.is_integer() or scaled >= 100:
        compact = f"{scaled:.0f}"
    else:
        compact = f"{scaled:.1f}".rstrip("0").rstrip(".")
    return f"{compact}{suffix} context"


def _read_model_label(data: dict[str, object], hook_payload=None) -> str:
    """Return the current model label with context-window size when available."""
    policy = hook_payload or _hook_payload_policy()
    model_value = data.get("model")
    if isinstance(model_value, str) and model_value:
        model_label = model_value
    else:
        model_label = _first_string(
            model_value,
            *_merged_policy_keys(policy, "model_keys", fallback=_CANONICAL_MODEL_KEYS),
        )

    context_label = _format_context_window_size(
        _first_value(
            data.get("context_window"),
            *_merged_policy_keys(policy, "context_window_size_keys", fallback=_CANONICAL_CONTEXT_WINDOW_SIZE_KEYS),
        )
    )
    if model_label and context_label:
        return f"{model_label} ({context_label})"
    return model_label


def _read_workspace_label(
    data: dict[str, object],
    workspace_dir: str,
    *,
    project_root: str | None = None,
    hook_payload=None,
) -> str:
    """Return a compact workspace label, relative to the project root when possible."""
    if not workspace_dir:
        return ""

    policy = hook_payload or _hook_payload_policy(workspace_dir)
    workspace_path = Path(workspace_dir).expanduser()
    workspace_value = data.get("workspace")
    project_dir = project_root or _first_string(workspace_value, *policy.project_dir_keys) or _first_string(
        data,
        *policy.project_dir_keys,
    )

    try:
        resolved_workspace = workspace_path.resolve()
    except OSError:
        resolved_workspace = workspace_path

    if project_dir:
        project_path = Path(project_dir).expanduser()
        try:
            resolved_project = project_path.resolve()
            relative = resolved_workspace.relative_to(resolved_project)
            project_name = resolved_project.name or str(resolved_project)
            if relative.parts:
                return f"[{project_name}/{relative.as_posix()}]"
            return f"[{project_name}]"
        except (OSError, ValueError):
            pass

    display_name = resolved_workspace.name or workspace_dir
    return f"[{display_name}]"


def _statusline_project_root(workspace_dir: str) -> Path | None:
    """Return the most durable project root visible from one workspace path."""
    normalized = normalize_workspace_hint(workspace_dir)
    if normalized is None:
        return None

    bare_grd_root: Path | None = None
    for steps, candidate in enumerate((normalized, *normalized.parents)):
        layout = ProjectLayout(candidate)
        if not layout.grd.is_dir():
            continue
        if (
            layout.state_json.exists()
            or layout.state_md.exists()
            or layout.project_md.exists()
            or layout.roadmap.exists()
            or layout.phases_dir.is_dir()
        ):
            return candidate
        if steps == 0 and bare_grd_root is None:
            bare_grd_root = candidate
    return bare_grd_root


def _read_position(workspace_dir: str) -> str:
    """Read research position from .grd/state.json."""
    workspace_root = resolve_project_root(workspace_dir) or Path(workspace_dir).expanduser().resolve(strict=False)
    state_file = workspace_root / PLANNING_DIR_NAME / STATE_JSON_FILENAME
    if not state_file.exists():
        return ""
    try:
        state, _issues, _source = peek_state_json(
            workspace_root,
            recover_intent=False,
            surface_blocked_project_contract=True,
            acquire_lock=False,
        )
    except Exception as exc:
        _debug(f"Failed to read state via canonical loader: {exc}")
        return ""

    if not isinstance(state, dict):
        return ""
    pos = state.get("position", {})
    phase = pos.get("current_phase")
    total_phases = pos.get("total_phases")
    if phase is None or total_phases is None:
        return ""
    result = f"P{phase}/{total_phases}"
    plan = pos.get("current_plan")
    total_plans = pos.get("total_plans_in_phase")
    if plan is not None and total_plans is not None:
        result += f" plan {plan}/{total_plans}"
    return result


def _matching_todo_files(todos_dir: Path, session_id: str) -> list[tuple[float, Path]]:
    """Return matching todo files for a session ordered newest-first within one directory."""
    matches: list[tuple[float, Path]] = []
    try:
        for todo_file in todos_dir.iterdir():
            if todo_file.name.startswith(f"{session_id}-agent-") and todo_file.suffix == ".json":
                try:
                    matches.append((todo_file.stat().st_mtime, todo_file))
                except OSError as exc:
                    _debug(f"Failed to stat {todo_file}: {exc}")
    except OSError as exc:
        _debug(f"Failed to read todo dir {todos_dir}: {exc}")
        return []

    matches.sort(key=lambda item: item[0], reverse=True)
    return matches


def _read_todo_entries(todo_file: Path) -> list[dict[str, object]]:
    """Return normalized todo entries from one JSON file."""
    try:
        payload = json.loads(todo_file.read_text(encoding="utf-8"))
    except Exception as exc:
        _debug(f"Failed to parse todo file {todo_file}: {exc}")
        return []

    if isinstance(payload, list):
        return [entry for entry in payload if isinstance(entry, dict)]
    if isinstance(payload, dict):
        return [payload]

    _debug(f"Ignoring non-object todo file {todo_file}")
    return []


def _read_current_task(session_id: str, workspace_dir: str | None = None) -> str:
    """Find the in-progress task across all runtime todo directories."""
    if not session_id:
        return ""

    from grd.hooks.runtime_detect import (
        RUNTIME_UNKNOWN,
        detect_active_runtime_with_grd_install,
        detect_runtime_for_grd_use,
        detect_runtime_install_target,
        get_todo_candidates,
        should_consider_todo_candidate,
    )

    workspace_path = resolve_project_root(workspace_dir) if workspace_dir else None
    active_installed_runtime = detect_active_runtime_with_grd_install(cwd=workspace_path)
    preferred_runtime = detect_runtime_for_grd_use(cwd=workspace_path)
    todo_candidates = get_todo_candidates(cwd=workspace_path, preferred_runtime=preferred_runtime)
    self_install = hook_layout.detect_self_owned_install(__file__)
    active_install_target = (
        detect_runtime_install_target(active_installed_runtime, cwd=workspace_path)
        if active_installed_runtime not in (None, "", RUNTIME_UNKNOWN)
        else None
    )
    if hook_layout.should_prefer_self_owned_install(
        self_install,
        active_install_target=active_install_target,
        workspace_path=workspace_path,
    ):
        self_candidate = hook_layout.self_owned_todo_candidate(self_install)
        if all(candidate.path != self_candidate.path for candidate in todo_candidates):
            todo_candidates = [self_candidate, *todo_candidates]

    todo_files: list[tuple[float, Path]] = []
    for candidate in todo_candidates:
        todos_dir = candidate.path
        if not todos_dir.is_dir():
            continue
        for _mtime, todo_file in _matching_todo_files(todos_dir, session_id):
            for todo in _read_todo_entries(todo_file):
                if todo.get("status") != "in_progress":
                    continue
                active_form = todo.get("activeForm")
                if isinstance(active_form, str) and active_form:
                    return active_form

    return ""


def _workspace_from_payload(data: dict[str, object], *, cwd: str | None = None) -> str:
    """Extract the workspace directory from a runtime hook payload."""
    from grd.adapters.runtime_catalog import get_hook_payload_policy

    hook_payload = _hook_payload_policy(cwd) if cwd else get_hook_payload_policy()
    workspace_value = data.get("workspace")
    raw_workspace = (
        workspace_value
        if isinstance(workspace_value, str) and workspace_value
        else _first_string(workspace_value, *hook_payload.workspace_keys)
        or _first_string(data, *hook_payload.workspace_keys)
        or os.getcwd()
    )
    return _normalize_workspace_text(raw_workspace)


def _workspace_root_from_payload(
    data: dict[str, object],
    workspace_dir: str,
    *,
    cwd: str | None = None,
) -> str:
    """Resolve the project root for one hook payload workspace."""
    hook_payload = _hook_payload_policy(cwd or workspace_dir)
    workspace_value = data.get("workspace")
    project_dir = _first_string(workspace_value, *hook_payload.project_dir_keys) or _first_string(
        data,
        *hook_payload.project_dir_keys,
    )
    resolved_root = resolve_project_root(workspace_dir, project_dir=project_dir)
    return str(resolved_root) if resolved_root is not None else workspace_dir


def _read_context_remaining(data: dict[str, object], hook_payload) -> float | int | None:
    """Read remaining context percentage from runtime payload aliases."""
    remaining = _first_value(
        data.get("context_window"),
        *_merged_policy_keys(hook_payload, "context_remaining_keys", fallback=_CANONICAL_CONTEXT_REMAINING_KEYS),
    )
    if isinstance(remaining, (int, float)) and math.isfinite(remaining):
        return remaining
    return None


def _read_session_id(data: dict[str, object], hook_payload) -> str:
    """Read the runtime session id using the adapter-owned contract."""
    for container in (
        data,
        data.get("workspace"),
        data.get("model"),
        data.get("usage"),
        data.get("token_usage"),
    ):
        session_id = _first_string(container, *hook_payload.runtime_session_id_keys)
        if session_id:
            return session_id
    return ""


def _read_execution_state(workspace_dir: str | None = None) -> dict[str, object]:
    """Return the current normalized execution snapshot for the workspace."""
    from grd.core.observability import get_current_execution

    workspace_path = Path(workspace_dir) if workspace_dir else None
    snapshot = get_current_execution(workspace_path)
    return snapshot.model_dump(mode="json") if snapshot is not None else {}


def _read_runtime_hints(workspace_dir: str | None = None) -> dict[str, object]:
    """Return the shallow runtime hint payload for the workspace."""
    from grd.core.runtime_hints import build_runtime_hint_payload

    payload = build_runtime_hint_payload(
        Path(workspace_dir) if workspace_dir else None,
        include_recovery=False,
        include_cost=False,
        include_workflow_presets=False,
    )
    return payload.model_dump(mode="json")


def _project_state_dir(
    data: dict[str, object],
    *,
    workspace_dir: str,
    project_root: str,
    runtime_lookup_dir: str,
    active_runtime: str | None,
    hook_payload: object,
) -> str:
    """Route project-owned state helpers to the project root unless the workspace owns the live runtime."""

    if runtime_lookup_dir != workspace_dir:
        return runtime_lookup_dir
    if not project_root or project_root == workspace_dir:
        return runtime_lookup_dir
    if _workspace_mapping_prefers_local_statusline_lookup(data, hook_payload=hook_payload):
        return runtime_lookup_dir

    normalized_project_root = str(Path(project_root).expanduser().resolve(strict=False))

    if isinstance(active_runtime, str) and active_runtime:
        install_target = detect_runtime_install_target(
            active_runtime,
            cwd=Path(workspace_dir).expanduser().resolve(strict=False),
        )
        if install_target is not None and install_target.install_scope == SCOPE_LOCAL:
            return runtime_lookup_dir

    return normalized_project_root


def _execution_reason_label(reason: str | None, *, default: str) -> str:
    text = (reason or "").strip().lower()
    if not text:
        return default
    if "result" in text or "skeptical" in text or "fanout" in text:
        return "review"
    if "budget" in text or "time" in text:
        return "budget"
    if "user" in text or "review" in text or "approve" in text:
        return "user"
    if "depend" in text or "upstream" in text or "fanout" in text:
        return "dependency"
    if "anchor" in text or "checkpoint" in text:
        return "checkpoint"
    return default


def _elapsed_segment_label(started_at: object, updated_at: object) -> str:
    """Return a compact segment elapsed label like ``12m`` when timestamps parse."""
    if not isinstance(started_at, str) or not isinstance(updated_at, str):
        return ""
    try:
        from datetime import datetime

        start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        end = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    except ValueError:
        return ""
    elapsed_seconds = max(0, int((end - start).total_seconds()))
    if elapsed_seconds < 60:
        return f"{elapsed_seconds}s"
    if elapsed_seconds < 3600:
        return f"{elapsed_seconds // 60}m"
    return f"{elapsed_seconds // 3600}h"


def _execution_review_badge(snapshot: dict[str, object]) -> str:
    """Return a compact review/wait badge from a raw execution snapshot."""
    checkpoint_reason = _first_string(snapshot, "checkpoint_reason")
    waiting_reason = _first_string(snapshot, "waiting_reason")
    segment_status = _first_string(snapshot, "segment_status").lower()

    if bool(snapshot.get("skeptical_requestioning_required")):
        return "REVIEW:skeptical"
    if bool(snapshot.get("first_result_gate_pending")):
        return "REVIEW:first-result"
    if bool(snapshot.get("pre_fanout_review_pending")):
        return "REVIEW:pre-fanout"
    if bool(snapshot.get("waiting_for_review")):
        label = "checkpoint"
        if checkpoint_reason == "first_result":
            label = "first-result"
        elif checkpoint_reason == "skeptical_requestioning":
            label = "skeptical"
        elif checkpoint_reason == "pre_fanout":
            label = "pre-fanout"
        elif checkpoint_reason:
            label = checkpoint_reason.replace("_", "-")
        return f"REVIEW:{label}"
    if waiting_reason:
        return f"WAIT:{_execution_reason_label(waiting_reason, default='hold')}"
    if segment_status in {"paused", "ready_to_continue"}:
        return "RESUME" if _first_string(snapshot, "resume_file") else "PAUSED"
    if segment_status:
        return "EXEC" if segment_status == "active" else segment_status.upper().replace("_", "-")
    return ""


def _execution_badge(snapshot: dict[str, object], visibility: object | None = None) -> str:
    """Return a compact badge describing live execution state."""
    if not snapshot and visibility is None:
        return ""

    current_snapshot = snapshot
    classification = ""
    possibly_stalled = False
    if visibility is not None:
        current_execution = _object_value(visibility, "current_execution")
        if isinstance(current_execution, dict):
            current_snapshot = current_execution
        classification = _object_string(visibility, "status_classification")
        possibly_stalled = bool(_object_value(visibility, "possibly_stalled"))
        if not classification and isinstance(current_snapshot, dict):
            classification = _first_string(current_snapshot, "segment_status").lower()
    else:
        classification = _first_string(snapshot, "segment_status").lower()

    blocked_reason = _first_string(current_snapshot, "blocked_reason")
    if visibility is not None and not classification:
        return ""

    if visibility is not None:
        if classification == "blocked" or blocked_reason:
            badge = "BLOCKED"
        elif classification == "waiting":
            badge = _execution_review_badge(current_snapshot)
        elif classification == "paused-or-resumable":
            badge = "RESUME" if _first_string(current_snapshot, "resume_file") else "PAUSED"
        elif classification == "active":
            badge = "STALL?" if possibly_stalled else "EXEC"
        elif classification == "idle":
            return ""
        else:
            badge = _execution_review_badge(current_snapshot)
    else:
        badge = _execution_review_badge(current_snapshot)
        if not badge:
            return ""
        if blocked_reason:
            badge = "BLOCKED"

    cadence = _first_string(snapshot, "review_cadence")
    if badge == "STALL?" and visibility is not None:
        elapsed = _compact_age_label(_object_string(visibility, "last_updated_age_label"))
    else:
        elapsed = _elapsed_segment_label(snapshot.get("segment_started_at"), snapshot.get("updated_at"))
    parts = [badge]
    if cadence:
        parts.append(cadence)
    if elapsed:
        parts.append(elapsed)
    return " ".join(parts)


def _execution_artifact_label(snapshot: dict[str, object]) -> str:
    """Return the latest artifact, result, or rerun anchor label for live execution state."""
    if bool(snapshot.get("skeptical_requestioning_required")):
        weakest_anchor = _first_string(snapshot, "weakest_unchecked_anchor")
        if weakest_anchor:
            return weakest_anchor
    tangent_summary = _first_string(snapshot, "tangent_summary")
    if tangent_summary:
        tangent_decision = _first_string(snapshot, "tangent_decision")
        if tangent_decision:
            return f"{tangent_decision.replace('_', ' ')}: {tangent_summary}"
        return tangent_summary
    artifact = _first_string(snapshot, "last_artifact_path")
    if artifact:
        return Path(artifact).name
    last_result_label = _first_string(snapshot, "last_result_label")
    if last_result_label:
        return last_result_label
    last_result_id = _first_string(snapshot, "last_result_id")
    if last_result_id:
        return f"rerun anchor: {last_result_id}"
    return ""


def _latest_update_cache(workspace_dir: str | None = None) -> tuple[dict[str, object] | None, object | None]:
    """Return the highest-priority valid update cache and its candidate metadata."""
    from grd.hooks.runtime_detect import (
        RUNTIME_UNKNOWN,
        detect_active_runtime_with_grd_install,
        detect_runtime_install_target,
        get_update_cache_candidates,
        should_consider_update_cache_candidate,
    )

    workspace_path = resolve_project_root(workspace_dir) if workspace_dir else None
    active_installed_runtime = detect_active_runtime_with_grd_install(cwd=workspace_path)
    self_install = hook_layout.detect_self_owned_install(__file__)
    active_install_target = (
        detect_runtime_install_target(active_installed_runtime, cwd=workspace_path)
        if active_installed_runtime not in (None, "", RUNTIME_UNKNOWN)
        else None
    )
    if hook_layout.should_prefer_self_owned_install(
        self_install,
        active_install_target=active_install_target,
        workspace_path=workspace_path,
    ):
        cache_file = self_install.cache_file
        if cache_file.exists():
            try:
                cache = json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception as exc:
                _debug(f"Failed to parse update cache {cache_file}: {exc}")
            else:
                if isinstance(cache, dict):
                    candidate = hook_layout.self_owned_update_cache_candidate(self_install)
                    return cache, candidate

    preferred_runtime = active_installed_runtime if workspace_path is not None else None
    fallback_hit: tuple[dict[str, object], object] | None = None
    for candidate in get_update_cache_candidates(cwd=workspace_path, preferred_runtime=preferred_runtime):
        cache_file = candidate.path
        if not cache_file.exists():
            continue
        if not should_consider_update_cache_candidate(
            candidate,
            active_installed_runtime=active_installed_runtime,
            cwd=workspace_path,
        ):
            continue
        try:
            cache = json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception as exc:
            _debug(f"Failed to parse update cache {cache_file}: {exc}")
            continue

        if not isinstance(cache, dict):
            _debug(f"Ignoring non-object update cache {cache_file}")
            continue

        if getattr(candidate, "runtime", None):
            return cache, candidate
        if fallback_hit is None:
            fallback_hit = (cache, candidate)

    return fallback_hit if fallback_hit is not None else (None, None)


def _check_update(workspace_dir: str | None = None) -> str:
    """Check GRD update cache files for available updates."""
    cache, cache_candidate = _latest_update_cache(workspace_dir)
    if cache and cache.get("update_available"):
        self_install = hook_layout.detect_self_owned_install(__file__)
        if self_install is not None and cache_candidate is not None and cache_candidate.path == self_install.cache_file:
            command = self_install.update_command
            if command is None:
                return ""
            return f"\x1b[33m\u2b06 {command}\x1b[0m \u2502 "

        from grd.hooks.runtime_detect import (
            RUNTIME_UNKNOWN,
            _runtime_dir_has_grd_install,
            detect_active_runtime_with_grd_install,
            detect_install_scope,
            update_command_for_runtime,
        )

        workspace_path = resolve_project_root(workspace_dir) if workspace_dir else None
        runtime = getattr(cache_candidate, "runtime", None) or RUNTIME_UNKNOWN
        scope = getattr(cache_candidate, "scope", None)
        if runtime != RUNTIME_UNKNOWN and not _runtime_dir_has_grd_install(runtime, cwd=workspace_path):
            runtime = RUNTIME_UNKNOWN
            scope = None
        if runtime == RUNTIME_UNKNOWN:
            runtime = detect_active_runtime_with_grd_install(cwd=workspace_path)
        if scope is None and runtime != RUNTIME_UNKNOWN:
            scope = detect_install_scope(runtime, cwd=workspace_path)
        command = update_command_for_runtime(runtime, scope=scope)
        return f"\x1b[33m\u2b06 {command}\x1b[0m \u2502 "
    return ""


def main() -> None:
    """Entry point: read JSON from stdin, write ANSI statusline to stdout."""
    try:
        data = json.loads(sys.stdin.read())
    except Exception as exc:
        _debug(f"Failed to parse stdin JSON: {exc}")
        return

    if not isinstance(data, dict):
        return

    try:
        roots = _resolve_payload_roots(data, policy_getter=_root_resolution_policy)
        workspace_dir = roots.workspace_dir
        project_root = roots.project_root
        project_dir_present = roots.project_dir_present
        project_dir_trusted = roots.project_dir_trusted
        payload_policy = _hook_payload_policy(workspace_dir)
        if project_dir_trusted is True and _workspace_mapping_prefers_local_statusline_lookup(
            data,
            hook_payload=payload_policy,
        ):
            project_dir_trusted = False
        statusline_project_root = _statusline_project_root(workspace_dir)
        if statusline_project_root is not None:
            project_root = str(statusline_project_root)
        elif not project_dir_trusted:
            project_root = workspace_dir
        runtime_roots = SimpleNamespace(
            workspace_dir=workspace_dir,
            project_root=project_root,
            project_dir_present=project_dir_present,
            project_dir_trusted=project_dir_trusted,
        )
        runtime_lookup = resolve_runtime_lookup_context_from_payload_roots(
            runtime_roots,
            runtime_resolver=_payload_runtime,
        )
        runtime_lookup_dir = runtime_lookup.lookup_dir

        hook_payload = _hook_payload_policy(runtime_lookup_dir)
        project_state_dir = _project_state_dir(
            data,
            workspace_dir=workspace_dir,
            project_root=project_root,
            runtime_lookup_dir=runtime_lookup_dir,
            active_runtime=runtime_lookup.active_runtime,
            hook_payload=hook_payload,
        )

        session_id = _read_session_id(data, hook_payload)
        remaining = _read_context_remaining(data, hook_payload)
        runtime_hints = _read_runtime_hints(project_state_dir)
        visibility = _mapping(runtime_hints.get("execution"))
        execution = _mapping(visibility.get("current_execution")) or _read_execution_state(project_state_dir)

        ctx = _context_bar(remaining) if isinstance(remaining, (int, float)) and math.isfinite(remaining) else ""
        position = _read_position(project_state_dir)
        execution_badge = _execution_badge(execution, visibility or None)
        execution_task = _object_string(visibility, "current_task") or _first_string(execution, "current_task")
        task = execution_task or _read_current_task(session_id, project_state_dir)
        if execution_task:
            task = execution_task
        elif execution_badge:
            task = ""
        artifact_label = _execution_artifact_label(execution)
        grd_update = _check_update(project_state_dir)
        model_label = _read_model_label(data, hook_payload)
        workspace_label = _read_workspace_label(
            data,
            workspace_dir,
            project_root=project_root,
            hook_payload=hook_payload,
        )

        segments = [f"\x1b[2m{_STATUS_LABEL}\x1b[0m"]
        if model_label:
            segments.append(model_label)
        if workspace_label:
            segments.append(f"\x1b[2m{workspace_label}\x1b[0m")
        if execution_badge:
            segments.append(f"\x1b[35m{execution_badge}\x1b[0m")
        if task:
            segments.append(f"\x1b[1m{task}\x1b[0m")
        if artifact_label:
            segments.append(f"\x1b[2m{artifact_label}\x1b[0m")
        if position:
            segments.append(f"\x1b[36m{position}\x1b[0m")

        statusline = " \u2502 ".join(segments)
        if grd_update:
            statusline = f"{grd_update}{statusline}"

        sys.stdout.write(statusline)
        if ctx:
            sys.stdout.write(ctx)
    except Exception as exc:
        _debug(f"Statusline render failed: {exc}")
        sys.stdout.write("\x1b[2mGPD\x1b[0m")


if __name__ == "__main__":
    main()
