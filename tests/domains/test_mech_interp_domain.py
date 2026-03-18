"""Tests for the mech-interp (mechanistic interpretability) domain pack.

Validates that the bundled mech-interp domain pack loads correctly and that
its convention fields work with the core conventions engine.
"""

from __future__ import annotations

import pytest

from grd.contracts import ConventionLock
from grd.core.conventions import (
    convention_check,
    convention_list,
    convention_set,
    normalize_key,
    normalize_value,
)
from grd.domains.loader import DomainContext, list_available_domains, load_domain


@pytest.fixture()
def mi_ctx() -> DomainContext:
    """Load the bundled mech-interp domain pack."""
    ctx = load_domain("mech-interp")
    assert ctx is not None, "Bundled mech-interp domain pack should always be available"
    return ctx


class TestMechInterpDomainContext:
    def test_domain_loads(self, mi_ctx: DomainContext) -> None:
        assert mi_ctx.name == "mech-interp"
        assert mi_ctx.display_name == "Mechanistic Interpretability"

    def test_listed_in_available_domains(self) -> None:
        domains = list_available_domains()
        assert "mech-interp" in domains

    def test_has_15_convention_fields(self, mi_ctx: DomainContext) -> None:
        assert len(mi_ctx.convention_fields) == 15

    def test_convention_field_names(self, mi_ctx: DomainContext) -> None:
        names = mi_ctx.known_convention_names
        expected = [
            "model_family",
            "activation_space",
            "patching_method",
            "attribution_method",
            "sae_architecture",
            "sae_normalization",
            "hook_point_convention",
            "layer_indexing",
            "logit_attribution_direction",
            "position_encoding",
            "attention_pattern_format",
            "feature_density_metric",
            "ablation_baseline",
            "circuit_completeness_criterion",
            "tokenizer",
        ]
        assert names == expected

    def test_key_aliases(self, mi_ctx: DomainContext) -> None:
        aliases = mi_ctx.key_aliases
        assert aliases["model"] == "model_family"
        assert aliases["basis"] == "activation_space"
        assert aliases["space"] == "activation_space"
        assert aliases["patching"] == "patching_method"
        assert aliases["attribution"] == "attribution_method"
        assert aliases["sae_type"] == "sae_architecture"
        assert aliases["hooks"] == "hook_point_convention"
        assert aliases["indexing"] == "layer_indexing"
        assert aliases["tok"] == "tokenizer"

    def test_value_aliases(self, mi_ctx: DomainContext) -> None:
        va = mi_ctx.value_aliases
        assert va["activation_space"]["residual"] == "residual-stream"
        assert va["sae_architecture"]["topk"] == "topk-sae"
        assert va["patching_method"]["zero_ablation"] == "zero-ablation"
        assert va["attribution_method"]["ig"] == "integrated-gradients"
        assert va["logit_attribution_direction"]["logit_diff"] == "logit-difference"
        assert va["layer_indexing"]["0-indexed"] == "zero-indexed"


class TestMechInterpConventionOps:
    def test_normalize_key(self, mi_ctx: DomainContext) -> None:
        assert normalize_key("model", domain_ctx=mi_ctx) == "model_family"
        assert normalize_key("basis", domain_ctx=mi_ctx) == "activation_space"
        assert normalize_key("patching", domain_ctx=mi_ctx) == "patching_method"

    def test_normalize_value(self, mi_ctx: DomainContext) -> None:
        assert normalize_value("activation_space", "residual", domain_ctx=mi_ctx) == "residual-stream"
        assert normalize_value("layer_indexing", "0-indexed", domain_ctx=mi_ctx) == "zero-indexed"
        assert normalize_value("sae_architecture", "topk", domain_ctx=mi_ctx) == "topk-sae"

    def test_convention_set_goes_to_custom(self, mi_ctx: DomainContext) -> None:
        """Mech-interp fields are not on ConventionLock model — they go to custom_conventions."""
        lock = ConventionLock()
        result = convention_set(lock, "model", "transformer", domain_ctx=mi_ctx)
        assert result.updated is True
        assert result.key == "model_family"
        assert lock.custom_conventions.get("model_family") == "transformer"

    def test_convention_set_with_value_alias(self, mi_ctx: DomainContext) -> None:
        lock = ConventionLock()
        result = convention_set(lock, "basis", "residual", domain_ctx=mi_ctx)
        assert result.updated is True
        assert lock.custom_conventions.get("activation_space") == "residual-stream"

    def test_convention_set_immutability(self, mi_ctx: DomainContext) -> None:
        lock = ConventionLock()
        convention_set(lock, "baseline", "zero", domain_ctx=mi_ctx)
        result = convention_set(lock, "baseline", "mean", domain_ctx=mi_ctx)
        assert result.updated is False
        assert result.reason == "convention_already_set"
        # Force overwrite works
        result = convention_set(lock, "baseline", "mean", domain_ctx=mi_ctx, force=True)
        assert result.updated is True

    def test_convention_list(self, mi_ctx: DomainContext) -> None:
        lock = ConventionLock()
        lock.custom_conventions["model_family"] = "transformer"
        lock.custom_conventions["activation_space"] = "residual-stream"
        result = convention_list(lock, domain_ctx=mi_ctx)
        assert result.canonical_total == 15
        assert result.set_count == 2

    def test_convention_check_missing_all(self, mi_ctx: DomainContext) -> None:
        lock = ConventionLock()
        result = convention_check(lock, domain_ctx=mi_ctx)
        assert result.total == 15
        assert result.missing_count == 15
        assert result.complete is False

    def test_convention_check_complete(self, mi_ctx: DomainContext) -> None:
        lock = ConventionLock()
        for name in mi_ctx.known_convention_names:
            lock.custom_conventions[name] = f"test-value-{name}"
        result = convention_check(lock, domain_ctx=mi_ctx)
        assert result.total == 15
        assert result.set_count == 15
        assert result.complete is True

    def test_physics_alias_does_not_resolve(self, mi_ctx: DomainContext) -> None:
        """Physics aliases should not work in mech-interp context."""
        assert normalize_key("gauge", domain_ctx=mi_ctx) == "gauge"  # not resolved
        assert normalize_key("units", domain_ctx=mi_ctx) == "units"  # not resolved
