"""Convention bridge: generate a Lean 4 preamble from the GRD convention lock.

Maps the 18-field convention lock from ``.grd/state.json`` to Lean 4 type
class instances so formal proofs inherit the same conventions as the informal
derivation.

Each convention field either:

- has a known Lean mapping → emits an ``instance`` declaration,
- has no Lean counterpart yet → emits a ``-- TODO`` comment documenting the
  gap, suitable for filing a ``discovered-from`` child of ge-tau.

The generated preamble is a standalone ``.lean`` file (``Blueprint/Conventions.lean``)
that the autoformalization pipeline imports in every compile attempt.

No external dependencies beyond GRD's own state loader.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from grd.core.state import load_state_json

__all__ = [
    "ConventionMapping",
    "PreambleResult",
    "generate_preamble",
    "generate_preamble_from_lock",
]


# ─── Known convention → Lean mappings ───────────────────────────────────────

# Each entry: (convention_key, lean_class, value_map)
# value_map maps convention values to Lean constructor expressions.
# When a value isn't in the map, we emit a sorry-commented instance.

_METRIC_VALUES: dict[str, str] = {
    "mostly-plus": "SignChoice.mostlyPlus",
    "mostly-minus": "SignChoice.mostlyMinus",
    "euclidean": "SignChoice.euclidean",
    # Aliases from the VALUE_ALIASES in conventions.py
    "(+,-,-,-)": "SignChoice.mostlyMinus",
    "+---": "SignChoice.mostlyMinus",
    "(-,+,+,+)": "SignChoice.mostlyPlus",
    "-+++": "SignChoice.mostlyPlus",
    "++++": "SignChoice.euclidean",
}

_NATURAL_UNITS_VALUES: dict[str, str] = {
    "natural": "NaturalUnitsChoice.natural",
    "SI": "NaturalUnitsChoice.si",
    "si": "NaturalUnitsChoice.si",
    "planck": "NaturalUnitsChoice.planck",
    "gaussian": "NaturalUnitsChoice.gaussian",
    "cgs": "NaturalUnitsChoice.cgs",
    "geometrized": "NaturalUnitsChoice.geometrized",
}

_FOURIER_VALUES: dict[str, str] = {
    "physics": "FourierChoice.physics",
    "math": "FourierChoice.math",
    "signal-processing": "FourierChoice.signalProcessing",
    "signal_processing": "FourierChoice.signalProcessing",
}

_COORDINATE_VALUES: dict[str, str] = {
    "cartesian": "CoordinateChoice.cartesian",
    "Cartesian": "CoordinateChoice.cartesian",
    "spherical": "CoordinateChoice.spherical",
    "cylindrical": "CoordinateChoice.cylindrical",
}

_GAMMA_MATRIX_VALUES: dict[str, str] = {
    "dirac": "GammaMatrixChoice.dirac",
    "Dirac": "GammaMatrixChoice.dirac",
    "weyl": "GammaMatrixChoice.weyl",
    "Weyl": "GammaMatrixChoice.weyl",
    "chiral": "GammaMatrixChoice.chiral",
    "majorana": "GammaMatrixChoice.majorana",
    "Majorana": "GammaMatrixChoice.majorana",
}

_LEVI_CIVITA_VALUES: dict[str, str] = {
    "+1": "LeviCivitaSign.plus",
    "plus": "LeviCivitaSign.plus",
    "-1": "LeviCivitaSign.minus",
    "minus": "LeviCivitaSign.minus",
}


@dataclass(frozen=True)
class _LeanMapping:
    """How to render one convention field as a Lean instance."""

    lean_class: str
    values: dict[str, str]


# Registry of convention fields that have known Lean counterparts.
_SUPPORTED_FIELDS: dict[str, _LeanMapping] = {
    "metric_signature": _LeanMapping("MetricSignature", _METRIC_VALUES),
    "natural_units": _LeanMapping("NaturalUnits", _NATURAL_UNITS_VALUES),
    "fourier_convention": _LeanMapping("FourierConvention", _FOURIER_VALUES),
    "coordinate_system": _LeanMapping("CoordinateSystem", _COORDINATE_VALUES),
    "gamma_matrix_convention": _LeanMapping("GammaMatrixConvention", _GAMMA_MATRIX_VALUES),
    "levi_civita_sign": _LeanMapping("LeviCivitaSign", _LEVI_CIVITA_VALUES),
}

# The full 18 canonical fields (order matches contracts.py ConventionLock).
_ALL_CONVENTION_FIELDS: tuple[str, ...] = (
    "metric_signature",
    "fourier_convention",
    "natural_units",
    "gauge_choice",
    "regularization_scheme",
    "renormalization_scheme",
    "coordinate_system",
    "spin_basis",
    "state_normalization",
    "coupling_convention",
    "index_positioning",
    "time_ordering",
    "commutation_convention",
    "levi_civita_sign",
    "generator_normalization",
    "covariant_derivative_sign",
    "gamma_matrix_convention",
    "creation_annihilation_order",
)


# ─── Result models ──────────────────────────────────────────────────────────


class ConventionMapping(BaseModel):
    """How one convention field was rendered (or why it wasn't)."""

    model_config = ConfigDict(extra="forbid")

    field_name: str
    value: str | None
    status: Literal["mapped", "unknown_value", "unsupported", "unset"]
    lean_instance: str | None = None
    lean_class: str | None = None
    todo: str | None = Field(
        default=None,
        description="TODO comment for unsupported fields — suitable for filing a discovered-from child of ge-tau.",
    )


class PreambleResult(BaseModel):
    """Outcome of preamble generation."""

    model_config = ConfigDict(extra="forbid")

    preamble: str
    path: str | None = None
    mappings: list[ConventionMapping] = Field(default_factory=list)
    mapped_count: int = 0
    unsupported_count: int = 0
    unset_count: int = 0


# ─── Core generation ────────────────────────────────────────────────────────


def _is_set(value: object) -> bool:
    """Check if a convention value is meaningfully set."""
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() not in {"", "NOT-SPECIFIED", "NOT_SPECIFIED", "unknown", "null", "none"}
    return True


def generate_preamble_from_lock(
    lock: dict[str, object],
    *,
    namespace: str = "GRDConventions",
) -> PreambleResult:
    """Generate a Lean 4 preamble from a convention lock dict.

    This is the pure-logic core — no filesystem or state.json dependency.
    ``lock`` is the flattened convention dict (same shape as
    ``BlueprintContext.conventions``).
    """
    lines: list[str] = [
        "-- Generated from .grd/state.json convention lock — do NOT edit by hand",
        "-- Regenerate with: grd lean gen-conventions",
        "",
        "namespace Blueprint.Conventions",
        "",
    ]
    mappings: list[ConventionMapping] = []
    mapped = 0
    unsupported = 0
    unset = 0

    for field_name in _ALL_CONVENTION_FIELDS:
        value = lock.get(field_name)

        if not _is_set(value):
            unset += 1
            mappings.append(ConventionMapping(field_name=field_name, value=None, status="unset"))
            continue

        str_value = str(value).strip()

        if field_name in _SUPPORTED_FIELDS:
            mapping = _SUPPORTED_FIELDS[field_name]
            lean_expr = mapping.values.get(str_value)
            if lean_expr is not None:
                instance_line = f"instance : {mapping.lean_class} := ⟨{lean_expr}⟩"
                lines.append(f"{instance_line}  -- {field_name} = {str_value}")
                mapped += 1
                mappings.append(
                    ConventionMapping(
                        field_name=field_name,
                        value=str_value,
                        status="mapped",
                        lean_instance=instance_line,
                        lean_class=mapping.lean_class,
                    )
                )
            else:
                # Known Lean class but unrecognized value — emit with sorry.
                instance_line = (
                    f'instance : {mapping.lean_class} := sorry  -- TODO: unknown value "{str_value}" for {field_name}'
                )
                lines.append(instance_line)
                unsupported += 1
                mappings.append(
                    ConventionMapping(
                        field_name=field_name,
                        value=str_value,
                        status="unknown_value",
                        lean_class=mapping.lean_class,
                        todo=f"Convention {field_name}={str_value}: value not in known Lean mapping. "
                        f"Add a constructor to {mapping.lean_class} or file discovered-from:ge-tau.",
                    )
                )
        else:
            # No Lean counterpart at all.
            todo_msg = (
                f"Convention {field_name}={str_value}: no Lean type class exists yet. "
                f"File discovered-from:ge-tau to add a {_suggested_class_name(field_name)} class."
            )
            lines.append(f"-- TODO in Blueprint.Conventions: {field_name} = {str_value}")
            lines.append(f"--   {todo_msg}")
            unsupported += 1
            mappings.append(
                ConventionMapping(
                    field_name=field_name,
                    value=str_value,
                    status="unsupported",
                    todo=todo_msg,
                )
            )

    # Handle custom_conventions.
    custom = lock.get("custom_conventions")
    if isinstance(custom, dict):
        for key, val in custom.items():
            if _is_set(val):
                str_val = str(val).strip()
                todo_msg = (
                    f"Custom convention {key}={str_val}: no Lean type class exists. "
                    f"File discovered-from:ge-tau to add support."
                )
                lines.append(f"-- TODO in Blueprint.Conventions: custom.{key} = {str_val}")
                lines.append(f"--   {todo_msg}")
                unsupported += 1
                mappings.append(
                    ConventionMapping(
                        field_name=f"custom.{key}",
                        value=str_val,
                        status="unsupported",
                        todo=todo_msg,
                    )
                )

    lines.append("")
    lines.append("end Blueprint.Conventions")
    lines.append("")

    preamble = "\n".join(lines)
    return PreambleResult(
        preamble=preamble,
        mappings=mappings,
        mapped_count=mapped,
        unsupported_count=unsupported,
        unset_count=unset,
    )


def generate_preamble(
    project_root: Path,
    *,
    output_path: Path | None = None,
    namespace: str = "GRDConventions",
) -> PreambleResult:
    """Generate a Lean preamble from the project's state.json convention lock.

    If ``output_path`` is provided, the preamble is written to disk and
    ``result.path`` is set to the written path. Otherwise, the preamble is
    returned in ``result.preamble`` only.
    """
    state = load_state_json(project_root) or {}
    lock = state.get("convention_lock") or {}
    if isinstance(lock, dict):
        flat = _flatten_lock(lock)
    else:
        flat = {}

    result = generate_preamble_from_lock(flat, namespace=namespace)

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result.preamble, encoding="utf-8")
        result = PreambleResult(
            preamble=result.preamble,
            path=str(output_path),
            mappings=result.mappings,
            mapped_count=result.mapped_count,
            unsupported_count=result.unsupported_count,
            unset_count=result.unset_count,
        )

    return result


def preamble_imports(result: PreambleResult) -> list[str]:
    """Extract import lines from a preamble for use in compile attempts.

    Returns module names suitable for passing to ``lean_check(imports=[...])``.
    Currently returns an empty list since the preamble is self-contained
    and does not require external imports. Reserved for when
    ``Blueprint.Conventions`` becomes a Lake dependency.
    """
    return []


def _flatten_lock(lock: dict[str, object]) -> dict[str, object]:
    """Flatten state.json convention_lock into a single dict.

    Mirrors ``blueprint.py:_flatten_conventions`` — kept local to avoid
    a circular import.
    """
    out: dict[str, object] = {}
    for key, val in lock.items():
        if key == "custom_conventions":
            continue
        if _is_set(val):
            out[key] = val
    custom = lock.get("custom_conventions")
    if isinstance(custom, dict):
        out["custom_conventions"] = {k: v for k, v in custom.items() if _is_set(v)}
    return out


def _suggested_class_name(field_name: str) -> str:
    """Convert a snake_case convention field to a PascalCase Lean class name."""
    return "".join(part.capitalize() for part in field_name.split("_"))
