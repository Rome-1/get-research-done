"""Sledgehammer-style parallel tactic hammer for Lean 4 statements (ge-k8s).

Where :mod:`grd.core.lean.prove` walks a fixed ladder sequentially and returns
the first tactic that closes the goal, ``try-prove`` runs the hammer-class
tactics (``exact?``, ``apply?``, ``simp_all``, ``aesop``, ``hammer``) in
parallel and returns *every* kernel-checked candidate, ranked. This is the UX
lifted from Isabelle's Sledgehammer: one invocation, a clickable list of
snippets, and the "never ship an oracle" discipline — a candidate is only
surfaced if it actually type-checks (UX-STUDY.md §P2-1, external-research.md
§5, nitro feature #5, rust PR9).

Each candidate snippet is the raw tactic string (e.g. ``by exact?``). The
kernel-check is performed by composing the full Lean source via
:func:`grd.core.lean.prove.compose_attempt_source` and running
:func:`grd.core.lean.client.check` on it — identical to the ``prove`` path so
the two share error handling and goal-state extraction.

With ``--with-llm`` / ``with_llm=True`` the hammer additionally asks an
LLM for ``llmqed``-style candidate tactics (the research proposal from
nitro feature #5); each LLM-proposed tactic is kernel-checked like any other.
Without a configured ``llm`` backend, ``with_llm`` is a no-op.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from grd.core.lean.client import check as lean_check
from grd.core.lean.events import EventCallback, TacticAttempted
from grd.core.lean.protocol import LeanCheckResult
from grd.core.lean.prove import (
    _first_error_hint,
    _first_error_summary,
    _infer_initial_goal,
    compose_attempt_source,
)

if TYPE_CHECKING:
    from grd.core.lean.autoformalize.llm import LLMBackend

__all__ = [
    "DEFAULT_HAMMER_TACTICS",
    "TryProveCandidate",
    "TryProveResult",
    "try_prove_statement",
]


DEFAULT_HAMMER_TACTICS: tuple[str, ...] = (
    "exact?",
    "apply?",
    "simp_all",
    "aesop",
    "hammer",
)
"""Ordered hammer-class tactic candidates.

Ordering reflects both cost and specificity: ``exact?`` and ``apply?`` are
one-lemma suggestions (cheapest, most direct), ``simp_all`` is a
normalization pass, ``aesop`` is Mathlib's general-purpose closer, and
``hammer`` is the 2025 LeanHammer integration (arXiv 2506.07477, 33%
Mathlib coverage) which may not be installed — failed attempts are
collected as ``failures`` rather than aborting the run.
"""


_LLM_MAX_CANDIDATES = 8
"""Cap on LLM-proposed tactic candidates per run.

Keeps the parallel pool bounded and the Lean daemon load predictable.
"""


class TryProveCandidate(BaseModel):
    """One candidate tactic run in parallel against the statement."""

    model_config = ConfigDict(extra="forbid")

    tactic: str = Field(description="Raw tactic text, e.g. 'aesop' or 'simp [Nat.add_comm]'.")
    snippet: str = Field(description="Clickable one-line snippet: 'by <tactic>'.")
    source: str = Field(description="Full Lean source that was kernel-checked.")
    ok: bool
    elapsed_ms: int = 0
    rank: int | None = Field(
        default=None,
        description="Position in the ranked list (0 = best). ``None`` for failures.",
    )
    via_llm: bool = False
    error_summary: str | None = None
    hint: str | None = None
    goal_before: str | None = None
    goal_after: list[str] | None = None


class TryProveResult(BaseModel):
    """Aggregate outcome of a parallel hammer run."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    statement: str
    successes: list[TryProveCandidate] = Field(
        default_factory=list,
        description="Kernel-checked candidates, ranked best-first.",
    )
    failures: list[TryProveCandidate] = Field(
        default_factory=list,
        description="Candidates that failed to close the goal (for diagnostics).",
    )
    total_elapsed_ms: int = 0
    with_llm: bool = False
    max_candidates: int = 0


