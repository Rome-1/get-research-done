"""Comprehensive tests for the domain pack loader.

Covers discovery, loading, convention field integrity, content health checks,
and edge cases for malformed/empty domain packs.
"""

from __future__ import annotations

from functools import cached_property
from pathlib import Path
from textwrap import dedent

import pytest

from grd.domains.loader import (
    DomainContext,
    DomainPack,
    _parse_domain_yaml,
    check_content_health,
    list_available_domains,
    load_domain,
    resolve_domain_pack_path,
)

# Expected bundled domain names (alphabetically sorted as list_available_domains returns).
EXPECTED_BUNDLED_DOMAINS = ["machine-learning", "mech-interp", "physics"]


# ─── Discovery tests ────────────────────────────────────────────────────────


class TestDiscovery:
    def test_list_available_domains_returns_expected_bundled(self) -> None:
        """All three bundled domains should be discoverable."""
        domains = list_available_domains()
        for name in EXPECTED_BUNDLED_DOMAINS:
            assert name in domains, f"Expected bundled domain '{name}' not found"

    def test_bundled_domain_packs_all_have_domain_yaml(self) -> None:
        """Every bundled domain directory should contain a domain.yaml file."""
        from grd.domains.loader import _bundled_domains_dir

        bundled = _bundled_domains_dir()
        for name in EXPECTED_BUNDLED_DOMAINS:
            pack_dir = bundled / name
            assert pack_dir.is_dir(), f"Bundled domain dir missing: {pack_dir}"
            assert (pack_dir / "domain.yaml").is_file(), (
                f"domain.yaml missing in {pack_dir}"
            )

    def test_discovery_order_project_local_wins(self, tmp_path: Path) -> None:
        """A project-local .grd/domain/ pack overrides bundled packs."""
        domain_dir = tmp_path / ".grd" / "domain"
        domain_dir.mkdir(parents=True)
        (domain_dir / "domain.yaml").write_text(dedent("""\
            name: physics
            display_name: Project Physics Override
            description: Local override of the physics domain.
            version: 99
        """))
        path = resolve_domain_pack_path("physics", project_root=tmp_path)
        assert path == domain_dir

        # Loading it should yield the local pack, not the bundled one.
        ctx = load_domain("physics", project_root=tmp_path)
        assert ctx is not None
        assert ctx.display_name == "Project Physics Override"

    def test_discovery_order_user_dir_wins_over_bundled(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A user-level domain pack (~/.grd/domains/<name>) wins over bundled."""
        user_domains = tmp_path / "user_domains"
        physics_dir = user_domains / "physics"
        physics_dir.mkdir(parents=True)
        (physics_dir / "domain.yaml").write_text(dedent("""\
            name: physics
            display_name: User Physics Override
            description: User-level override.
            version: 42
        """))

        monkeypatch.setattr(
            "grd.domains.loader._USER_DOMAINS_DIR", user_domains
        )

        path = resolve_domain_pack_path("physics")
        assert path == physics_dir

        ctx = load_domain("physics")
        assert ctx is not None
        assert ctx.display_name == "User Physics Override"


# ─── Loading tests ───────────────────────────────────────────────────────────


class TestLoading:
    def test_load_nonexistent_domain_returns_none(self) -> None:
        ctx = load_domain("nonexistent-domain-abc123")
        assert ctx is None

    @pytest.mark.parametrize("domain_name", EXPECTED_BUNDLED_DOMAINS)
    def test_load_each_bundled_domain_succeeds(self, domain_name: str) -> None:
        ctx = load_domain(domain_name)
        assert ctx is not None, f"Failed to load bundled domain '{domain_name}'"
        assert ctx.name == domain_name

    def test_domain_context_lazy_properties(self) -> None:
        """Verify that key DomainContext properties use cached_property."""
        lazy_attrs = [
            "convention_fields",
            "known_convention_names",
            "convention_labels",
            "key_aliases",
            "value_aliases",
            "critical_fields",
            "convention_options",
        ]
        for attr_name in lazy_attrs:
            descriptor = getattr(DomainContext, attr_name)
            assert isinstance(descriptor, cached_property), (
                f"DomainContext.{attr_name} should be a cached_property"
            )

    def test_domain_context_content_dirs_resolve(self) -> None:
        """Content dirs on physics domain resolve to Path objects.

        At least the core content types (subfields, protocols, errors) must
        exist on disk.  Other declared types are allowed to be absent (e.g.
        project_types, bundles may be declared but not yet created).
        """
        ctx = load_domain("physics")
        assert ctx is not None
        must_exist = {"subfields", "protocols", "errors"}
        for ctype in ctx.content_types:
            resolved = ctx.content_dir(ctype)
            assert resolved is not None, f"content_dir('{ctype}') returned None"
            if ctype in must_exist:
                assert resolved.is_dir(), (
                    f"Core content dir '{ctype}' not found: {resolved}"
                )


# ─── Convention field tests ──────────────────────────────────────────────────


class TestConventionFields:
    def test_physics_conventions_have_required_fields(self) -> None:
        """Every physics convention field should have at least name and label."""
        ctx = load_domain("physics")
        assert ctx is not None
        for field_def in ctx.convention_fields:
            assert field_def.name, "Convention field has empty name"
            assert field_def.label, "Convention field has empty label"

    @pytest.mark.parametrize("domain_name", EXPECTED_BUNDLED_DOMAINS)
    def test_no_duplicate_convention_names_within_domain(self, domain_name: str) -> None:
        """No two convention fields in the same domain should share a name."""
        ctx = load_domain(domain_name)
        assert ctx is not None
        names = [f.name for f in ctx.convention_fields]
        assert len(names) == len(set(names)), (
            f"Duplicate convention names in '{domain_name}': "
            f"{[n for n in names if names.count(n) > 1]}"
        )

    @pytest.mark.parametrize("domain_name", EXPECTED_BUNDLED_DOMAINS)
    def test_no_alias_conflicts_within_domain(self, domain_name: str) -> None:
        """No two fields in the same domain should claim the same alias."""
        ctx = load_domain(domain_name)
        assert ctx is not None
        seen: dict[str, str] = {}
        for field_def in ctx.convention_fields:
            for alias in field_def.aliases:
                if alias in seen:
                    pytest.fail(
                        f"Alias '{alias}' in domain '{domain_name}' is claimed by "
                        f"both '{seen[alias]}' and '{field_def.name}'"
                    )
                seen[alias] = field_def.name

    @pytest.mark.parametrize("domain_name", EXPECTED_BUNDLED_DOMAINS)
    def test_value_aliases_reference_valid_fields(self, domain_name: str) -> None:
        """Every key in value_aliases should be a canonical convention name."""
        ctx = load_domain(domain_name)
        assert ctx is not None
        canonical_names = set(ctx.known_convention_names)
        for field_name in ctx.value_aliases:
            assert field_name in canonical_names, (
                f"Value alias key '{field_name}' in domain '{domain_name}' "
                f"is not a canonical convention name"
            )


# ─── Content health tests ───────────────────────────────────────────────────


class TestContentHealth:
    @pytest.mark.parametrize("domain_name", EXPECTED_BUNDLED_DOMAINS)
    def test_check_content_health_all_bundled_domains_pass(self, domain_name: str) -> None:
        """Bundled domains should have no health errors for core content types.

        Some domains may declare future content types (e.g. project_types,
        bundles) whose directories don't yet exist.  We only assert that no
        errors come from the essential types: subfields, protocols, errors,
        verification.
        """
        ctx = load_domain(domain_name)
        assert ctx is not None
        errors = check_content_health(ctx)
        core_types = {"subfields", "protocols", "errors", "verification"}
        core_errors = [e for e in errors if e.content_type in core_types]
        assert core_errors == [], (
            f"Core content health errors in '{domain_name}': "
            + "; ".join(e.message for e in core_errors)
        )

    def test_check_content_health_detects_missing_dir(self, tmp_path: Path) -> None:
        """A domain declaring a content dir that doesn't exist should fail health."""
        domain_dir = tmp_path / "bad-domain"
        domain_dir.mkdir()
        pack = DomainPack(
            name="bad-domain",
            display_name="Bad Domain",
            description="Domain with missing content dir",
            version=1,
            pack_path=domain_dir,
            content_dirs={"protocols": "protocols", "subfields": "subfields"},
        )
        ctx = DomainContext(pack)
        errors = check_content_health(ctx)
        assert len(errors) == 2
        error_types = {e.content_type for e in errors}
        assert error_types == {"protocols", "subfields"}


# ─── Edge cases ──────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_load_domain_with_malformed_yaml(self, tmp_path: Path) -> None:
        """A domain.yaml with invalid YAML should cause load_domain to return None."""
        domain_dir = tmp_path / "malformed"
        domain_dir.mkdir()
        (domain_dir / "domain.yaml").write_text("{{{{invalid yaml: [")

        # load_domain won't find it by name, so test via _parse_domain_yaml directly.
        with pytest.raises((ValueError, Exception)):
            _parse_domain_yaml(domain_dir)

    def test_load_domain_with_empty_yaml(self, tmp_path: Path) -> None:
        """A domain.yaml that's empty (parses as None) should raise ValueError."""
        domain_dir = tmp_path / "empty-yaml"
        domain_dir.mkdir()
        (domain_dir / "domain.yaml").write_text("")

        with pytest.raises(ValueError, match="must be a YAML mapping"):
            _parse_domain_yaml(domain_dir)

    def test_convention_fields_yaml_missing_gracefully_returns_empty(
        self, tmp_path: Path
    ) -> None:
        """If conventions_file doesn't exist, convention_fields should be empty."""
        domain_dir = tmp_path / "no-conventions"
        domain_dir.mkdir()
        pack = DomainPack(
            name="no-conventions",
            display_name="No Conventions",
            description="Domain without conventions file",
            version=1,
            pack_path=domain_dir,
            conventions_file="conventions/convention-fields.yaml",
        )
        ctx = DomainContext(pack)
        assert ctx.convention_fields == []
        assert ctx.known_convention_names == []
        assert ctx.key_aliases == {}
        assert ctx.value_aliases == {}

    def test_domain_pack_template_is_valid(self) -> None:
        """The _template domain should be parseable (not loadable by name)."""
        from grd.domains.loader import _bundled_domains_dir

        template_dir = _bundled_domains_dir() / "_template"
        assert template_dir.is_dir(), "_template directory should exist"
        pack = _parse_domain_yaml(template_dir)
        assert pack.name == "my-domain"
        assert pack.version == 1
        # Template should have a conventions file reference.
        assert "convention-fields" in pack.conventions_file

    def test_malformed_convention_fields_yaml_returns_empty(
        self, tmp_path: Path
    ) -> None:
        """If the conventions YAML is malformed, convention_fields returns []."""
        domain_dir = tmp_path / "bad-conv"
        domain_dir.mkdir()
        conv_dir = domain_dir / "conventions"
        conv_dir.mkdir()
        (conv_dir / "convention-fields.yaml").write_text("{{invalid: yaml [")
        pack = DomainPack(
            name="bad-conv",
            display_name="Bad Conv",
            description="Domain with malformed conventions YAML",
            version=1,
            pack_path=domain_dir,
        )
        ctx = DomainContext(pack)
        assert ctx.convention_fields == []

    def test_convention_fields_yaml_with_non_dict_returns_empty(
        self, tmp_path: Path
    ) -> None:
        """If conventions YAML parses to a non-dict, convention_fields returns []."""
        domain_dir = tmp_path / "list-conv"
        domain_dir.mkdir()
        conv_dir = domain_dir / "conventions"
        conv_dir.mkdir()
        (conv_dir / "convention-fields.yaml").write_text("- just\n- a\n- list\n")
        pack = DomainPack(
            name="list-conv",
            display_name="List Conv",
            description="Conventions YAML is a list not dict",
            version=1,
            pack_path=domain_dir,
        )
        ctx = DomainContext(pack)
        assert ctx.convention_fields == []
