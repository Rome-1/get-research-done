"""Tactic-search proof attempts for Lean 4 statements.

MVP scope for ge-8cn: iterate a fixed ladder of common tactics
(``rfl``, ``decide``, ``norm_num``, ``ring``, ``linarith``, ``omega``,
``simp``, ``aesop``) and return the first one that type-checks. Each
attempt composes ``theorem <stmt> := by <tactic>`` and invokes
``grd.core.lean.client.check`` — no Pantograph REPL state is held across
attempts yet (follow-up bead ``ge-nsd`` handles persistent REPL reuse,
``ge-48t`` handles LLM-generated tactic candidates).

The statement is passed through verbatim so callers can supply:

    * a full theorem (``theorem foo : P → P := sorry``) — the ``:=`` tail is
      rewritten with each candidate tactic,
    * a signature with a keyword header (``theorem foo : P → P``) — we
      append ``:= by <tactic>``,
    * a bare proposition (``1 + 1 = 2``) — we wrap it as
      ``example : <prop> := by <tactic>``.

Tests monkeypatch ``lean_client.check`` to avoid a hard dependency on a
real Lean toolchain during CI.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from grd.core.lean.client import check as lean_check
from grd.core.lean.events import EventCallback, TacticAttempted
from grd.core.lean.protocol import LeanCheckResult

__all__ = [
    "DEFAULT_TACTIC_LADDER",
    "ProofAttempt",
    "ProveResult",
    "compose_attempt_source",
    "prove_statement",
]


DEFAULT_TACTIC_LADDER: tuple[str, ...] = (
    "rfl",
    "decide",
    "norm_num",
    "ring",
    "linarith",
    "omega",
    "simp",
    "aesop",
)
"""Ordered tactic candidates tried by default.

Cheap decidable tactics first (``rfl``/``decide``), then arithmetic
normalizers, then the general-purpose closers (``simp``/``aesop``).
"""


class ProofAttempt(BaseModel):
    """One candidate tactic run against the statement."""

    model_config = ConfigDict(extra="forbid")

    tactic: str
    ok: bool
    elapsed_ms: int = 0
    error_summary: str | None = None
    hint: str | None = None


class ProveResult(BaseModel):
    """Aggregate outcome of a tactic-ladder proof search."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    statement: str
    proof: str | None = None
    attempts: list[ProofAttempt] = Field(default_factory=list)
    total_elapsed_ms: int = 0


_KEYWORD_PREFIXES: tuple[str, ...] = ("theorem", "lemma", "example", "def", "instance")


def compose_attempt_source(
    statement: str,
    tactic: str,
    *,
    imports: list[str] | None = None,
) -> str:
    """Build the Lean source that would prove *statement* with *tactic*.

    ``imports`` are prepended as ``import <name>`` lines — the same shape
    ``lean_client.check`` already expects, duplicated here so callers that
    use this function for dry-run / debug logging get the full source.
    """
    body = statement.strip()
    if not body:
        raise ValueError("statement must not be empty")

    if ":=" in body:
        head = body.split(":=", 1)[0].rstrip()
        core = f"{head} := by {tactic}"
    elif body.startswith(_KEYWORD_PREFIXES):
        core = f"{body.rstrip()} := by {tactic}"
    else:
        core = f"example : {body} := by {tactic}"

    if imports:
        prelude = "\n".join(f"import {mod}" for mod in imports)
        return f"{prelude}\n{core}\n"
    return f"{core}\n"


def prove_statement(
    statement: str,
    *,
    project_root: Path,
    tactics: list[str] | None = None,
    imports: list[str] | None = None,
    max_attempts: int | None = None,
    timeout_s: float = 30.0,
    use_daemon: bool = True,
    auto_spawn: bool = True,
    on_event: EventCallback = None,
) -> ProveResult:
    """Try ``tactics`` (or the default ladder) in order; return the first pass.

    ``max_attempts`` truncates the ladder — useful for smoke tests and for
    budget-constrained agent invocations. The returned ``ProveResult``
    always lists every attempt actually made so the caller can see partial
    progress, even on failure.

    ``on_event`` receives ``TacticAttempted`` after each candidate tactic.
    """
    _emit = on_event or (lambda _e: None)
    ladder = list(tactics) if tactics else list(DEFAULT_TACTIC_LADDER)
    if max_attempts is not None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        ladder = ladder[:max_attempts]

    attempts: list[ProofAttempt] = []
    total_elapsed = 0
    proof_source: str | None = None
    overall_ok = False
    ladder_len = len(ladder)

    for idx, tactic in enumerate(ladder):
        source = compose_attempt_source(statement, tactic, imports=imports)
        result: LeanCheckResult = lean_check(
            code=source,
            project_root=project_root,
            timeout_s=timeout_s,
            use_daemon=use_daemon,
            auto_spawn=auto_spawn,
        )
        total_elapsed += result.elapsed_ms
        attempt = ProofAttempt(
            tactic=tactic,
            ok=result.ok,
            elapsed_ms=result.elapsed_ms,
            error_summary=None if result.ok else _first_error_summary(result),
            hint=None if result.ok else _first_error_hint(result),
        )
        attempts.append(attempt)
        _emit(TacticAttempted(
            tactic=tactic,
            index=idx,
            total=ladder_len,
            ok=result.ok,
            elapsed_ms=result.elapsed_ms,
        ))
        if result.ok:
            overall_ok = True
            proof_source = source
            break

    return ProveResult(
        ok=overall_ok,
        statement=statement,
        proof=proof_source,
        attempts=attempts,
        total_elapsed_ms=total_elapsed,
    )


def _first_error_summary(result: LeanCheckResult) -> str:
    if result.error is not None:
        detail = result.error_detail or ""
        return f"{result.error}: {detail}".strip(": ") or result.error
    for diag in result.diagnostics:
        if diag.severity == "error":
            first_line = (diag.message or "").splitlines()[0] if diag.message else ""
            return first_line or "elaboration error"
    return "no error-level diagnostic"


def _first_error_hint(result: LeanCheckResult) -> str | None:
    """Return the first populated diagnostic hint, or ``None``.

    Mirrors ``_first_error_summary`` so agents reading ``ProofAttempt`` see
    both the raw summary (for fidelity) and the human-cause hint (for
    actionability) without having to re-parse diagnostics themselves.
    """
    for diag in result.diagnostics:
        if diag.severity == "error" and diag.hint:
            return diag.hint
    return None
