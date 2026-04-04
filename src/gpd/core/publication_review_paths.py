"""Shared path normalization helpers for publication review artifacts."""

from __future__ import annotations

import posixpath
import re
from pathlib import Path

__all__ = [
    "manuscript_matches_review_artifact_path",
    "normalize_review_path_label",
    "review_artifact_round",
]


def review_artifact_round(path: Path, *, pattern: re.Pattern[str]) -> tuple[int, str] | None:
    """Return the round number and suffix encoded in a review artifact filename."""
    match = pattern.fullmatch(path.name)
    if match is None:
        return None
    round_text = match.group("round")
    if round_text is None:
        return 1, ""
    if round_text.startswith("0"):
        return None
    round_number = int(round_text)
    if round_number <= 1:
        return None
    return round_number, match.group("round_suffix") or ""


def normalize_review_path_label(value: str) -> str:
    """Normalize artifact manuscript path labels across OS-specific separators."""
    normalized = value.strip().replace("\\", "/")
    if not normalized:
        return ""
    return posixpath.normpath(normalized)


def manuscript_matches_review_artifact_path(artifact_path: str, manuscript: Path, *, cwd: Path) -> bool:
    """Return whether a stored manuscript path points at the active manuscript."""
    normalized_artifact_path = normalize_review_path_label(artifact_path)
    if not normalized_artifact_path:
        return False

    resolved_manuscript = manuscript.expanduser().resolve(strict=False)
    resolved_cwd = cwd.expanduser().resolve(strict=False)
    candidates = {
        normalize_review_path_label(resolved_manuscript.as_posix()),
        normalize_review_path_label(manuscript.as_posix()),
    }
    try:
        candidates.add(normalize_review_path_label(resolved_manuscript.relative_to(resolved_cwd).as_posix()))
    except ValueError:
        pass
    return normalized_artifact_path in candidates
