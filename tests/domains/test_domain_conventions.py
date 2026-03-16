"""Tests for domain-aware convention operations.

Validates that convention set/list/check/normalize functions work correctly
when provided with a DomainContext from a domain pack, using both the bundled
physics domain and a synthetic test domain.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from grd.contracts import ConventionLock
from grd.core.conventions import (
    convention_check,
    convention_list,
    convention_set,
    normalize_key,
    normalize_value,
)
from grd.domains.loader import (
    ContentHealthError,
    DomainContext,
    DomainPack,
    check_content_health,
    load_domain,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture()
def physics_ctx() -> DomainContext:
    """Load the bundled physics domain pack."""
    ctx = load_domain("physics")
    assert ctx is not None, "Bundled physics domain pack should always be available"
    return ctx


@pytest.fixture()
def biology_domain(tmp_path: Path) -> DomainContext:
    """Create a synthetic biology domain pack for testing."""
    domain_dir = tmp_path / "biology"
    domain_dir.mkdir()
    (domain_dir / "domain.yaml").write_text(dedent("""\
        name: biology
        display_name: Biology
        description: Molecular and cell biology research domain.
        version: 1
        conventions_file: conventions/convention-fields.yaml
    """))
    conv_dir = domain_dir / "conventions"
    conv_dir.mkdir()
    (conv_dir / "convention-fields.yaml").write_text(dedent("""\
        fields:
          - name: organism
            label: "Model organism"
            description: "Primary model organism"
            aliases: ["species"]
            value_aliases:
              "fruit fly": "drosophila-melanogaster"
              "worm": "c-elegans"
              "mouse": "mus-musculus"
          - name: sequence_format
            label: "Sequence format"
            description: "DNA/RNA/protein sequence format"
            aliases: ["seqfmt"]
          - name: alignment_tool
            label: "Alignment tool"
            description: "Sequence alignment tool"
    """))
    pack = DomainPack(
        name="biology",
        display_name="Biology",
        description="Test biology domain",
        version=1,
        pack_path=domain_dir,
    )
    return DomainContext(pack)


# ─── Physics domain pack tests ──────────────────────────────────────────────


class TestPhysicsDomainContext:
    def test_physics_domain_has_18_convention_fields(self, physics_ctx: DomainContext) -> None:
        assert len(physics_ctx.convention_fields) == 18

    def test_physics_known_conventions_match_module_constant(self, physics_ctx: DomainContext) -> None:
        from grd.core.conventions import KNOWN_CONVENTIONS

        assert physics_ctx.known_convention_names == KNOWN_CONVENTIONS

    def test_physics_key_aliases_match_module_constant(self, physics_ctx: DomainContext) -> None:
        from grd.core.conventions import KEY_ALIASES

        assert physics_ctx.key_aliases == KEY_ALIASES

    def test_physics_value_aliases_match_module_constant(self, physics_ctx: DomainContext) -> None:
        from grd.core.conventions import VALUE_ALIASES

        assert physics_ctx.value_aliases == VALUE_ALIASES

    def test_physics_labels_match_module_constant(self, physics_ctx: DomainContext) -> None:
        from grd.core.conventions import CONVENTION_LABELS

        assert physics_ctx.convention_labels == CONVENTION_LABELS

    def test_physics_content_types(self, physics_ctx: DomainContext) -> None:
        assert set(physics_ctx.content_types) == {"subfields", "protocols", "errors"}

    def test_physics_content_dir_accessor(self, physics_ctx: DomainContext) -> None:
        pack_path = physics_ctx.pack_path
        assert physics_ctx.content_dir("protocols") == pack_path / "protocols"
        assert physics_ctx.content_dir("errors") == pack_path / "errors"
        assert physics_ctx.content_dir("subfields") == pack_path / "subfields"

    def test_physics_content_dir_unknown_returns_none(self, physics_ctx: DomainContext) -> None:
        assert physics_ctx.content_dir("nonexistent") is None

    def test_physics_backward_compat_properties(self, physics_ctx: DomainContext) -> None:
        """The convenience .protocols_dir / .errors_dir / .subfields_dir still work."""
        pack_path = physics_ctx.pack_path
        assert physics_ctx.protocols_dir == pack_path / "protocols"
        assert physics_ctx.errors_dir == pack_path / "errors"
        assert physics_ctx.subfields_dir == pack_path / "subfields"


class TestPhysicsDomainConventionOps:
    def test_normalize_key_with_physics_ctx(self, physics_ctx: DomainContext) -> None:
        assert normalize_key("metric", domain_ctx=physics_ctx) == "metric_signature"
        assert normalize_key("units", domain_ctx=physics_ctx) == "natural_units"

    def test_normalize_value_with_physics_ctx(self, physics_ctx: DomainContext) -> None:
        assert normalize_value("metric_signature", "+---", domain_ctx=physics_ctx) == "mostly-minus"

    def test_convention_set_with_physics_ctx(self, physics_ctx: DomainContext) -> None:
        lock = ConventionLock()
        result = convention_set(lock, "metric", "mostly-minus", domain_ctx=physics_ctx)
        assert result.updated is True
        assert result.key == "metric_signature"
        assert lock.metric_signature == "mostly-minus"

    def test_convention_list_with_physics_ctx(self, physics_ctx: DomainContext) -> None:
        lock = ConventionLock(metric_signature="mostly-minus")
        result = convention_list(lock, domain_ctx=physics_ctx)
        assert result.canonical_total == 18
        assert result.set_count == 1

    def test_convention_check_with_physics_ctx(self, physics_ctx: DomainContext) -> None:
        lock = ConventionLock()
        result = convention_check(lock, domain_ctx=physics_ctx)
        assert result.missing_count == 18
        assert result.complete is False


# ─── Custom domain (biology) tests ──────────────────────────────────────────


class TestCustomDomainConventionOps:
    def test_biology_has_3_convention_fields(self, biology_domain: DomainContext) -> None:
        assert len(biology_domain.convention_fields) == 3
        names = [f.name for f in biology_domain.convention_fields]
        assert names == ["organism", "sequence_format", "alignment_tool"]

    def test_biology_key_aliases(self, biology_domain: DomainContext) -> None:
        assert biology_domain.key_aliases == {"species": "organism", "seqfmt": "sequence_format"}

    def test_biology_value_aliases(self, biology_domain: DomainContext) -> None:
        assert "organism" in biology_domain.value_aliases
        assert biology_domain.value_aliases["organism"]["fruit fly"] == "drosophila-melanogaster"

    def test_normalize_key_with_biology_ctx(self, biology_domain: DomainContext) -> None:
        assert normalize_key("species", domain_ctx=biology_domain) == "organism"
        # Physics alias should NOT work in biology context
        assert normalize_key("metric", domain_ctx=biology_domain) == "metric"  # not resolved

    def test_normalize_value_with_biology_ctx(self, biology_domain: DomainContext) -> None:
        assert normalize_value("organism", "fruit fly", domain_ctx=biology_domain) == "drosophila-melanogaster"
        assert normalize_value("organism", "worm", domain_ctx=biology_domain) == "c-elegans"

    def test_convention_set_biology_field_goes_to_custom(self, biology_domain: DomainContext) -> None:
        """Biology fields are not in ConventionLock model — they go to custom_conventions."""
        lock = ConventionLock()
        result = convention_set(lock, "species", "fruit fly", domain_ctx=biology_domain)
        assert result.updated is True
        assert result.key == "organism"
        # Since "organism" is not a ConventionLock model field, it goes to custom_conventions
        assert lock.custom_conventions.get("organism") == "drosophila-melanogaster"

    def test_convention_list_biology_shows_3_canonical(self, biology_domain: DomainContext) -> None:
        lock = ConventionLock()
        lock.custom_conventions["organism"] = "drosophila-melanogaster"
        result = convention_list(lock, domain_ctx=biology_domain)
        assert result.canonical_total == 3
        assert result.set_count == 1
        assert "organism" in result.conventions
        assert result.conventions["organism"].canonical is True

    def test_convention_check_biology_missing_all(self, biology_domain: DomainContext) -> None:
        lock = ConventionLock()
        result = convention_check(lock, domain_ctx=biology_domain)
        assert result.total == 3
        assert result.missing_count == 3
        assert result.complete is False

    def test_convention_check_biology_complete(self, biology_domain: DomainContext) -> None:
        lock = ConventionLock()
        lock.custom_conventions["organism"] = "drosophila-melanogaster"
        lock.custom_conventions["sequence_format"] = "FASTA"
        lock.custom_conventions["alignment_tool"] = "BLAST"
        result = convention_check(lock, domain_ctx=biology_domain)
        assert result.total == 3
        assert result.set_count == 3
        assert result.complete is True

    def test_biology_immutability_gate(self, biology_domain: DomainContext) -> None:
        """Once a biology convention is set, it requires force to overwrite."""
        lock = ConventionLock()
        convention_set(lock, "organism", "drosophila-melanogaster", domain_ctx=biology_domain)
        result = convention_set(lock, "organism", "mus-musculus", domain_ctx=biology_domain)
        assert result.updated is False
        assert result.reason == "convention_already_set"
        # Force overwrite
        result = convention_set(lock, "organism", "mus-musculus", domain_ctx=biology_domain, force=True)
        assert result.updated is True


# ─── No domain context (backward compatibility) ─────────────────────────────


class TestNoDomainContext:
    """Verify that omitting domain_ctx gives identical behavior to before."""

    def test_normalize_key_no_ctx(self) -> None:
        assert normalize_key("metric") == "metric_signature"

    def test_normalize_value_no_ctx(self) -> None:
        assert normalize_value("metric_signature", "+---") == "mostly-minus"

    def test_convention_set_no_ctx(self) -> None:
        lock = ConventionLock()
        result = convention_set(lock, "metric", "mostly-minus")
        assert result.updated is True
        assert lock.metric_signature == "mostly-minus"

    def test_convention_list_no_ctx(self) -> None:
        lock = ConventionLock(metric_signature="mostly-minus")
        result = convention_list(lock)
        assert result.canonical_total == 18

    def test_convention_check_no_ctx(self) -> None:
        lock = ConventionLock()
        result = convention_check(lock)
        assert result.missing_count == 18


# ─── Domain loading tests ───────────────────────────────────────────────────


class TestDomainLoading:
    def test_load_physics_domain(self) -> None:
        ctx = load_domain("physics")
        assert ctx is not None
        assert ctx.name == "physics"

    def test_load_nonexistent_domain_returns_none(self) -> None:
        ctx = load_domain("nonexistent-domain-xyz")
        assert ctx is None

    def test_list_available_domains_includes_physics(self) -> None:
        from grd.domains.loader import list_available_domains

        domains = list_available_domains()
        assert "physics" in domains

    def test_project_local_domain_override(self, tmp_path: Path) -> None:
        """A project-local .grd/domain/ pack overrides bundled packs."""
        domain_dir = tmp_path / ".grd" / "domain"
        domain_dir.mkdir(parents=True)
        (domain_dir / "domain.yaml").write_text(dedent("""\
            name: custom-project
            display_name: Custom Project Domain
            description: Project-specific domain override.
            version: 1
        """))
        from grd.domains.loader import resolve_domain_pack_path

        # With project_root, should find the project-local pack
        path = resolve_domain_pack_path("physics", project_root=tmp_path)
        assert path == domain_dir

    def test_load_domain_with_content_section(self, tmp_path: Path) -> None:
        """A domain.yaml with a 'content' section populates content_dirs."""
        from grd.domains.loader import _parse_domain_yaml

        domain_dir = tmp_path / "test-domain"
        domain_dir.mkdir()
        (domain_dir / "domain.yaml").write_text(dedent("""\
            name: test-domain
            display_name: Test Domain
            description: A test domain.
            version: 1
            content:
              protocols: protocols
              errors: errors
              verification: verification
        """))
        pack = _parse_domain_yaml(domain_dir)
        assert pack.content_dirs == {
            "protocols": "protocols",
            "errors": "errors",
            "verification": "verification",
        }

    def test_load_domain_with_legacy_dir_fields(self, tmp_path: Path) -> None:
        """Legacy *_dir fields are still parsed into content_dirs."""
        from grd.domains.loader import _parse_domain_yaml

        domain_dir = tmp_path / "legacy-domain"
        domain_dir.mkdir()
        (domain_dir / "domain.yaml").write_text(dedent("""\
            name: legacy-domain
            display_name: Legacy Domain
            description: A domain using old-style *_dir fields.
            version: 1
            subfields_dir: my-subfields
            protocols_dir: my-protocols
            errors_dir: my-errors
        """))
        pack = _parse_domain_yaml(domain_dir)
        assert pack.content_dirs == {
            "subfields": "my-subfields",
            "protocols": "my-protocols",
            "errors": "my-errors",
        }

    def test_content_section_takes_precedence_over_legacy(self, tmp_path: Path) -> None:
        """When both content section and legacy fields exist, content wins."""
        from grd.domains.loader import _parse_domain_yaml

        domain_dir = tmp_path / "mixed-domain"
        domain_dir.mkdir()
        (domain_dir / "domain.yaml").write_text(dedent("""\
            name: mixed-domain
            display_name: Mixed Domain
            description: A domain with both old and new fields.
            version: 1
            protocols_dir: old-protocols
            content:
              protocols: new-protocols
        """))
        pack = _parse_domain_yaml(domain_dir)
        assert pack.content_dirs == {"protocols": "new-protocols"}


# ─── Content health check tests ───────────────────────────────────────────


class TestContentHealthCheck:
    def test_healthy_domain_returns_no_errors(self, tmp_path: Path) -> None:
        domain_dir = tmp_path / "healthy"
        domain_dir.mkdir()
        (domain_dir / "protocols").mkdir()
        (domain_dir / "errors").mkdir()
        pack = DomainPack(
            name="healthy",
            display_name="Healthy",
            description="Healthy domain",
            version=1,
            pack_path=domain_dir,
            content_dirs={"protocols": "protocols", "errors": "errors"},
        )
        ctx = DomainContext(pack)
        errors = check_content_health(ctx)
        assert errors == []

    def test_missing_content_dir_returns_error(self, tmp_path: Path) -> None:
        domain_dir = tmp_path / "unhealthy"
        domain_dir.mkdir()
        # Only create protocols, not errors
        (domain_dir / "protocols").mkdir()
        pack = DomainPack(
            name="unhealthy",
            display_name="Unhealthy",
            description="Unhealthy domain",
            version=1,
            pack_path=domain_dir,
            content_dirs={"protocols": "protocols", "errors": "errors"},
        )
        ctx = DomainContext(pack)
        errors = check_content_health(ctx)
        assert len(errors) == 1
        assert errors[0].content_type == "errors"
        assert errors[0].expected_path == domain_dir / "errors"

    def test_empty_content_dirs_is_healthy(self, tmp_path: Path) -> None:
        domain_dir = tmp_path / "minimal"
        domain_dir.mkdir()
        pack = DomainPack(
            name="minimal",
            display_name="Minimal",
            description="No content declared",
            version=1,
            pack_path=domain_dir,
        )
        ctx = DomainContext(pack)
        errors = check_content_health(ctx)
        assert errors == []

    def test_backward_compat_properties_without_content_dirs(self, tmp_path: Path) -> None:
        """When no content_dirs are declared, backward-compat properties fall back."""
        domain_dir = tmp_path / "no-content"
        domain_dir.mkdir()
        pack = DomainPack(
            name="no-content",
            display_name="No Content",
            description="No content dirs",
            version=1,
            pack_path=domain_dir,
        )
        ctx = DomainContext(pack)
        # Fallback paths should still resolve (even if dirs don't exist)
        assert ctx.protocols_dir == domain_dir / "protocols"
        assert ctx.errors_dir == domain_dir / "errors"
        assert ctx.subfields_dir == domain_dir / "subfields"
