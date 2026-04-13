"""Stage 3: candidate generation.

Generates N Lean 4 theorem candidates for one informal claim using the
configured LLM backend. Per AUTOFORMALIZATION.md §8.2:

- N = 4 for the MVP (pro pipeline uses N=16 with cross-model consensus),
- Claude Sonnet 4.5 with DRAFT-SKETCH-PROVE framing,
- grounded context (phase text + conventions + Mathlib4 name sample),
- Lean-4-only reminder in the system prompt.

Returned candidates are *source text only* — compilation and repair happen in
``repair.py``. Extracting the Lean block from the LLM's fenced output is
deliberately liberal: we accept plain text when no fence is present, so
back-translation-style free-form responses don't silently drop candidates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from grd.core.lean.autoformalize.config import AutoformalizeConfig
from grd.core.lean.autoformalize.llm import build_candidate_messages

if TYPE_CHECKING:
    from grd.core.lean.autoformalize.blueprint import BlueprintContext
    from grd.core.lean.autoformalize.index import NameIndex
    from grd.core.lean.autoformalize.llm import LLMBackend

__all__ = [
    "Candidate",
    "extract_lean_block",
    "generate_candidates",
]


_FENCE_RE = re.compile(
    r"```(?:lean|lean4)?\s*\n(?P<body>.*?)```",
    re.DOTALL | re.IGNORECASE,
)


@dataclass(frozen=True)
class Candidate:
    """One generated candidate statement.

    ``raw`` is the full model response; ``source`` is the extracted Lean code
    block. They can differ when the model emits commentary around the fence.
    The pipeline uses ``source`` for compile attempts and ``raw`` only for
    debugging / JSON emission.
    """

    index: int
    source: str
    raw: str
    temperature: float


def extract_lean_block(text: str) -> str:
    """Pull the Lean 4 source out of a possibly-fenced LLM response.

    If a fenced ``` ```lean ... ``` ``` block is present, return its body. If
    not, return the input stripped. This keeps tests simple — they can hand
    back plain Lean without fencing — while still handling well-formed model
    output gracefully.
    """
    match = _FENCE_RE.search(text)
    if match:
        return match.group("body").strip()
    return text.strip()


def generate_candidates(
    *,
    blueprint: BlueprintContext,
    index: NameIndex,
    llm: LLMBackend,
    config: AutoformalizeConfig,
    temperature_schedule: list[float] | None = None,
) -> list[Candidate]:
    """Generate ``config.num_candidates`` Lean candidates for the claim.

    Each candidate is drawn with a distinct temperature so the samples aren't
    all identical — this is the cheap ensemble dimension that still gives the
    faithfulness gate something to cluster over. The default schedule cycles
    through 0.3, 0.7, 1.0, 0.5 so temperature-0 regressions on fixed seeds
    don't wipe out diversity.
    """
    schedule = list(temperature_schedule) if temperature_schedule else _default_schedule(config.num_candidates)
    index_sample = index.sample(60)
    system, base_messages = build_candidate_messages(
        claim=blueprint.claim,
        conventions=blueprint.conventions,
        index_sample=index_sample,
        index_total=index.size,
        physics=blueprint.physics,
    )

    out: list[Candidate] = []
    for i in range(config.num_candidates):
        temp = schedule[i % len(schedule)]
        raw = llm.complete(system=system, messages=list(base_messages), temperature=temp)
        out.append(
            Candidate(
                index=i,
                source=extract_lean_block(raw),
                raw=raw,
                temperature=temp,
            )
        )
    return out


def _default_schedule(n: int) -> list[float]:
    """Cycle through low/mid/high temperatures to diversify without manual tuning."""
    base = [0.3, 0.7, 1.0, 0.5]
    if n <= len(base):
        return base[:n]
    # For larger N (pro pipeline), keep cycling — still deterministic.
    return [base[i % len(base)] for i in range(n)]
