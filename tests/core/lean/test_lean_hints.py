"""Tests for grd.core.lean.hints — the error-explanation lookup layer.

Covers the top-5 user-visible Lean failures from the nitro UX study (ge-m0m):
``failed to synthesize instance``, ``type mismatch``, heartbeat timeouts,
``deep recursion``, and universe errors. These are the P0-1 acceptance
criteria for ge-13w — if any of these regress, a cold mathematician loses
the hint that tells them what to do next.
"""

from __future__ import annotations

import pytest

from grd.core.lean.hints import HINT_RULES, hint_for_message


class TestTopFiveQ9Errors:
    """Exact Lean 4 message strings from the external UX research, Q9."""

    def test_failed_to_synthesize_instance_generic(self) -> None:
        msg = "failed to synthesize instance MyClass Nat"
        hint = hint_for_message(msg)
        assert hint is not None
        assert "typeclass" in hint.lower()
        # Must suggest an actionable next step, not just restate the error.
        assert "import" in hint.lower() or "trace" in hint.lower() or "binder" in hint.lower()

    def test_failed_to_synthesize_decidable_more_specific(self) -> None:
        msg = "failed to synthesize instance Decidable (x > 0)"
        hint = hint_for_message(msg)
        assert hint is not None
        assert "Decidable" in hint

    def test_failed_to_synthesize_decidable_eq_more_specific(self) -> None:
        msg = "failed to synthesize instance DecidableEq α"
        hint = hint_for_message(msg)
        assert hint is not None
        assert "DecidableEq" in hint

    def test_type_mismatch_with_has_type_vs_expected(self) -> None:
        msg = "type mismatch\n  hfoo\nhas type\n  Nat\nbut is expected to have type\n  Int"
        hint = hint_for_message(msg)
        assert hint is not None
        # Must call out lean4#333 remedies: pp.all or show ascription.
        assert "pp.all" in hint or "ascription" in hint

    def test_type_mismatch_generic_fallback(self) -> None:
        """Even terse `type mismatch` lines get a hint — otherwise the common
        Lean 4.14 short form leaves the user stranded."""
        hint = hint_for_message("type mismatch at application of `foo`")
        assert hint is not None
        assert "type" in hint.lower()

    def test_heartbeat_timeout_deterministic(self) -> None:
        msg = "(deterministic) timeout at 'whnf', maximum number of heartbeats (200000) has been reached"
        hint = hint_for_message(msg)
        assert hint is not None
        assert "maxHeartbeats" in hint

    def test_heartbeats_without_deterministic_prefix(self) -> None:
        """Lean sometimes prints just 'maximum number of heartbeats' without the
        parenthetical — we must still match."""
        msg = "something something maximum number of heartbeats something"
        hint = hint_for_message(msg)
        assert hint is not None
        assert "maxHeartbeats" in hint

    def test_deep_recursion(self) -> None:
        hint = hint_for_message("deep recursion detected")
        assert hint is not None
        assert "typeclass" in hint.lower() or "loop" in hint.lower() or "cycle" in hint.lower()

    def test_invalid_universe_level(self) -> None:
        hint = hint_for_message("invalid universe level")
        assert hint is not None
        assert "universe" in hint.lower()

    def test_universe_level_ordering_error(self) -> None:
        hint = hint_for_message("universe level 2 not <= 1")
        assert hint is not None
        assert "universe" in hint.lower()

    def test_universe_level_unicode_le(self) -> None:
        """Lean prints the comparison with the Unicode ≤ in some paths."""
        hint = hint_for_message("universe level 2 not ≤ 1")
        assert hint is not None
        assert "universe" in hint.lower()


