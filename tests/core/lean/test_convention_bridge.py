"""Tests for ``grd.core.lean.convention_bridge``.

Covers preamble generation from convention locks: supported field mapping,
unsupported fields → TODO comments, unknown values → sorry instances,
custom conventions, empty/unset handling, and the full ``generate_preamble``
filesystem path.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from grd.core.lean.convention_bridge import (
    ConventionMapping,
    generate_preamble,
    generate_preamble_from_lock,
)


class TestEmptyLock:
    """No conventions set — preamble should be a valid but empty namespace."""

    def test_empty_dict(self) -> None:
        result = generate_preamble_from_lock({})
        assert result.mapped_count == 0
        assert result.unsupported_count == 0
        assert result.unset_count == 18  # all 18 canonical fields
        assert "namespace Blueprint.Conventions" in result.preamble
        assert "end Blueprint.Conventions" in result.preamble
        # No instances emitted.
        assert "instance" not in result.preamble

    def test_all_unset_mappings_have_status_unset(self) -> None:
        result = generate_preamble_from_lock({})
        assert all(m.status == "unset" for m in result.mappings)
        assert len(result.mappings) == 18


class TestSupportedFields:
    """The 6 fields with known Lean type class counterparts."""

    def test_metric_signature_mostly_minus(self) -> None:
        result = generate_preamble_from_lock({"metric_signature": "mostly-minus"})
        assert result.mapped_count == 1
        assert "MetricSignature" in result.preamble
        assert "SignChoice.mostlyMinus" in result.preamble

    def test_metric_signature_alias(self) -> None:
        """The (+,-,-,-) alias should map to the same constructor."""
        result = generate_preamble_from_lock({"metric_signature": "(+,-,-,-)"})
        assert result.mapped_count == 1
        assert "SignChoice.mostlyMinus" in result.preamble

    def test_natural_units_si(self) -> None:
        result = generate_preamble_from_lock({"natural_units": "SI"})
        assert result.mapped_count == 1
        assert "NaturalUnits" in result.preamble
        assert "NaturalUnitsChoice.si" in result.preamble

    def test_natural_units_case_insensitive_si(self) -> None:
        result = generate_preamble_from_lock({"natural_units": "si"})
        assert result.mapped_count == 1
        assert "NaturalUnitsChoice.si" in result.preamble

    def test_fourier_convention_physics(self) -> None:
        result = generate_preamble_from_lock({"fourier_convention": "physics"})
        assert result.mapped_count == 1
        assert "FourierConvention" in result.preamble
        assert "FourierChoice.physics" in result.preamble

    def test_coordinate_system_spherical(self) -> None:
        result = generate_preamble_from_lock({"coordinate_system": "spherical"})
        assert result.mapped_count == 1
        assert "CoordinateSystem" in result.preamble
        assert "CoordinateChoice.spherical" in result.preamble

    def test_gamma_matrix_convention_weyl(self) -> None:
        result = generate_preamble_from_lock({"gamma_matrix_convention": "Weyl"})
        assert result.mapped_count == 1
        assert "GammaMatrixConvention" in result.preamble
        assert "GammaMatrixChoice.weyl" in result.preamble

    def test_levi_civita_sign_plus(self) -> None:
        result = generate_preamble_from_lock({"levi_civita_sign": "+1"})
        assert result.mapped_count == 1
        assert "LeviCivitaSign" in result.preamble
        assert "LeviCivitaSign.plus" in result.preamble

    def test_multiple_supported_fields(self) -> None:
        lock = {
            "metric_signature": "mostly-plus",
            "natural_units": "natural",
            "levi_civita_sign": "-1",
        }
        result = generate_preamble_from_lock(lock)
        assert result.mapped_count == 3
        assert "MetricSignature" in result.preamble
        assert "NaturalUnits" in result.preamble
        assert "LeviCivitaSign" in result.preamble


class TestUnsupportedFields:
    """Fields with no Lean type class → TODO comments."""

    def test_gauge_choice_emits_todo(self) -> None:
        result = generate_preamble_from_lock({"gauge_choice": "Lorenz"})
        assert result.unsupported_count == 1
        assert result.mapped_count == 0
        assert "-- TODO in Blueprint.Conventions: gauge_choice = Lorenz" in result.preamble
        mapping = next(m for m in result.mappings if m.field_name == "gauge_choice")
        assert mapping.status == "unsupported"
        assert mapping.todo is not None
        assert "ge-tau" in mapping.todo

    def test_regularization_scheme_emits_todo(self) -> None:
        result = generate_preamble_from_lock({"regularization_scheme": "dim-reg"})
        assert result.unsupported_count == 1
        mapping = next(m for m in result.mappings if m.field_name == "regularization_scheme")
        assert mapping.status == "unsupported"
        assert "RegularizationScheme" in mapping.todo  # suggested PascalCase class name


class TestUnknownValues:
    """Supported field with an unrecognized value → sorry instance."""

    def test_metric_unknown_value_emits_sorry(self) -> None:
        result = generate_preamble_from_lock({"metric_signature": "rindler"})
        assert result.unsupported_count == 1
        assert result.mapped_count == 0
        assert "sorry" in result.preamble
        assert "rindler" in result.preamble
        mapping = next(m for m in result.mappings if m.field_name == "metric_signature")
        assert mapping.status == "unknown_value"
        assert mapping.lean_class == "MetricSignature"


class TestCustomConventions:
    """The ``custom_conventions`` sub-dict."""

    def test_custom_convention_emits_todo(self) -> None:
        lock = {"custom_conventions": {"my_convention": "value1"}}
        result = generate_preamble_from_lock(lock)
        assert result.unsupported_count == 1
        assert "-- TODO in Blueprint.Conventions: custom.my_convention = value1" in result.preamble
        mapping = next(m for m in result.mappings if m.field_name == "custom.my_convention")
        assert mapping.status == "unsupported"

    def test_empty_custom_conventions_ignored(self) -> None:
        lock = {"custom_conventions": {}}
        result = generate_preamble_from_lock(lock)
        assert result.unsupported_count == 0

    def test_unset_custom_convention_ignored(self) -> None:
        lock = {"custom_conventions": {"empty_one": None}}
        result = generate_preamble_from_lock(lock)
        assert result.unsupported_count == 0


class TestUnsetSentinels:
    """Values that should be treated as 'not set'."""

    @pytest.mark.parametrize("sentinel", [None, "", "NOT-SPECIFIED", "NOT_SPECIFIED", "unknown", "null", "none"])
    def test_sentinel_treated_as_unset(self, sentinel: str | None) -> None:
        result = generate_preamble_from_lock({"metric_signature": sentinel})
        # metric_signature should be counted as unset, not mapped or unsupported.
        mapping = next(m for m in result.mappings if m.field_name == "metric_signature")
        assert mapping.status == "unset"
        assert result.mapped_count == 0


class TestPreambleStructure:
    """The generated Lean 4 code must be syntactically well-formed."""

    def test_header_comments_present(self) -> None:
        result = generate_preamble_from_lock({"metric_signature": "mostly-minus"})
        assert "do NOT edit by hand" in result.preamble
        assert "grd lean gen-conventions" in result.preamble

    def test_namespace_opens_and_closes(self) -> None:
        result = generate_preamble_from_lock({})
        lines = result.preamble.splitlines()
        assert any("namespace Blueprint.Conventions" in line for line in lines)
        assert any("end Blueprint.Conventions" in line for line in lines)

    def test_instance_uses_angle_brackets(self) -> None:
        result = generate_preamble_from_lock({"natural_units": "planck"})
        # Lean anonymous constructor ⟨...⟩
        assert "⟨" in result.preamble
        assert "⟩" in result.preamble


class TestGeneratePreamble:
    """Integration: ``generate_preamble`` reads state.json and optionally writes."""

    def test_writes_file_when_output_path_given(self, tmp_path: Path) -> None:
        # Create a minimal state.json with a convention lock.
        state_dir = tmp_path / ".grd"
        state_dir.mkdir()
        (state_dir / "state.json").write_text(
            '{"convention_lock": {"metric_signature": "mostly-minus"}}',
            encoding="utf-8",
        )
        out = tmp_path / "blueprint" / "Conventions.lean"

        result = generate_preamble(tmp_path, output_path=out)

        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "MetricSignature" in content
        assert result.path == str(out)
        assert result.mapped_count == 1

    def test_returns_preamble_without_writing_when_no_output_path(self, tmp_path: Path) -> None:
        state_dir = tmp_path / ".grd"
        state_dir.mkdir()
        (state_dir / "state.json").write_text('{"convention_lock": {}}', encoding="utf-8")

        result = generate_preamble(tmp_path)

        assert result.path is None
        assert "namespace Blueprint.Conventions" in result.preamble

    def test_missing_state_json_returns_empty_preamble(self, tmp_path: Path) -> None:
        result = generate_preamble(tmp_path)
        assert result.mapped_count == 0
        assert result.unsupported_count == 0


class TestConventionMappingModel:
    """Pydantic model round-trip / validation."""

    def test_mapped_roundtrip(self) -> None:
        m = ConventionMapping(
            field_name="metric_signature",
            value="mostly-minus",
            status="mapped",
            lean_instance="instance : MetricSignature := ⟨SignChoice.mostlyMinus⟩",
            lean_class="MetricSignature",
        )
        assert m.field_name == "metric_signature"
        assert m.status == "mapped"
        assert m.todo is None

    def test_unsupported_includes_todo(self) -> None:
        m = ConventionMapping(
            field_name="gauge_choice",
            value="Lorenz",
            status="unsupported",
            todo="Convention gauge_choice=Lorenz: no Lean type class",
        )
        assert m.todo is not None
        assert "Lorenz" in m.todo


class TestPreambleResultModel:
    """PreambleResult counts / shape."""

    def test_counts_consistent_with_mappings(self) -> None:
        result = generate_preamble_from_lock(
            {
                "metric_signature": "mostly-minus",
                "gauge_choice": "Lorenz",
            }
        )
        total = result.mapped_count + result.unsupported_count + result.unset_count
        assert total == len(result.mappings)
