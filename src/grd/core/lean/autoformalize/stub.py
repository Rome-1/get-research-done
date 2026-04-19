"""``grd lean stub-claim`` — NL claim to skeleton Lean statement + retrieval hits.

The highest-leverage unmet need in the Lean ecosystem per UX-STUDY.md §3 P1-1:
Tao's "~1 hour per line" during PFR and ~300 Zulip msgs/week asking "Is there
code for X?" show that the gap between informal claim and formal statement is
the primary bottleneck.

``stub_claim`` runs stages 1-3 of the autoformalization pipeline (context
extraction, retrieval, candidate generation) but stops *before* compile-repair
and faithfulness. The output is a skeleton, not a verified statement:

- One Lean 4 ``theorem ... := sorry`` stub
- Ranked retrieval hits from the Mathlib4 / PhysLean name index
- Suggested import list (extracted from the skeleton)
- "What to try next" hints

This is intentionally cheaper than ``verify_claim`` — no compilation, no
back-translation, no LLM repair loop — so it can be used interactively as a
first step.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from grd.core.lean.autoformalize.blueprint import BlueprintContext, extract_blueprint_context
from grd.core.lean.autoformalize.candidates import extract_lean_block
from grd.core.lean.autoformalize.config import AutoformalizeConfig, load_autoformalize_config
from grd.core.lean.autoformalize.index import NameIndex, load_default_index
from grd.core.lean.autoformalize.llm import build_candidate_messages

if TYPE_CHECKING:
    from grd.core.lean.autoformalize.llm import LLMBackend

__all__ = [
    "StubClaimResult",
    "search_index",
    "stub_claim",
]


@dataclass(frozen=True)
class StubClaimResult:
    """Output of ``stub_claim`` — a skeleton plus retrieval context.

    ``skeleton`` is a Lean 4 ``theorem ... := sorry`` that may or may not
    typecheck. The user is expected to refine it — this is a starting point,
    not a verdict.
    """

    claim: str
    skeleton: str
    retrieval_hits: list[str] = field(default_factory=list)
    suggested_imports: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    index_source: str = ""
    notes: list[str] = field(default_factory=list)


def stub_claim(
    *,
    claim: str,
    project_root: Path,
    llm: LLMBackend,
    config: AutoformalizeConfig | None = None,
    index: NameIndex | None = None,
    phase: str | None = None,
    physics_override: bool | None = None,
    imports: list[str] | None = None,
) -> StubClaimResult:
    """Generate a skeleton Lean statement and retrieval context for *claim*.

    This is the lightweight entry point — stages 1-3 only, no compilation.
    """
    cfg = config or load_autoformalize_config(project_root)
    idx = index or load_default_index(project_root, cfg)
    blueprint = extract_blueprint_context(
        claim=claim,
        project_root=project_root,
        phase=phase,
        physics_override=physics_override,
    )

    notes: list[str] = []
    if idx.size == 0:
        notes.append(
            "name index is empty — retrieval hits unavailable; "
            "drop a newline-delimited identifier snapshot into "
            ".grd/mathlib4-names.txt to enable grounded retrieval"
        )

    # Generate ONE skeleton at temperature 0 for deterministic output.
    skeleton = _generate_skeleton(blueprint, idx, llm, cfg)

    # Find relevant Mathlib/PhysLean identifiers.
    retrieval_hits = search_index(claim, idx)

    # Extract import suggestions from the skeleton.
    suggested_imports = _extract_imports(skeleton)
    if imports:
        for imp in imports:
            if imp not in suggested_imports:
                suggested_imports.append(imp)

    # Compose "what to try next" hints.
    next_steps = _compose_next_steps(claim, skeleton, retrieval_hits, blueprint)

    return StubClaimResult(
        claim=claim,
        skeleton=skeleton,
        retrieval_hits=retrieval_hits,
        suggested_imports=suggested_imports,
        next_steps=next_steps,
        index_source=idx.source,
        notes=notes,
    )


def search_index(claim: str, index: NameIndex, *, max_results: int = 20) -> list[str]:
    """Find index entries relevant to *claim* by token overlap.

    Tokenizes the claim into content words, then scores each index name
    by how many claim tokens appear as substrings of the name (case-insensitive).
    Returns the top *max_results* names, sorted by score descending then
    alphabetically.
    """
    if index.size == 0:
        return []

    claim_tokens = _claim_tokens(claim)
    if not claim_tokens:
        return []

    scored: list[tuple[int, str]] = []
    for name in index.names:
        lower_name = name.lower()
        score = sum(1 for tok in claim_tokens if tok in lower_name)
        if score > 0:
            scored.append((score, name))

    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return [name for _, name in scored[:max_results]]


_CLAIM_STOP = frozenset({
    "the", "a", "an", "of", "for", "and", "or", "is", "are", "be",
    "to", "in", "on", "at", "by", "from", "with", "that", "this",
    "it", "as", "we", "if", "then", "let", "any", "some", "all",
    "every", "there", "has", "have", "which", "such",
})

_CLAIM_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]+")


def _claim_tokens(claim: str) -> list[str]:
    """Extract content tokens from an informal claim for index search."""
    return [
        tok.lower()
        for tok in _CLAIM_TOKEN_RE.findall(claim)
        if tok.lower() not in _CLAIM_STOP
    ]


def _generate_skeleton(
    blueprint: BlueprintContext,
    index: NameIndex,
    llm: LLMBackend,
    config: AutoformalizeConfig,
) -> str:
    """Generate one skeleton Lean statement via the LLM."""
    system, messages = build_candidate_messages(
        claim=blueprint.claim,
        conventions=blueprint.conventions,
        index_sample=index.sample(60),
        index_total=index.size,
        physics=blueprint.physics,
    )
    raw = llm.complete(system=system, messages=messages, temperature=0.0)
    return extract_lean_block(raw)


_IMPORT_RE = re.compile(r"^import\s+(\S+)", re.MULTILINE)
_OPEN_RE = re.compile(r"^open\s+(\S+)", re.MULTILINE)


def _extract_imports(skeleton: str) -> list[str]:
    """Pull import and open statements from the skeleton."""
    imports: list[str] = []
    seen: set[str] = set()
    for match in _IMPORT_RE.finditer(skeleton):
        mod = match.group(1)
        if mod not in seen:
            imports.append(mod)
            seen.add(mod)
    for match in _OPEN_RE.finditer(skeleton):
        mod = match.group(1)
        if mod not in seen:
            imports.append(mod)
            seen.add(mod)
    return imports


def _compose_next_steps(
    claim: str,
    skeleton: str,
    retrieval_hits: list[str],
    blueprint: BlueprintContext,
) -> list[str]:
    """Generate actionable "what to try next" hints."""
    steps: list[str] = []

    # Always suggest typechecking first.
    steps.append("Typecheck the skeleton: grd lean check --file <path>.lean")

    # If retrieval hits exist, suggest browsing them.
    if retrieval_hits:
        top = retrieval_hits[:3]
        steps.append(f"Review retrieval hits: {', '.join(top)}")

    # Suggest the prove command.
    steps.append("Attempt automated proof: grd lean prove \"<statement>\"")

    # If it's a physics claim, remind about conventions.
    if blueprint.physics:
        steps.append("Check convention alignment: grd lean env (physics project detected)")

    # Suggest the full verify-claim pipeline.
    steps.append("Run full verification: grd lean verify-claim \"<claim>\"")

    return steps
