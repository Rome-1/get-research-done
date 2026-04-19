"""Tests for ``grd.core.lean.autoformalize.faithfulness``.

Covers the Jaccard primitive (stopword handling, symmetry, empty cases), the
back-translation flow driven by a MockLLM, and the SBERT path via a stubbed
model so we don't pull 300MB of embeddings into CI.
"""

from __future__ import annotations

import math
from importlib.util import find_spec

import pytest

from grd.core.lean.autoformalize.faithfulness import (
    assess_faithfulness,
    compute_semantic_diff,
    cosine_sbert_similarity,
    jaccard_similarity,
)
from grd.core.lean.autoformalize.llm import MockLLM

# SBERT path requires numpy — skip those tests gracefully when numpy isn't
# installed (CI doesn't pull the ``autoformalize`` extra by default).
_HAS_NUMPY = find_spec("numpy") is not None
_skip_without_numpy = pytest.mark.skipif(
    not _HAS_NUMPY,
    reason="numpy not installed; SBERT path only runs with the 'autoformalize' extra",
)


# ─── Jaccard ───────────────────────────────────────────────────────────────


def test_jaccard_identical_text_is_one() -> None:
    assert jaccard_similarity("pi is irrational", "pi is irrational") == 1.0


def test_jaccard_disjoint_content_is_zero() -> None:
    assert jaccard_similarity("pi irrational", "Goldbach primes") == 0.0


def test_jaccard_is_symmetric() -> None:
    a = "every even natural number is the sum of two primes"
    b = "primes sum to every even natural number"
    assert jaccard_similarity(a, b) == jaccard_similarity(b, a)


def test_jaccard_stopwords_dont_inflate_score() -> None:
    """Stopwords ('the', 'is', 'of') should not count as shared content."""
    a = "the claim is trivial"
    b = "the other thing is also trivial"
    # Only "trivial" should count as shared content.
    sim = jaccard_similarity(a, b)
    # content tokens: {trivial, claim} ∩ {trivial, other, thing, also} = {trivial}
    # union size is 5 → 1/5 = 0.2
    assert sim == 0.2


def test_jaccard_empty_vs_nonempty_is_zero() -> None:
    assert jaccard_similarity("", "prime") == 0.0
    assert jaccard_similarity("prime", "") == 0.0
    # Purely stopwords → no content tokens → treated as empty.
    assert jaccard_similarity("the is of", "prime") == 0.0


# ─── SBERT (stubbed model) ─────────────────────────────────────────────────


class _FakeSbertModel:
    """Stub that returns a fixed encoding per input — no numpy-embedding dep."""

    def __init__(self, vectors: dict[str, list[float]]) -> None:
        self._vectors = vectors

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [self._vectors[t] for t in texts]


@_skip_without_numpy
def test_cosine_sbert_parallel_vectors_is_one() -> None:
    model = _FakeSbertModel({"a": [1.0, 0.0], "b": [2.0, 0.0]})
    assert math.isclose(cosine_sbert_similarity("a", "b", model), 1.0, abs_tol=1e-9)


@_skip_without_numpy
def test_cosine_sbert_orthogonal_vectors_is_zero() -> None:
    model = _FakeSbertModel({"a": [1.0, 0.0], "b": [0.0, 1.0]})
    assert math.isclose(cosine_sbert_similarity("a", "b", model), 0.0, abs_tol=1e-9)


@_skip_without_numpy
def test_cosine_sbert_zero_vector_returns_zero() -> None:
    model = _FakeSbertModel({"a": [0.0, 0.0], "b": [1.0, 1.0]})
    # denom=0 path — defensive, don't divide by zero.
    assert cosine_sbert_similarity("a", "b", model) == 0.0


# ─── assess_faithfulness flow ──────────────────────────────────────────────


def test_assess_back_translates_then_scores_with_jaccard() -> None:
    llm = MockLLM(responses=["pi is irrational"])
    report = assess_faithfulness(
        claim="pi is irrational",
        lean_source="theorem foo : Irrational Real.pi := sorry",
        llm=llm,
    )
    assert report.backend == "jaccard"
    assert report.back_translation == "pi is irrational"
    assert report.similarity == 1.0
    # Sanity: the tokens captured on the report exclude stopwords.
    assert "is" not in report.tokens_claim
    assert "pi" in report.tokens_claim


