"""Stage 4: APOLLO-style compile-repair loop.

Per AUTOFORMALIZATION.md §5 and §8.2: iterate ``compile → classify error →
repair`` up to ``repair_budget`` times per candidate. Each repair call shows
the LLM the failing source + diagnostics + the classified error kind so it
can emit a targeted fix rather than a blind rewrite.

This module does not spawn its own compile worker — it calls the existing
``grd.core.lean.client.check`` seam so a) we reuse the Unix-socket daemon
instead of starting fresh Lean subprocesses, and b) tests can monkeypatch a
single function to simulate every compile outcome.

Hallucinated-identifier rejection is short-circuited: if the NameIndex can
already tell a candidate uses unknown identifiers, we classify the error
without waiting for Lean to confirm — saves 2-30s of compile time per
candidate. This is the DDR "generate-and-check" idea extended to repair.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from grd.core.lean.autoformalize.candidates import extract_lean_block
from grd.core.lean.autoformalize.llm import (
    ErrorKind,
    build_repair_messages,
    classify_compile_error,
)
from grd.core.lean.client import check as default_lean_check
from grd.core.lean.protocol import LeanCheckResult, LeanDiagnostic

if TYPE_CHECKING:
    from grd.core.lean.autoformalize.blueprint import BlueprintContext
    from grd.core.lean.autoformalize.candidates import Candidate
    from grd.core.lean.autoformalize.index import NameIndex
    from grd.core.lean.autoformalize.llm import LLMBackend

__all__ = [
    "LeanCheckFn",
    "RepairStep",
    "RepairOutcome",
    "repair_candidate",
]


LeanCheckFn = Callable[..., LeanCheckResult]
"""Signature of ``grd.core.lean.client.check``.

