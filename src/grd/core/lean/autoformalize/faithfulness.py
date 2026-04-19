"""Stage 5: faithfulness gate.

Per AUTOFORMALIZATION.md §8.2: back-translate the Lean statement to English
with a second LLM call, then compare the paraphrase against the original
informal claim. High similarity means the Lean statement preserves the
claim's meaning; low similarity means convention drift / quantifier swap /
missing hypothesis — silent failures that compilation can't catch.

The published SOTA uses SBERT (sentence-transformers) for similarity. We
lazily import it and fall back to a deterministic token-Jaccard similarity
when the package isn't installed. The Jaccard fallback:

* keeps CI green without a 300MB embedding-model download,
* is itself a useful signal (per [Paraphrase-robustness eval, 2025] simple
  lexical overlap flags egregious drift even if it misses subtle cases),
* behaves deterministically so tests can pin similarity values.

Users who want the real SBERT number install the ``autoformalize`` optional
extra — the signature is identical.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from grd.core.lean.autoformalize.llm import build_back_translation_messages

if TYPE_CHECKING:
    from grd.core.lean.autoformalize.llm import LLMBackend

logger = logging.getLogger(__name__)

__all__ = [
    "FaithfulnessReport",
    "SemanticDiff",
    "assess_faithfulness",
    "compute_semantic_diff",
    "cosine_sbert_similarity",
    "jaccard_similarity",
]


_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]+")
_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "of",
        "for",
        "and",
        "or",
        "is",
        "are",
        "be",
        "to",
        "in",
        "on",
        "at",
        "by",
        "from",
        "with",
        "that",
        "this",
        "it",
        "as",
        "we",
        "if",
        "then",
        "let",
        "any",
        "some",
        "all",
    }
)


@dataclass(frozen=True)
class SemanticDiff:
    """Structured diff between an informal claim and its back-translation.

    Replaces the opaque scalar-only similarity signal with a breakdown of
    *what* diverged, per AUTOFORMALIZATION.md §8.4: "surface the specific
    ambiguity (e.g., quantifier-order uncertain between candidates A/B)".

    All list fields are populated from token-level analysis (cheap, always
    available) rather than LLM calls (expensive, optional). The categories
    are not mutually exclusive — a token can appear in both
    ``changed_quantifiers`` and ``only_in_claim``.
    """

    similarity: float
    changed_quantifiers: list[str] = field(default_factory=list)
    changed_domains: list[str] = field(default_factory=list)
    missing_hypotheses: list[str] = field(default_factory=list)
    changed_convention_terms: list[str] = field(default_factory=list)
    only_in_claim: list[str] = field(default_factory=list)
    only_in_translation: list[str] = field(default_factory=list)


# ─── Token-level semantic categories ──────────────────────────────────────
# These pattern sets map tokens to semantic categories so the diff can say
# "quantifier changed" rather than just "token missing". Kept intentionally
# small — false negatives are fine (the raw only_in_claim/only_in_translation
# fields catch everything); false positives are worse.

_QUANTIFIER_TOKENS = frozenset({
    "forall", "exists", "every", "each", "some", "any", "no",
    "unique", "infinitely", "finitely", "countably", "uncountably",
    "bounded", "unbounded", "almost",
})

_DOMAIN_TOKENS = frozenset({
    "real", "reals", "complex", "integer", "integers", "natural", "naturals",
    "rational", "rationals", "positive", "negative", "nonnegative",
    "nonzero", "finite", "infinite", "compact", "open", "closed",
    "continuous", "differentiable", "measurable", "integrable",
    "hilbert", "banach", "metric", "topological", "manifold",
})

_CONVENTION_TOKENS = frozenset({
    "metric", "signature", "mostly", "minus", "plus",
    "natural", "units", "planck", "hbar",
    "covariant", "contravariant", "einstein", "summation",
    "diag", "minkowski", "lorentz", "euclidean",
})


def compute_semantic_diff(
    claim: str,
    back_translation: str,
    similarity: float,
) -> SemanticDiff:
    """Compute a structured diff from token-level analysis.

    Classifies tokens unique to either side into semantic categories
    (quantifiers, domains, conventions) so the escalation message can
    say *what* changed, not just *how much*.
    """
    claim_tokens = set(_tokenize(claim))
    trans_tokens = set(_tokenize(back_translation))

    only_claim = sorted(claim_tokens - trans_tokens)
    only_trans = sorted(trans_tokens - claim_tokens)

    all_diff = set(only_claim) | set(only_trans)

    return SemanticDiff(
        similarity=similarity,
        changed_quantifiers=sorted(all_diff & _QUANTIFIER_TOKENS),
        changed_domains=sorted(all_diff & _DOMAIN_TOKENS),
        missing_hypotheses=[t for t in only_claim if t not in _QUANTIFIER_TOKENS | _DOMAIN_TOKENS | _CONVENTION_TOKENS],
        changed_convention_terms=sorted(all_diff & _CONVENTION_TOKENS),
        only_in_claim=only_claim,
        only_in_translation=only_trans,
    )


@dataclass(frozen=True)
class FaithfulnessReport:
    """Similarity + metadata for one successful candidate.

    ``backend`` is either ``"sbert"`` or ``"jaccard"`` so the decision layer
    can weight them differently in the future (currently both feed the same
    thresholds — the MVP keeps the comparison single-signal so behavior is
    predictable).
    """

    similarity: float
    back_translation: str
    backend: str
    semantic_diff: SemanticDiff | None = None
    notes: str = ""
    tokens_claim: tuple[str, ...] = field(default_factory=tuple)
    tokens_translation: tuple[str, ...] = field(default_factory=tuple)


def assess_faithfulness(
    *,
    claim: str,
    lean_source: str,
    llm: LLMBackend,
    sbert_model: object | None = None,
) -> FaithfulnessReport:
    """Back-translate ``lean_source`` and compare to ``claim``.

    ``sbert_model`` is an optional pre-loaded sentence-transformers model —
    passing one bypasses the lazy-import path and is the recommended way to
    avoid paying the load cost once per call in long batches.
    """
    system, messages = build_back_translation_messages(lean_source=lean_source)
    back = llm.complete(system=system, messages=messages, temperature=0.0).strip()
    back = _strip_surrounding_quotes(back)

    sim, backend, notes = _similarity(claim, back, sbert_model=sbert_model)
    diff = compute_semantic_diff(claim, back, similarity=sim)
    return FaithfulnessReport(
        similarity=sim,
        back_translation=back,
        backend=backend,
        semantic_diff=diff,
        notes=notes,
        tokens_claim=tuple(_tokenize(claim)),
        tokens_translation=tuple(_tokenize(back)),
    )


def jaccard_similarity(text_a: str, text_b: str) -> float:
    """Stopword-filtered token Jaccard; 1.0 on identical content, 0.0 on disjoint.

    Exposed separately so the decision layer can recompute on arbitrary text
    pairs (e.g., comparing two back-translations for the cluster-consensus
    path). Empty-vs-empty is conventionally 0.0 — we never want "there is no
    signal" to read as "perfect match".
    """
    a = set(_tokenize(text_a))
    b = set(_tokenize(text_b))
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def cosine_sbert_similarity(text_a: str, text_b: str, model: object) -> float:
    """Compute cosine similarity via a pre-loaded sentence-transformers model.

    ``model`` must support ``.encode([...])`` returning a numpy array. We
    import numpy lazily so this module stays importable without it.
    """
    import numpy as np  # noqa: PLC0415  (lazy — only the SBERT path needs numpy)

    encoded = model.encode([text_a, text_b])  # type: ignore[attr-defined]
    a, b = np.asarray(encoded[0]), np.asarray(encoded[1])
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _similarity(claim: str, back_translation: str, *, sbert_model: object | None) -> tuple[float, str, str]:
    if sbert_model is not None:
        try:
            sim = cosine_sbert_similarity(claim, back_translation, sbert_model)
            return sim, "sbert", "sbert cosine on provided model"
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("SBERT scoring failed, falling back to Jaccard: %s", exc)
    return jaccard_similarity(claim, back_translation), "jaccard", "stopword-filtered token Jaccard"


def _tokenize(text: str) -> list[str]:
    return [tok.lower() for tok in _TOKEN_RE.findall(text) if tok.lower() not in _STOPWORDS]


def _strip_surrounding_quotes(text: str) -> str:
    """Handle models that wrap their single-sentence answer in quotes."""
    t = text.strip()
    if len(t) >= 2 and t[0] == t[-1] and t[0] in {'"', "'"}:
        return t[1:-1].strip()
    return t
