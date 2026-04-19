"""Tests for grd.core.templates — project template discovery and stamping."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from grd.core.templates import (
    ProjectTemplate,
    StampResult,
    get_project_template,
    list_project_templates,
    stamp_project_template,
)


# ── Discovery ──────────────────────────────────────────────────────────────


class TestListProjectTemplates:
    def test_returns_at_least_simple_mechanics(self) -> None:
        templates = list_project_templates()
        names = [t.name for t in templates]
        assert "simple-mechanics" in names

    def test_all_templates_have_required_fields(self) -> None:
        for t in list_project_templates():
            assert t.name
            assert t.domain
            assert t.files
            assert t.path.is_dir()


class TestGetProjectTemplate:
    def test_simple_mechanics_exists(self) -> None:
        t = get_project_template("simple-mechanics")
        assert t.name == "simple-mechanics"
        assert t.domain == "physics"
        assert t.project_type == "classical-mechanics"
        assert t.phases == 1
        assert "derived-energy-conservation" in t.claims

    def test_unknown_template_raises_key_error(self) -> None:
        with pytest.raises(KeyError, match="Unknown project template"):
            get_project_template("nonexistent-template")

    def test_error_message_lists_available(self) -> None:
        with pytest.raises(KeyError, match="simple-mechanics"):
            get_project_template("nonexistent-template")


# ── Template files ─────────────────────────────────────────────────────────


class TestSimpleMechanicsTemplateFiles:
    @pytest.fixture()
    def template(self) -> ProjectTemplate:
        return get_project_template("simple-mechanics")

    def test_all_declared_files_exist(self, template: ProjectTemplate) -> None:
        for f in template.files:
            assert (template.path / f).exists(), f"Missing template file: {f}"

    def test_project_md_has_sho_content(self, template: ProjectTemplate) -> None:
        content = (template.path / "PROJECT.md").read_text()
        assert "Harmonic Oscillator" in content
        assert "H(q, p)" in content or "H(q,p)" in content
        assert "energy conservation" in content.lower()

    def test_conventions_md_has_si_units(self, template: ProjectTemplate) -> None:
        content = (template.path / "CONVENTIONS.md").read_text()
        assert "SI" in content
        assert "kilogram" in content or "kg" in content
        assert "metre" in content or "meter" in content or " m " in content

    def test_roadmap_has_phase_1(self, template: ProjectTemplate) -> None:
        content = (template.path / "ROADMAP.md").read_text()
        assert "Phase 1" in content
        assert "energy" in content.lower() or "conservation" in content.lower()
        assert "derived-energy-conservation" in content

    def test_state_json_is_valid(self, template: ProjectTemplate) -> None:
        data = json.loads((template.path / "state.json").read_text())
        assert data["_version"] == 1
        assert data["position"]["phase"] == 1

    def test_state_json_has_convention_lock(self, template: ProjectTemplate) -> None:
        data = json.loads((template.path / "state.json").read_text())
        cl = data["convention_lock"]
        assert "SI" in cl["natural_units"]
        assert "Cartesian" in cl["coordinate_system"]

    def test_state_json_has_claim(self, template: ProjectTemplate) -> None:
        data = json.loads((template.path / "state.json").read_text())
        claims = data["project_contract"]["claims"]
        assert len(claims) == 1
        claim = claims[0]
        assert claim["id"] == "derived-energy-conservation"
        assert claim["claim_kind"] == "theorem"

    def test_state_json_has_tier_scaffolding(self, template: ProjectTemplate) -> None:
        data = json.loads((template.path / "state.json").read_text())
        claim = data["project_contract"]["claims"][0]
        vs = claim["verification_status"]
        # Tier 1-4 have pass status
        assert vs["tier_1"]["dimensional_analysis"]["status"] == "pass"
        assert vs["tier_1"]["limiting_cases"]["status"] == "pass"
        assert vs["tier_2"]["conservation_laws"]["status"] == "pass"
        assert vs["tier_4"]["symmetry_check"]["status"] == "pass"
        # Tier 5 is available (not yet proved)
        assert vs["tier_5"]["formal_proof"]["status"] == "available"


# ── Stamping ───────────────────────────────────────────────────────────────


class TestStampProjectTemplate:
    @pytest.fixture()
    def target_dir(self, tmp_path: Path) -> Path:
        return tmp_path / "demo-sho"

    def test_stamps_all_files(self, target_dir: Path) -> None:
        target_dir.mkdir()
        result = stamp_project_template(target_dir, "simple-mechanics")
        assert result.template == "simple-mechanics"
        assert set(result.files_written) == {
            "PROJECT.md",
            "CONVENTIONS.md",
            "ROADMAP.md",
            "state.json",
        }
        assert result.skipped == []
        assert (target_dir / ".grd" / "PROJECT.md").exists()
        assert (target_dir / ".grd" / "CONVENTIONS.md").exists()
        assert (target_dir / ".grd" / "ROADMAP.md").exists()
        assert (target_dir / ".grd" / "state.json").exists()

    def test_creates_planning_dir(self, target_dir: Path) -> None:
        target_dir.mkdir()
        stamp_project_template(target_dir, "simple-mechanics")
        assert (target_dir / ".grd").is_dir()

    def test_skips_existing_files_without_force(self, target_dir: Path) -> None:
        target_dir.mkdir()
        (target_dir / ".grd").mkdir()
        (target_dir / ".grd" / "PROJECT.md").write_text("existing content")
        result = stamp_project_template(target_dir, "simple-mechanics")
        assert "PROJECT.md" in result.skipped
        assert "PROJECT.md" not in result.files_written
        # Existing content preserved
        assert (target_dir / ".grd" / "PROJECT.md").read_text() == "existing content"

    def test_force_overwrites_existing(self, target_dir: Path) -> None:
        target_dir.mkdir()
        (target_dir / ".grd").mkdir()
        (target_dir / ".grd" / "PROJECT.md").write_text("existing content")
        result = stamp_project_template(target_dir, "simple-mechanics", force=True)
        assert "PROJECT.md" in result.files_written
        assert "PROJECT.md" not in result.skipped
        assert "existing content" not in (target_dir / ".grd" / "PROJECT.md").read_text()

    def test_date_placeholder_replaced(self, target_dir: Path) -> None:
        target_dir.mkdir()
        stamp_project_template(target_dir, "simple-mechanics")
        content = (target_dir / ".grd" / "CONVENTIONS.md").read_text()
        assert "{{created_date}}" not in content
        # Should have an ISO date like 2026-04-19
        assert "202" in content  # year prefix

    def test_state_json_is_valid_after_stamp(self, target_dir: Path) -> None:
        target_dir.mkdir()
        stamp_project_template(target_dir, "simple-mechanics")
        data = json.loads((target_dir / ".grd" / "state.json").read_text())
        assert data["_version"] == 1
        assert data["project_contract"]["claims"][0]["id"] == "derived-energy-conservation"

    def test_unknown_template_raises(self, target_dir: Path) -> None:
        target_dir.mkdir()
        with pytest.raises(KeyError, match="Unknown project template"):
            stamp_project_template(target_dir, "does-not-exist")

    def test_result_is_dataclass(self, target_dir: Path) -> None:
        import dataclasses

        target_dir.mkdir()
        result = stamp_project_template(target_dir, "simple-mechanics")
        assert dataclasses.is_dataclass(result)
        d = dataclasses.asdict(result)
        assert d["template"] == "simple-mechanics"