Carved out as a type alias so tests can pass a stub without type errors; the
runtime default is ``default_lean_check``.
"""


@dataclass(frozen=True)
class RepairStep:
    """One iteration of the repair loop (compile + optional LLM repair edit)."""

    iteration: int
    source: str
    ok: bool
    elapsed_ms: int
    error_kind: ErrorKind | None
    unknown_identifiers: list[str] = field(default_factory=list)
    repair_applied: bool = False


@dataclass(frozen=True)
class RepairOutcome:
    """Final verdict for one candidate after (up to) ``repair_budget`` steps.

    ``final_source`` is the last source we tried. On success it's the one that
    compiled cleanly; on failure it's the last repair attempt. Either way, the
    faithfulness gate runs against this source — callers don't have to look at
    the history to know what to back-translate.
    """

    ok: bool
    final_source: str
    steps: list[RepairStep] = field(default_factory=list)
    total_elapsed_ms: int = 0
    reason: str = ""


def repair_candidate(
    *,
    candidate: Candidate,
    blueprint: BlueprintContext,
    index: NameIndex,
    llm: LLMBackend,
    project_root: Path,
    repair_budget: int,
    timeout_s: float = 30.0,
    imports: list[str] | None = None,
    use_daemon: bool = True,
    lean_check: LeanCheckFn | None = None,
) -> RepairOutcome:
    """Compile ``candidate``; on failure, LLM-repair up to ``repair_budget`` times.

    The first iteration's ``repair_applied=False`` because no repair has been
    tried yet — it's the pristine compile of the candidate. Subsequent
    iterations are LLM-fixed versions.

    ``repair_budget`` is the total number of compile attempts (per §8.2 MVP:
    10-20). A budget of 0 means "compile once, no repairs" — useful for
    latency-sensitive dry-runs.
    """
    check = lean_check or default_lean_check
    steps: list[RepairStep] = []
    total_ms = 0
    source = candidate.source
    if repair_budget < 0:
        raise ValueError("repair_budget must be >= 0")

    # Total compile attempts allowed: the initial compile + repair_budget repairs.
    max_attempts = repair_budget + 1

    for iteration in range(max_attempts):
        is_repair = iteration > 0
        # Pre-compile Suffix Array Check: if we already know an identifier is
        # missing, treat it as a hallucination diagnostic without burning a
        # Lean compile slot.
        unknowns = index.unknown_identifiers(source)
        if unknowns:
            steps.append(
                RepairStep(
                    iteration=iteration,
                    source=source,
                    ok=False,
                    elapsed_ms=0,
                    error_kind="hallucinated_identifier",
                    unknown_identifiers=unknowns,
                    repair_applied=is_repair,
                )
            )
            if iteration == max_attempts - 1:
                return RepairOutcome(
                    ok=False,
                    final_source=source,
                    steps=steps,
                    total_elapsed_ms=total_ms,
                    reason=f"hallucinated identifiers: {', '.join(unknowns[:5])}",
                )
            source = _request_repair(
                llm=llm,
                blueprint=blueprint,
                source=source,
                lean_result=_synthetic_unknown_result(unknowns),
                error_kind="hallucinated_identifier",
            )
            continue

        result = check(
            code=source,
            project_root=project_root,
            imports=list(imports) if imports else None,
            timeout_s=timeout_s,
            use_daemon=use_daemon,
        )
        total_ms += result.elapsed_ms

        if result.ok:
            steps.append(
                RepairStep(
                    iteration=iteration,
                    source=source,
                    ok=True,
                    elapsed_ms=result.elapsed_ms,
                    error_kind=None,
                    repair_applied=is_repair,
                )
            )
            return RepairOutcome(
                ok=True,
                final_source=source,
                steps=steps,
                total_elapsed_ms=total_ms,
                reason="compiled" if not is_repair else f"repaired after {iteration} iterations",
            )

        error_kind = classify_compile_error(result, source)
        steps.append(
            RepairStep(
                iteration=iteration,
                source=source,
                ok=False,
                elapsed_ms=result.elapsed_ms,
                error_kind=error_kind,
                repair_applied=is_repair,
            )
        )
        if iteration == max_attempts - 1:
            return RepairOutcome(
                ok=False,
                final_source=source,
                steps=steps,
                total_elapsed_ms=total_ms,
                reason=f"budget exhausted ({max_attempts} compiles, last error: {error_kind})",
            )
        source = _request_repair(
            llm=llm,
            blueprint=blueprint,
            source=source,
            lean_result=result,
            error_kind=error_kind,
        )

    # Unreachable — the loop always returns on its last iteration.
    return RepairOutcome(
        ok=False,
        final_source=source,
        steps=steps,
        total_elapsed_ms=total_ms,
        reason="internal: exhausted loop without emitting a verdict",
    )


def _request_repair(
    *,
    llm: LLMBackend,
    blueprint: BlueprintContext,
    source: str,
    lean_result: LeanCheckResult,
    error_kind: ErrorKind,
) -> str:
    """Ask the LLM for a repair; extract the next Lean source to try."""
    system, messages = build_repair_messages(
        claim=blueprint.claim,
        previous_source=source,
        lean_result=lean_result,
        error_kind=error_kind,
        conventions=blueprint.conventions,
    )
    raw = llm.complete(system=system, messages=messages, temperature=0.3)
    return extract_lean_block(raw)


def _synthetic_unknown_result(unknowns: list[str]) -> LeanCheckResult:
    """Fabricate a LeanCheckResult that represents the DDR-detected failure.

    The repair prompt needs *some* diagnostic to show the LLM why we rejected
    the candidate; synthesizing one from the unknown identifiers makes the
    error feel like Lean's own output ("unknown identifier 'FooBar'"), which
    matches the LLM's training distribution and produces better repairs than
    a custom wrapper message.
    """
    messages = [f"unknown identifier '{ident}'" for ident in unknowns[:5]]
    return LeanCheckResult(
        ok=False,
        backend="subprocess",
        elapsed_ms=0,
        diagnostics=[LeanDiagnostic(severity="error", message=m) for m in messages],
    )