def try_prove_statement(
    statement: str,
    *,
    project_root: Path,
    tactics: Iterable[str] | None = None,
    imports: list[str] | None = None,
    max_candidates: int | None = None,
    timeout_s: float = 30.0,
    with_llm: bool = False,
    llm: LLMBackend | None = None,
    use_daemon: bool = True,
    auto_spawn: bool = True,
    max_workers: int | None = None,
    on_event: EventCallback = None,
) -> TryProveResult:
    """Run hammer tactics in parallel and return every kernel-checked candidate.

    ``tactics`` overrides the default ladder when provided. ``max_candidates``
    caps the size of the parallel pool *before* any LLM-proposed tactics are
    added — useful for smoke tests and budget-bounded agent invocations.

    ``with_llm`` enables the ``llmqed``-style path: when an ``llm`` backend is
    available the hammer asks it for up to :data:`_LLM_MAX_CANDIDATES` extra
    tactic strings, each kernel-checked alongside the built-in ladder. The
    flag is a no-op when ``llm`` is ``None``.

    ``on_event`` receives a :class:`TacticAttempted` after each candidate
    completes (in completion order, not launch order).
    """
    emit = on_event or (lambda _e: None)

    base = list(tactics) if tactics is not None else list(DEFAULT_HAMMER_TACTICS)
    if max_candidates is not None:
        if max_candidates < 1:
            raise ValueError("max_candidates must be >= 1")
        base = base[:max_candidates]

    llm_tactics: list[str] = []
    if with_llm and llm is not None:
        llm_tactics = _propose_llm_tactics(
            statement=statement,
            llm=llm,
            limit=_LLM_MAX_CANDIDATES,
        )

    all_candidates: list[tuple[str, bool]] = [(t, False) for t in base] + [
        (t, True) for t in llm_tactics
    ]
    # De-duplicate while preserving order and the first "via_llm" tag.
    seen: set[str] = set()
    unique: list[tuple[str, bool]] = []
    for tactic, via_llm in all_candidates:
        key = tactic.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append((key, via_llm))

    initial_goal = _infer_initial_goal(statement)
    total = len(unique)

    if total == 0:
        return TryProveResult(
            ok=False,
            statement=statement,
            total_elapsed_ms=0,
            with_llm=with_llm,
            max_candidates=max_candidates or 0,
        )

    workers = max_workers if max_workers is not None else max(1, min(total, 8))

    results: list[TryProveCandidate] = []
    total_elapsed = 0

    def _run_one(idx: int, tactic: str, via_llm: bool) -> TryProveCandidate:
        source = compose_attempt_source(statement, tactic, imports=imports)
        check_result: LeanCheckResult = lean_check(
            code=source,
            project_root=project_root,
            timeout_s=timeout_s,
            use_daemon=use_daemon,
            auto_spawn=auto_spawn,
        )
        return TryProveCandidate(
            tactic=tactic,
            snippet=f"by {tactic}",
            source=source,
            ok=check_result.ok,
            elapsed_ms=check_result.elapsed_ms,
            via_llm=via_llm,
            error_summary=None if check_result.ok else _first_error_summary(check_result),
            hint=None if check_result.ok else _first_error_hint(check_result),
            goal_before=initial_goal,
            goal_after=check_result.goals_after,
        )

    # Parallel execution. ThreadPoolExecutor is appropriate: lean_check is
    # I/O-bound (subprocess or socket round-trip) so the GIL is released
    # during the wait, and the daemon sequentialises true concurrency on its
    # end anyway.
    with ThreadPoolExecutor(max_workers=workers) as ex:
        future_to_idx = {
            ex.submit(_run_one, idx, tactic, via_llm): (idx, tactic)
            for idx, (tactic, via_llm) in enumerate(unique)
        }
        for fut in as_completed(future_to_idx):
            idx, tactic = future_to_idx[fut]
            cand = fut.result()
            total_elapsed += cand.elapsed_ms
            results.append(cand)
            emit(TacticAttempted(
                tactic=tactic,
                index=idx,
                total=total,
                ok=cand.ok,
                elapsed_ms=cand.elapsed_ms,
            ))

    # Rank successes: builtin-first, then by the built-in ordering, then by
    # elapsed time (fastest kernel-check wins ties). LLM candidates come
    # after the built-ins so the "never ship an oracle" default stays safe
    # even when the LLM happens to propose a one-liner.
    builtin_order = {t: i for i, t in enumerate(base)}

    def _sort_key(c: TryProveCandidate) -> tuple[int, int, int]:
        via_llm_bucket = 1 if c.via_llm else 0
        builtin_rank = builtin_order.get(c.tactic, len(builtin_order))
        return (via_llm_bucket, builtin_rank, c.elapsed_ms)

    successes = sorted([c for c in results if c.ok], key=_sort_key)
    for rank, cand in enumerate(successes):
        cand.rank = rank
    failures = [c for c in results if not c.ok]

    return TryProveResult(
        ok=bool(successes),
        statement=statement,
        successes=successes,
        failures=failures,
        total_elapsed_ms=total_elapsed,
        with_llm=with_llm,
        max_candidates=max_candidates or 0,
    )


# ─── LLM-backed llmqed path ──────────────────────────────────────────────────


_LLMQED_SYSTEM = (
    "You are a Lean 4 proof assistant. Given a Lean 4 statement, propose "
    "short tactic-mode proof bodies that might close the goal. Reply with "
    "one tactic per line, no numbering, no prose. Prefer one-liners. "
    "Do not include 'by', 'example', 'theorem', or any keyword — just the "
    "tactic text itself, e.g. 'simp' or 'linarith' or 'exact Nat.succ_pos n'."
)


_TACTIC_LINE_RE = re.compile(r"^[\-\*\d\.\)\s]*([^\n]+?)\s*$")


def _propose_llm_tactics(
    *,
    statement: str,
    llm: LLMBackend,
    limit: int,
) -> list[str]:
    """Ask the LLM for up to ``limit`` candidate tactics.

    Raises are swallowed — the hammer must degrade to built-in tactics if
    the LLM is unreachable or misbehaves. The parsing is intentionally
    permissive: we strip bullets and obvious noise, then let the kernel
    check sort the signal from the hallucinations.
    """
    from grd.core.lean.autoformalize.llm import LLMMessage  # noqa: PLC0415

    user_prompt = (
        "Propose up to "
        f"{limit} candidate Lean 4 tactics (one per line) that might close "
        f"this goal:\n\n{statement}\n"
    )
    try:
        response = llm.complete(
            system=_LLMQED_SYSTEM,
            messages=[LLMMessage(role="user", content=user_prompt)],
            temperature=0.3,
        )
    except Exception:  # noqa: BLE001
        return []

    tactics: list[str] = []
    for raw in response.splitlines():
        match = _TACTIC_LINE_RE.match(raw)
        if not match:
            continue
        line = match.group(1).strip()
        if not line:
            continue
        # Strip a leading 'by ' that the LLM may have included despite the
        # instructions.
        if line.lower().startswith("by "):
            line = line[3:].strip()
        if line.startswith("```") or line.endswith("```"):
            continue
        tactics.append(line)
        if len(tactics) >= limit:
            break
    return tactics