def test_assess_strips_surrounding_quotes_from_llm_output() -> None:
    llm = MockLLM(responses=['"pi is irrational"'])
    report = assess_faithfulness(
        claim="pi is irrational",
        lean_source="stuff",
        llm=llm,
    )
    # Quotes should be stripped before similarity is computed.
    assert report.back_translation == "pi is irrational"
    assert report.similarity == 1.0


@_skip_without_numpy
def test_assess_uses_sbert_when_model_provided() -> None:
    llm = MockLLM(responses=["pi is irrational"])
    # Exact-string lookup since both encode() inputs here are the same text.
    model = _FakeSbertModel({"pi is irrational": [3.0, 4.0]})
    report = assess_faithfulness(
        claim="pi is irrational",
        lean_source="stuff",
        llm=llm,
        sbert_model=model,
    )
    assert report.backend == "sbert"
    # cosine of identical vectors is 1.
    assert math.isclose(report.similarity, 1.0, abs_tol=1e-9)


def test_assess_records_divergent_back_translation() -> None:
    """A wrong back-translation produces a low Jaccard score, not a crash."""
    llm = MockLLM(responses=["something entirely different about Goldbach"])
    report = assess_faithfulness(
        claim="pi is irrational",
        lean_source="theorem foo : Irrational Real.pi := sorry",
        llm=llm,
    )
    # No content overlap at all → 0.0.
    assert report.similarity == 0.0
    assert report.backend == "jaccard"


def test_assess_populates_semantic_diff() -> None:
    """assess_faithfulness must produce a SemanticDiff on the report."""
    llm = MockLLM(responses=["something entirely different about Goldbach"])
    report = assess_faithfulness(
        claim="pi is irrational",
        lean_source="theorem foo : Irrational Real.pi := sorry",
        llm=llm,
    )
    assert report.semantic_diff is not None
    assert report.semantic_diff.similarity == report.similarity
    # "pi" and "irrational" are in claim but not in "something entirely different about Goldbach"
    assert "pi" in report.semantic_diff.only_in_claim
    assert "irrational" in report.semantic_diff.only_in_claim


# ─── compute_semantic_diff ────────────────────────────────────────────────


def test_diff_identical_text_has_no_divergence() -> None:
    diff = compute_semantic_diff("pi is irrational", "pi is irrational", similarity=1.0)
    assert diff.similarity == 1.0
    assert diff.only_in_claim == []
    assert diff.only_in_translation == []
    assert diff.changed_quantifiers == []
    assert diff.changed_domains == []
    assert diff.missing_hypotheses == []
    assert diff.changed_convention_terms == []


def test_diff_detects_quantifier_change() -> None:
    diff = compute_semantic_diff(
        "forall real numbers the function is continuous",
        "exists real numbers the function is continuous",
        similarity=0.7,
    )
    # "forall" in claim only, "exists" in translation only — both quantifiers.
    assert "exists" in diff.changed_quantifiers
    assert "forall" in diff.changed_quantifiers


def test_diff_detects_domain_change() -> None:
    diff = compute_semantic_diff(
        "the function is continuous on the reals",
        "the function is continuous on the integers",
        similarity=0.6,
    )
    assert "reals" in diff.changed_domains
    assert "integers" in diff.changed_domains


def test_diff_detects_convention_terms() -> None:
    diff = compute_semantic_diff(
        "using the mostly minus metric signature",
        "using the mostly plus metric signature",
        similarity=0.7,
    )
    assert "minus" in diff.changed_convention_terms
    assert "plus" in diff.changed_convention_terms


def test_diff_missing_hypotheses_excludes_categorized_tokens() -> None:
    diff = compute_semantic_diff(
        "for every bounded continuous function on the reals",
        "for a function on a space",
        similarity=0.3,
    )
    # "bounded" is a quantifier-class token, "continuous" and "reals" are domain-class.
    # "every" is a quantifier. None of these should appear in missing_hypotheses.
    for tok in diff.missing_hypotheses:
        assert tok not in {"every", "bounded", "continuous", "reals"}


def test_diff_only_in_translation_captures_added_terms() -> None:
    diff = compute_semantic_diff(
        "pi is irrational",
        "pi is irrational and transcendental",
        similarity=0.6,
    )
    assert "transcendental" in diff.only_in_translation
    assert diff.only_in_claim == []
