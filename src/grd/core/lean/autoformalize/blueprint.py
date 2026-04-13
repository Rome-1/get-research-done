"""Stage 1: Blueprint-style context extraction from phase artifacts.

Per AUTOFORMALIZATION.md §8.2, the MVP does NOT attempt full leanblueprint
``\\lemma{...}\\uses{...}`` DAG rendering yet — that's Phase 3.1d territory.
The MVP just assembles the *grounded context* the candidate-generation stage
needs:

    - the informal claim text,
    - the active convention lock (from state.json),
    - a flag indicating whether the project is a physics project (which
      changes the retrieval library from Mathlib4 → Mathlib4 + PhysLean).

Pulled into its own module so the pipeline's orchestrator stays a thin
composition: the hard part (parsing state.json) never touches stage 3+.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from grd.core.state import load_state_json

__all__ = [
    "BlueprintContext",
    "extract_blueprint_context",
]


_PHYSICS_CONVENTION_KEYS: frozenset[str] = frozenset(
    {
        "metric_signature",
        "fourier_convention",
        "natural_units",
        "gauge_choice",
        "coordinate_system",
        "spin_basis",
        "gamma_matrix_convention",
    }
)
"""Convention keys whose presence indicates a physics project.

When any of these is set in the project's convention lock, the candidate
generator will prefer PhysLean identifiers where applicable. This is a
heuristic — users can still pass ``--physics`` to the CLI to force the
physics path regardless of the state.
"""


@dataclass(frozen=True)
class BlueprintContext:
    """Grounded context for one claim, ready to hand to stage 3.

    Immutable so the orchestrator can log / serialize it for debugging
    without fearing mutation by downstream stages.
    """

    claim: str
    conventions: dict[str, object] = field(default_factory=dict)
    physics: bool = False
    project_name: str | None = None
    phase: str | None = None


def extract_blueprint_context(
    *,
    claim: str,
    project_root: Path,
    phase: str | None = None,
    physics_override: bool | None = None,
) -> BlueprintContext:
    """Read state.json and package the context needed for candidate generation.

    ``physics_override`` wins over auto-detection: pass ``True`` to force the
    physics path (useful when the project's convention keys look general but
    the user knows the claim is physics), or ``False`` to suppress it.
    """
    state = load_state_json(project_root) or {}
    lock = state.get("convention_lock") or {}
    conventions = _flatten_conventions(lock if isinstance(lock, dict) else {})
    project_name = None
    if isinstance(state.get("project"), dict):
        project_name = state["project"].get("name")

    if physics_override is not None:
        physics = physics_override
    else:
        physics = any(key in conventions for key in _PHYSICS_CONVENTION_KEYS)

    return BlueprintContext(
        claim=claim.strip(),
        conventions=conventions,
        physics=physics,
        project_name=project_name,
        phase=phase,
    )


def _flatten_conventions(lock: dict[str, object]) -> dict[str, object]:
    """Merge canonical and custom-convention entries into a single dict.

    ``state.json`` serializes ``convention_lock`` as a dict with canonical
    keys at the top level plus a nested ``custom_conventions`` map. Callers
    of the pipeline only need a flat "what's set" view, so we collapse them
    here. Unset values (None, empty string) are dropped so the prompt isn't
    polluted with noise.
    """
    out: dict[str, object] = {}
    for key, val in lock.items():
        if key == "custom_conventions":
            continue
        if _is_set(val):
            out[key] = val
    custom = lock.get("custom_conventions")
    if isinstance(custom, dict):
        for key, val in custom.items():
            if _is_set(val):
                out[key] = val
    return out


def _is_set(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() not in {"", "NOT-SPECIFIED", "NOT_SPECIFIED", "unknown"}
    return True
