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

    def test_has_14_convention_fields(self, mi_ctx: DomainContext) -> None:
        assert len(mi_ctx.convention_fields) == 14

    def test_convention_field_names(self, mi_ctx: DomainContext) -> None:
        names = mi_ctx.known_convention_names
        expected = [
            "model_family",
            "activation_site",
            "feature_method",
            "sae_architecture",
            "patching_method",
            "ablation_type",
            "tokenizer",
            "metric",
            "layer_indexing",
            "component_notation",
            "direction_convention",
            "dataset",
            "dtype",
            "library",
        ]
        assert names == expected

    def test_key_aliases(self, mi_ctx: DomainContext) -> None:
        aliases = mi_ctx.key_aliases
        assert aliases["model"] == "model_family"
        assert aliases["hook"] == "activation_site"
        assert aliases["hookpoint"] == "activation_site"
        assert aliases["features"] == "feature_method"
        assert aliases["patching"] == "patching_method"
        assert aliases["framework"] == "library"
        assert aliases["precision"] == "dtype"

    def test_value_aliases(self, mi_ctx: DomainContext) -> None:
        va = mi_ctx.value_aliases
        assert va["activation_site"]["residual_pre"] == "resid_pre"
        assert va["sae_architecture"]["topk"] == "top-k"
        assert va["patching_method"]["actpatch"] == "activation-patching"
        assert va["ablation_type"]["zero_ablation"] == "zero"
        assert va["metric"]["logit_diff"] == "logit-diff"
        assert va["dtype"]["bf16"] == "bfloat16"
        assert va["library"]["tl"] == "transformer-lens"


class TestMechInterpConventionOps:
    def test_normalize_key(self, mi_ctx: DomainContext) -> None:
        assert normalize_key("model", domain_ctx=mi_ctx) == "model_family"
        assert normalize_key("hook", domain_ctx=mi_ctx) == "activation_site"
        assert normalize_key("features", domain_ctx=mi_ctx) == "feature_method"

    def test_normalize_value(self, mi_ctx: DomainContext) -> None:
        assert normalize_value("activation_site", "residual", domain_ctx=mi_ctx) == "resid_post"
        assert normalize_value("dtype", "bf16", domain_ctx=mi_ctx) == "bfloat16"
        assert normalize_value("library", "tl", domain_ctx=mi_ctx) == "transformer-lens"

    def test_convention_set_goes_to_custom(self, mi_ctx: DomainContext) -> None:
        """Mech-interp fields are not on ConventionLock model — they go to custom_conventions."""
        lock = ConventionLock()
        result = convention_set(lock, "model", "gpt2-small", domain_ctx=mi_ctx)
        assert result.updated is True
        assert result.key == "model_family"
        assert lock.custom_conventions.get("model_family") == "gpt2-small"

    def test_convention_set_with_value_alias(self, mi_ctx: DomainContext) -> None:
        lock = ConventionLock()
        result = convention_set(lock, "hook", "residual", domain_ctx=mi_ctx)
        assert result.updated is True
        assert lock.custom_conventions.get("activation_site") == "resid_post"

    def test_convention_set_immutability(self, mi_ctx: DomainContext) -> None:
        lock = ConventionLock()
        convention_set(lock, "ablation", "zero", domain_ctx=mi_ctx)
        result = convention_set(lock, "ablation", "mean", domain_ctx=mi_ctx)
        assert result.updated is False
        assert result.reason == "convention_already_set"
        # Force overwrite works
        result = convention_set(lock, "ablation", "mean", domain_ctx=mi_ctx, force=True)
        assert result.updated is True

    def test_convention_list(self, mi_ctx: DomainContext) -> None:
        lock = ConventionLock()
        lock.custom_conventions["model_family"] = "gpt2-small"
        lock.custom_conventions["activation_site"] = "resid_pre"
        result = convention_list(lock, domain_ctx=mi_ctx)
        assert result.canonical_total == 14
        assert result.set_count == 2

    def test_convention_check_missing_all(self, mi_ctx: DomainContext) -> None:
        lock = ConventionLock()
        result = convention_check(lock, domain_ctx=mi_ctx)
        assert result.total == 14
        assert result.missing_count == 14
        assert result.complete is False

    def test_convention_check_complete(self, mi_ctx: DomainContext) -> None:
        lock = ConventionLock()
        for name in mi_ctx.known_convention_names:
            lock.custom_conventions[name] = f"test-value-{name}"
        result = convention_check(lock, domain_ctx=mi_ctx)
        assert result.total == 14
        assert result.set_count == 14
        assert result.complete is True

    def test_physics_alias_does_not_resolve(self, mi_ctx: DomainContext) -> None:
        """Physics aliases should not work in mech-interp context."""
        # "metric" alias is used by mech-interp for "metric" field, not "metric_signature"
        assert normalize_key("gauge", domain_ctx=mi_ctx) == "gauge"  # not resolved
        assert normalize_key("units", domain_ctx=mi_ctx) == "units"  # not resolved
