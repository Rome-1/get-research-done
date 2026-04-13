"""Autoformalization configuration loaded from ``.grd/lean-env.json``.

The pipeline reads its thresholds, candidate count, and repair budget from an
``autoformalize`` section nested in the existing ``lean-env.json`` file so we
don't proliferate config files. Defaults match the MVP targets from
AUTOFORMALIZATION.md §8.2:

- N=4 candidates per claim (MVP; pro pipeline uses N=16)
- APOLLO repair budget 15 compiles/claim (§8.2 says 10-20)
- auto-accept at SBERT ≥ 0.85
- escalate below 0.7
- 0.7 - 0.85 requires symbolic-cluster consensus

These live here, not in env.py, so the MVP tactic-search code keeps zero
dependency on the autoformalization layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from grd.core.lean.env import load_env

__all__ = [
    "DEFAULT_AUTO_ACCEPT_SIMILARITY",
    "DEFAULT_ESCALATE_BELOW_SIMILARITY",
    "DEFAULT_MODEL_ID",
    "DEFAULT_NUM_CANDIDATES",
    "DEFAULT_REPAIR_BUDGET",
    "AutoformalizeConfig",
    "load_autoformalize_config",
]


DEFAULT_NUM_CANDIDATES = 4
DEFAULT_REPAIR_BUDGET = 15
DEFAULT_AUTO_ACCEPT_SIMILARITY = 0.85
DEFAULT_ESCALATE_BELOW_SIMILARITY = 0.70
DEFAULT_MODEL_ID = "claude-sonnet-4-5"


@dataclass(frozen=True)
class AutoformalizeConfig:
    """Resolved autoformalization knobs for a project.

    Immutable so the orchestrator can pass it freely across stages without
    worrying about accidental mutation mid-run.
    """

    num_candidates: int = DEFAULT_NUM_CANDIDATES
    repair_budget: int = DEFAULT_REPAIR_BUDGET
    auto_accept_similarity: float = DEFAULT_AUTO_ACCEPT_SIMILARITY
    escalate_below_similarity: float = DEFAULT_ESCALATE_BELOW_SIMILARITY
    model_id: str = DEFAULT_MODEL_ID
    mathlib_names_path: str | None = None
    physlean_names_path: str | None = None

    def __post_init__(self) -> None:
        if self.num_candidates < 1:
            raise ValueError("num_candidates must be >= 1")
        if self.repair_budget < 0:
            raise ValueError("repair_budget must be >= 0")
        if not 0.0 <= self.escalate_below_similarity <= self.auto_accept_similarity <= 1.0:
            raise ValueError("thresholds must satisfy 0 <= escalate_below_similarity <= auto_accept_similarity <= 1")


def load_autoformalize_config(project_root: Path) -> AutoformalizeConfig:
    """Read ``autoformalize`` section from ``.grd/lean-env.json``.

    Unknown keys are ignored (forward-compatible). Missing section or missing
    individual keys fall back to module-level defaults — callers can rely on
    always getting a fully populated config without special-casing "no file".
    """
    data = load_env(project_root)
    section = data.get("autoformalize") or {}
    if not isinstance(section, dict):
        section = {}

    def _get(key: str, default: object) -> object:
        val = section.get(key)
        return val if val is not None else default

    return AutoformalizeConfig(
        num_candidates=int(_get("num_candidates", DEFAULT_NUM_CANDIDATES)),  # type: ignore[call-overload]
        repair_budget=int(_get("repair_budget", DEFAULT_REPAIR_BUDGET)),  # type: ignore[call-overload]
        auto_accept_similarity=float(_get("auto_accept_similarity", DEFAULT_AUTO_ACCEPT_SIMILARITY)),  # type: ignore[call-overload]
        escalate_below_similarity=float(
            _get("escalate_below_similarity", DEFAULT_ESCALATE_BELOW_SIMILARITY)  # type: ignore[call-overload]
        ),
        model_id=str(_get("model_id", DEFAULT_MODEL_ID)),
        mathlib_names_path=(str(section["mathlib_names_path"]) if section.get("mathlib_names_path") else None),
        physlean_names_path=(str(section["physlean_names_path"]) if section.get("physlean_names_path") else None),
    )
