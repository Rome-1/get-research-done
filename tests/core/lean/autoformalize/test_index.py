"""Tests for ``grd.core.lean.autoformalize.index``.

Exercises Suffix Array Check, identifier extraction, and default-index
loading from ``.grd/mathlib4-names.txt``.
"""

from __future__ import annotations

from pathlib import Path

from grd.core.constants import PLANNING_DIR_NAME
from grd.core.lean.autoformalize.config import AutoformalizeConfig
from grd.core.lean.autoformalize.index import (
    MATHLIB_NAMES_FILE,
    PHYSLEAN_NAMES_FILE,
    NameIndex,
    extract_identifiers,
    load_default_index,
)


def test_empty_index_disables_unknown_detection() -> None:
    idx = NameIndex.empty()
    assert idx.size == 0
    assert idx.unknown_identifiers("theorem foo : Nat.Prime 7 := sorry") == []


def test_sample_is_deterministic_sorted_order() -> None:
    idx = NameIndex.from_iterable(["Zebra", "Alpha", "Nat.Prime", "Real.pi"])
    assert idx.sample(3) == ["Alpha", "Nat.Prime", "Real.pi"]
    # Asking for more than we have returns everything, no error.
    assert len(idx.sample(100)) == idx.size


def test_sample_of_zero_is_empty() -> None:
    idx = NameIndex.from_iterable(["Alpha", "Beta"])
    assert idx.sample(0) == []
    assert idx.sample(-5) == []


def test_unknown_identifiers_flags_camelcase_and_qualified_names() -> None:
    idx = NameIndex.from_iterable(["Nat.Prime", "Real.pi"])
    source = "theorem foo : Nat.Prime 7 ∧ Real.pi > 0 ∧ IrratNum 2 := by sorry"
    unknown = idx.unknown_identifiers(source)
    # Nat.Prime + Real.pi are known; IrratNum is a hallucination.
    assert "IrratNum" in unknown
    assert "Nat.Prime" not in unknown
    assert "Real.pi" not in unknown


def test_unknown_identifiers_ignores_local_bindings() -> None:
    """Single-word lowercase tokens are local bindings — never flagged."""
    idx = NameIndex.from_iterable(["Nat.Prime"])
    source = "theorem foo (n : Nat) (h : n > 0) : Nat.Prime n ∨ True := by sorry"
    # n, h, foo, by, sorry, theorem — none get flagged as "unknown Mathlib".
    assert idx.unknown_identifiers(source) == []


def test_unknown_identifiers_deduplicates() -> None:
    idx = NameIndex.from_iterable(["Nat.Prime"])
    source = "IrratNum IrratNum IrratNum"
    assert idx.unknown_identifiers(source) == ["IrratNum"]


def test_extract_identifiers_handles_unicode_subscripts() -> None:
    # Lean 4 happily uses subscripts in identifiers; the extractor must preserve them.
    toks = extract_identifiers("theorem f (a₁ a₂ : Nat) : a₁ + a₂ = a₂ + a₁ := sorry")
    assert "a₁" in toks
    assert "a₂" in toks


def test_load_default_index_reads_mathlib_and_physlean(tmp_path: Path) -> None:
    grd_dir = tmp_path / PLANNING_DIR_NAME
    grd_dir.mkdir()
    (grd_dir / MATHLIB_NAMES_FILE).write_text("Nat.Prime\nReal.pi\n# a comment\n\n")
    (grd_dir / PHYSLEAN_NAMES_FILE).write_text("PhysLean.Metric\n")

    cfg = AutoformalizeConfig()
    idx = load_default_index(tmp_path, cfg)
    assert "Nat.Prime" in idx.names
    assert "Real.pi" in idx.names
    assert "PhysLean.Metric" in idx.names
    # Comments and blank lines stripped.
    assert "# a comment" not in idx.names
    assert "" not in idx.names
    assert MATHLIB_NAMES_FILE in idx.source
    assert PHYSLEAN_NAMES_FILE in idx.source


def test_load_default_index_respects_configured_path(tmp_path: Path) -> None:
    grd_dir = tmp_path / PLANNING_DIR_NAME
    grd_dir.mkdir()
    custom = tmp_path / "elsewhere" / "names.txt"
    custom.parent.mkdir()
    custom.write_text("Custom.Name\n")
    cfg = AutoformalizeConfig(mathlib_names_path="elsewhere/names.txt")
    idx = load_default_index(tmp_path, cfg)
    assert "Custom.Name" in idx.names


def test_load_default_index_returns_empty_when_files_absent(tmp_path: Path) -> None:
    cfg = AutoformalizeConfig()
    idx = load_default_index(tmp_path, cfg)
    assert idx.size == 0
    assert idx.source == ""