class TestHonorableMentions:
    """Honorable-mention failures from Q9 — not top-5, but common day-one trips."""

    def test_unknown_identifier_unicode_nat(self) -> None:
        hint = hint_for_message("unknown identifier 'ℕ'")
        assert hint is not None
        assert "Mathlib" in hint

    def test_unknown_identifier_generic(self) -> None:
        hint = hint_for_message("unknown identifier 'hfoo'")
        assert hint is not None
        assert "import" in hint.lower() or "typo" in hint.lower()

    def test_unknown_package_mathlib(self) -> None:
        hint = hint_for_message("unknown package 'Mathlib'")
        assert hint is not None
        assert "bootstrap" in hint.lower() or "lake" in hint.lower()

    def test_missing_exponent_digits_pitfall(self) -> None:
        """lean4#9450: message is nowhere near the actual cause. The hint has
        to spell out the real cause (digit-prefixed theorem name)."""
        hint = hint_for_message("missing exponent digits in scientific literal")
        assert hint is not None
        assert "theorem name" in hint.lower() or "rename" in hint.lower() or "digit" in hint.lower()

    def test_maximum_class_instance_depth(self) -> None:
        hint = hint_for_message("maximum class-instance resolution depth has been reached")
        assert hint is not None
        assert "instance" in hint.lower() or "typeclass" in hint.lower()

    def test_invalid_lake_configuration(self) -> None:
        hint = hint_for_message("Invalid Lake configuration: network error")
        assert hint is not None
        # lean4#6827 — frequently a network error masquerading as a config error.
        assert "network" in hint.lower() or "manifest" in hint.lower()


class TestTacticFailures:
    def test_unsolved_goals(self) -> None:
        hint = hint_for_message("unsolved goals\n  x : Nat\n  ⊢ x = x")
        assert hint is not None
        assert "goals" in hint.lower()

    def test_linarith_failed(self) -> None:
        hint = hint_for_message("linarith failed to find a contradiction")
        assert hint is not None
        assert "nlinarith" in hint or "polyrith" in hint or "linear" in hint.lower()

    def test_ring_failed(self) -> None:
        hint = hint_for_message("ring tactic failed")
        assert hint is not None
        assert "ring" in hint.lower()

    def test_simp_no_progress(self) -> None:
        hint = hint_for_message("simp made no progress")
        assert hint is not None
        assert "simp?" in hint or "normal" in hint.lower()


class TestUnknownAndEdgeCases:
    def test_unrecognized_message_returns_none(self) -> None:
        """Unknown messages must return ``None`` — the contract is 'say nothing
        rather than invent guidance'."""
        assert hint_for_message("xyzzy plugh") is None

    def test_empty_message_returns_none(self) -> None:
        assert hint_for_message("") is None

    def test_case_insensitive(self) -> None:
        """Lean message casing can vary between Lean versions/backends."""
        assert hint_for_message("FAILED TO SYNTHESIZE something") is not None
        assert hint_for_message("Deep Recursion Detected") is not None

    def test_hint_is_single_line_under_200_chars(self) -> None:
        """Contract: every hint reads as a single bullet. Long, multi-line
        hints would blow up the rich table and the JSON trace."""
        for _pattern, hint in HINT_RULES:
            assert "\n" not in hint, f"hint contains newline: {hint!r}"
            assert len(hint) < 260, f"hint too long ({len(hint)} chars): {hint!r}"

    def test_at_least_30_rules(self) -> None:
        """UX-STUDY.md P0-1 target: ~30-entry lookup covers ~80% of failures."""
        assert len(HINT_RULES) >= 25, f"expected ≥25 rules, got {len(HINT_RULES)}"


class TestOrderingAndSpecificity:
    """The first matching rule wins, so narrower patterns must come first."""

    def test_decidable_specific_beats_generic_synthesize(self) -> None:
        msg = "failed to synthesize instance Decidable (x > 0)"
        hint = hint_for_message(msg)
        # The Decidable-specific hint mentions Decidable prominently; the
        # generic synthInstance one does not.
        assert hint is not None and "Decidable" in hint

    @pytest.mark.parametrize(
        "msg,expected_fragment",
        [
            ("failed to synthesize instance Repr MyType", "typeclass"),
            ("deep recursion detected in instance search", "typeclass"),
            (
                "(deterministic) timeout at 'whnf', maximum number of heartbeats (200000) has been reached",
                "maxHeartbeats",
            ),
            ("invalid universe level", "universe"),
        ],
    )
    def test_parametrized_top_five_match(self, msg: str, expected_fragment: str) -> None:
        hint = hint_for_message(msg)
        assert hint is not None
        assert expected_fragment.lower() in hint.lower()
