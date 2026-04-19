"""First-class counterexample search for Lean 4 statements (ge-16j / P2-3).

Where :mod:`grd.core.lean.try_prove` hunts for a kernel-checked *proof*, this
module hunts for a kernel-checked *refutation*. Three methods run in parallel,
each producing a witness that survives a kernel check — "never ship an oracle"
applies just as firmly to counterexamples as it does to proofs (UX-STUDY.md
§P2-3, external-research.md §9, Alexeev/Xena Dec 2025).

Methods, each yielding a :class:`CounterexampleCandidate` whose ``ok=True``
means a counterexample has been genuinely established by the Lean kernel:

* ``decide`` — compose ``example : ¬(<prop>) := by decide`` and kernel-check.
  When the statement reduces decidably (finite/Bool-valued domains) and is
  false, this produces a *global* counterexample certificate.
* ``plausible`` — compose ``example : <prop> := by plausible`` and kernel-check.
  The twist: Plausible ``succeeds`` the tactic only when it *fails to falsify*
  the goal, so a *failing* kernel check whose diagnostics mention "found a
  counterexample" is the signal. We parse the reported witness from the
  diagnostic text.
* ``llm`` — ask the configured LLM for concrete witnesses (one per line) and
  kernel-check ``example : ¬(<prop applied to witness>) := by <witness_tactic>``
  for each. The LLM never decides the answer; the kernel does. Without a
  configured backend, this method is a no-op (matches ``try_prove`` semantics).

Users combine methods via ``methods=[...]``; ``budget`` caps the total number
of candidates across methods *before* dedup so noisy LLM proposals can't blow
the worker pool.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

from grd.core.lean.client import check as lean_check
from grd.core.lean.events import EventCallback, TacticAttempted
from grd.core.lean.protocol import LeanCheckResult
from grd.core.lean.prove import (
    _KEYWORD_PREFIXES,
    _first_error_hint,
    _first_error_summary,
)

if TYPE_CHECKING:
    from grd.core.lean.autoformalize.llm import LLMBackend

__all__ = [
    "DEFAULT_METHODS",
    "CounterexampleCandidate",
    "CounterexampleResult",
    "find_counterexample",
]


Method = Literal["decide", "plausible", "llm"]


DEFAULT_METHODS: tuple[str, ...] = ("decide", "plausible")
"""Default methods when the caller doesn't pass ``methods``.

``llm`` is opt-in via ``with_llm=True`` (and requires a configured backend);
keeping it off the default list mirrors ``try_prove``'s "never shell-out to
the network unless asked" discipline.
"""


_LLM_MAX_WITNESSES = 8
"""Cap on LLM-proposed witnesses per run."""


class CounterexampleCandidate(BaseModel):
    """One candidate refutation, kernel-checked in parallel."""

    model_config = ConfigDict(extra="forbid")

    method: Method
    witness: str | None = Field(
        default=None,
        description=(
            "Concrete witness text (e.g. 'n := 7') for ``llm``/``plausible`` "
            "candidates, ``None`` for the global ``decide`` certificate."
        ),
    )
    tactic: str = Field(description="Kernel-check tactic used for this candidate (e.g. 'decide').")
    snippet: str = Field(description="Clickable one-line summary, e.g. '¬P via decide' or 'n = 7 (decide)'.")
    source: str = Field(description="Full Lean source that was kernel-checked.")
    ok: bool
    elapsed_ms: int = 0
    rank: int | None = Field(
        default=None,
        description="Position in the ranked list (0 = best). ``None`` for rejected candidates.",
    )
    via_llm: bool = False
    error_summary: str | None = None
    hint: str | None = None
    plausible_message: str | None = Field(
        default=None,
        description="Raw Plausible diagnostic text when method=='plausible'.",
    )


class CounterexampleResult(BaseModel):
    """Aggregate outcome of a parallel counterexample search."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    statement: str
    counterexamples: list[CounterexampleCandidate] = Field(
        default_factory=list,
        description="Kernel-verified refutations, ranked best-first.",
    )
    rejected: list[CounterexampleCandidate] = Field(
        default_factory=list,
        description="Candidates where the kernel did not confirm a counterexample.",
    )
    methods: list[str] = Field(default_factory=list)
    total_elapsed_ms: int = 0
    with_llm: bool = False
    budget: int = 0


def find_counterexample(
    statement: str,
    *,
    project_root: Path,
    methods: Iterable[str] | None = None,
    budget: int | None = None,
    witness_tactic: str = "decide",
    imports: list[str] | None = None,
    timeout_s: float = 30.0,
    with_llm: bool = False,
    llm: LLMBackend | None = None,
    use_daemon: bool = True,
    auto_spawn: bool = True,
    max_workers: int | None = None,
    on_event: EventCallback = None,
) -> CounterexampleResult:
    """Run counterexample-finding methods in parallel; return every refutation.

    ``statement`` is the proposition under test. Accepted shapes match
    :func:`grd.core.lean.prove.compose_attempt_source`: bare proposition,
    ``theorem foo : <prop>`` signature, or a full definition whose ``:=``
    tail is discarded.

    ``methods`` selects the techniques to attempt (default
    :data:`DEFAULT_METHODS`). ``with_llm`` enables the ``llm`` method in
    addition — but only when an ``llm`` backend is configured.

    ``budget`` caps the total number of kernel checks launched across
    methods *after* LLM expansion. Useful for smoke tests and
    budget-bounded agent invocations. ``None`` means "no cap".

    ``witness_tactic`` is the tactic used to kernel-check each LLM-proposed
    witness negation (``example : ¬ (<prop> <witness>) := by <tactic>``).
    ``decide`` is the safe default for finite/decidable instances;
    ``norm_num`` or ``simp`` are common overrides.
    """
    emit = on_event or (lambda _e: None)

    requested = list(methods) if methods is not None else list(DEFAULT_METHODS)
    if with_llm and "llm" not in requested:
        requested.append("llm")

    invalid = [m for m in requested if m not in ("decide", "plausible", "llm")]
    if invalid:
        raise ValueError(f"unknown counterexample method(s): {invalid}. Valid: decide, plausible, llm.")
    # Preserve caller order while deduplicating.
    seen_methods: set[str] = set()
    ordered_methods: list[str] = []
    for m in requested:
        if m in seen_methods:
            continue
        seen_methods.add(m)
        ordered_methods.append(m)

    proposition = _extract_proposition(statement)

    # Build the concrete candidate list. Each entry is (method, witness, tactic).
    pending: list[tuple[Method, str | None, str]] = []

    if "decide" in ordered_methods:
        pending.append(("decide", None, "decide"))

    if "plausible" in ordered_methods:
        pending.append(("plausible", None, "plausible"))

    llm_witnesses: list[str] = []
    if "llm" in ordered_methods:
        if llm is not None:
            llm_witnesses = _propose_llm_witnesses(
                statement=statement,
                llm=llm,
                limit=_LLM_MAX_WITNESSES,
            )
        # When llm is None we silently degrade (matches try_prove).
        for witness in llm_witnesses:
            pending.append(("llm", witness, witness_tactic))

    if budget is not None:
        if budget < 1:
            raise ValueError("budget must be >= 1")
        pending = pending[:budget]

    total = len(pending)

    if total == 0:
        return CounterexampleResult(
            ok=False,
            statement=statement,
            methods=ordered_methods,
            with_llm=with_llm,
            budget=budget or 0,
        )

    workers = max_workers if max_workers is not None else max(1, min(total, 8))

    def _run_one(method: Method, witness: str | None, tactic: str) -> CounterexampleCandidate:
        if method == "decide":
            source = _compose_decide_negation(proposition, imports=imports)
        elif method == "plausible":
            source = _compose_plausible_attempt(proposition, imports=imports)
        else:  # llm
            assert witness is not None
            source = _compose_witness_negation(proposition, witness, tactic, imports=imports)

        check_result: LeanCheckResult = lean_check(
            code=source,
            project_root=project_root,
            timeout_s=timeout_s,
            use_daemon=use_daemon,
            auto_spawn=auto_spawn,
        )

        return _interpret_result(
            method=method,
            witness=witness,
            tactic=tactic,
            source=source,
            check_result=check_result,
        )

    results: list[CounterexampleCandidate] = []
    total_elapsed = 0

    with ThreadPoolExecutor(max_workers=workers) as ex:
        future_to_meta = {
            ex.submit(_run_one, method, witness, tactic): (idx, method, witness, tactic)
            for idx, (method, witness, tactic) in enumerate(pending)
        }
        for fut in as_completed(future_to_meta):
            idx, method, witness, tactic = future_to_meta[fut]
            cand = fut.result()
            total_elapsed += cand.elapsed_ms
            results.append(cand)
            label = _event_label(method, witness)
            emit(
                TacticAttempted(
                    tactic=label,
                    index=idx,
                    total=total,
                    ok=cand.ok,
                    elapsed_ms=cand.elapsed_ms,
                )
            )

    # Rank: decide before plausible before llm, then by elapsed time (fastest
    # kernel-check wins ties). Matches try_prove's "safe default first" rule.
    method_order = {"decide": 0, "plausible": 1, "llm": 2}

    def _sort_key(c: CounterexampleCandidate) -> tuple[int, int]:
        return (method_order.get(c.method, 99), c.elapsed_ms)

    counterexamples = sorted([c for c in results if c.ok], key=_sort_key)
    for rank, cand in enumerate(counterexamples):
        cand.rank = rank
    rejected = [c for c in results if not c.ok]

    return CounterexampleResult(
        ok=bool(counterexamples),
        statement=statement,
        counterexamples=counterexamples,
        rejected=rejected,
        methods=ordered_methods,
        total_elapsed_ms=total_elapsed,
        with_llm=with_llm,
        budget=budget or 0,
    )


# ─── Source composition ──────────────────────────────────────────────────────


def _extract_proposition(statement: str) -> str:
    """Strip a keyword header and ``:=`` tail to get the bare proposition.

    ``theorem foo : ∀ n, P n`` → ``∀ n, P n``.  A ``:=`` tail is discarded
    regardless of keyword.  Bare propositions are returned verbatim.

    Raises ``ValueError`` on an empty statement (matches ``prove`` convention).
    """
    body = statement.strip()
    if not body:
        raise ValueError("statement must not be empty")
    if ":=" in body:
        body = body.split(":=", 1)[0].rstrip()
    if body.startswith(_KEYWORD_PREFIXES):
        # "theorem foo : P" → after keyword+name → ": P" → " P"
        for prefix in _KEYWORD_PREFIXES:
            if body.startswith(prefix):
                rest = body[len(prefix) :].lstrip()
                if ":" in rest:
                    return rest.split(":", 1)[1].strip()
                return rest
    return body


def _prelude(imports: list[str] | None) -> str:
    if not imports:
        return ""
    return "\n".join(f"import {mod}" for mod in imports) + "\n"


def _compose_decide_negation(proposition: str, *, imports: list[str] | None = None) -> str:
    """``example : ¬(<prop>) := by decide``."""
    return f"{_prelude(imports)}example : ¬({proposition}) := by decide\n"


def _compose_plausible_attempt(proposition: str, *, imports: list[str] | None = None) -> str:
    """``example : <prop> := by plausible`` — a *failure* is the signal."""
    return f"{_prelude(imports)}example : {proposition} := by plausible\n"


def _compose_witness_negation(
    proposition: str,
    witness: str,
    tactic: str,
    *,
    imports: list[str] | None = None,
) -> str:
    """``example : ¬(<prop with witness substituted>) := by <tactic>``.

    The witness is spliced by textual substitution of the outermost binder.
    If no binder is detectable, the witness is appended as an application —
    this preserves behaviour for already-quantifier-free propositions where
    the LLM proposed a full saturated term the user means to refute directly.
    """
    spliced = _substitute_witness(proposition, witness)
    prelude = _prelude(imports)
    return f"{prelude}example : ¬({spliced}) := by {tactic}\n"


_BINDER_RE = re.compile(
    r"^(?:∀|forall)\s+"  # leading quantifier
    r"(?:\(([^)]+)\)|([^,]+?))"  # "(n : Nat)", "n : Nat", "n m", or "n"
    r"\s*,\s*",  # comma separator
    re.UNICODE,
)


def _substitute_witness(proposition: str, witness: str) -> str:
    """Replace leading ``∀`` binders with a lambda-applied witness.

    Peels every leading ``∀`` binder off the proposition and wraps the
    remaining body in a lambda whose parameters match the bound names,
    applied to the witness text. Examples:

    * ``∀ n : Nat, P n`` + witness ``7``  → ``(fun n => P n) 7``
    * ``∀ n m, P n m``   + witness ``0 1`` → ``(fun n m => P n m) 0 1``
    * ``∀ n, ∀ m, Q``    + witness ``3 4`` → ``(fun n m => Q) 3 4``

    A named assignment like ``n := 7`` is accepted — only the value after
    ``:=`` is spliced. Quantifier-free propositions fall back to plain
    application so the caller can pass a saturated refutation term directly.
    """
    w = witness.strip()
    if ":=" in w:
        w = w.split(":=", 1)[1].strip()

    binders: list[str] = []
    rest = proposition
    while True:
        match = _BINDER_RE.match(rest)
        if not match:
            break
        raw_decl = match.group(1) or match.group(2) or ""
        # Names live before any ``:`` (type annotation). An unparenthesized
        # binder may still bind multiple names, e.g. ``n m : Nat``.
        names_part = raw_decl.split(":", 1)[0].strip()
        names = names_part.split()
        if not names:
            break
        binders.extend(names)
        rest = rest[match.end() :]

    if not binders:
        return proposition if not w else f"{proposition} {w}"

    binder_str = " ".join(binders)
    return f"(fun {binder_str} => {rest}) {w}"


# ─── Result interpretation ───────────────────────────────────────────────────


_PLAUSIBLE_COUNTEREXAMPLE_RE = re.compile(
    r"(?:plausible[^\n]*?)?(?:found\s+a?\s*counter[-\s]?example|counterexample\s+found)"
    r"[^\n]*",
    re.IGNORECASE,
)


def _interpret_result(
    *,
    method: Method,
    witness: str | None,
    tactic: str,
    source: str,
    check_result: LeanCheckResult,
) -> CounterexampleCandidate:
    """Turn a raw ``LeanCheckResult`` into a method-specific candidate verdict.

    The interpretation differs per method because each method encodes a
    different kernel-check convention:

    * ``decide``/``llm`` — kernel ``ok`` ⇔ counterexample confirmed.
    * ``plausible`` — kernel ``not ok`` + Plausible counterexample in
      diagnostics ⇔ counterexample confirmed. Kernel ``ok`` means the
      tactic closed the goal (statement is true — no counterexample).
    """
    if method in ("decide", "llm"):
        ok = check_result.ok
        snippet = _build_snippet(method, witness, tactic, ok=ok)
        return CounterexampleCandidate(
            method=method,
            witness=witness,
            tactic=tactic,
            snippet=snippet,
            source=source,
            ok=ok,
            elapsed_ms=check_result.elapsed_ms,
            via_llm=(method == "llm"),
            error_summary=None if ok else _first_error_summary(check_result),
            hint=None if ok else _first_error_hint(check_result),
        )

    # plausible
    plausible_msg = _extract_plausible_counterexample(check_result)
    # ok==True means Plausible claimed the statement; no counterexample.
    if check_result.ok:
        return CounterexampleCandidate(
            method="plausible",
            witness=witness,
            tactic=tactic,
            snippet="plausible: no counterexample found (goal closed)",
            source=source,
            ok=False,
            elapsed_ms=check_result.elapsed_ms,
            error_summary="plausible closed the goal — statement appears true",
        )

    confirmed = plausible_msg is not None
    return CounterexampleCandidate(
        method="plausible",
        witness=plausible_msg if confirmed else witness,
        tactic=tactic,
        snippet=(f"plausible: {plausible_msg}" if confirmed else "plausible: no counterexample reported"),
        source=source,
        ok=confirmed,
        elapsed_ms=check_result.elapsed_ms,
        plausible_message=plausible_msg,
        error_summary=None if confirmed else _first_error_summary(check_result),
        hint=None if confirmed else _first_error_hint(check_result),
    )


def _extract_plausible_counterexample(result: LeanCheckResult) -> str | None:
    """Best-effort extraction of a Plausible counterexample message.

    Plausible reports counterexamples in the tactic error text; the exact
    wording has varied across releases. We look for ``found a counterexample``
    or ``counterexample found`` anywhere in the diagnostics and return the
    surrounding line verbatim so the user can read the witness as Plausible
    pretty-printed it.
    """
    for diag in result.diagnostics:
        if diag.severity != "error" or not diag.message:
            continue
        for line in diag.message.splitlines():
            if _PLAUSIBLE_COUNTEREXAMPLE_RE.search(line):
                return line.strip()
        # Fallback: if any diagnostic line mentions "counter-example" /
        # "counterexample", grab the first such line.
        for line in diag.message.splitlines():
            lower = line.lower()
            if "counter" in lower and "example" in lower:
                return line.strip()
    return None


def _build_snippet(method: Method, witness: str | None, tactic: str, *, ok: bool) -> str:
    """Human-readable one-liner for the ranked list."""
    if method == "decide":
        return "¬ statement via decide" if ok else "decide: kernel rejected ¬statement"
    if method == "llm":
        w = witness or "?"
        return f"witness {w} (verified by {tactic})" if ok else f"witness {w}: kernel rejected refutation ({tactic})"
    return f"plausible ({tactic})"  # plausible snippets are overwritten in _interpret_result


def _event_label(method: Method, witness: str | None) -> str:
    if method == "llm" and witness is not None:
        return f"llm:{witness}"
    return method


# ─── LLM witness proposal ────────────────────────────────────────────────────


_LLM_SYSTEM = (
    "You are a Lean 4 counterexample finder. Given a universally-quantified "
    "Lean 4 statement, propose concrete witness values that would make the "
    "statement false. Reply with one witness per line, no numbering, no "
    "prose, no backticks. For a single binder propose bare values (e.g. "
    "'7', '-1', '0'); for multiple binders propose space-separated tuples "
    "in binder order (e.g. '0 1'). Do not restate the theorem; do not "
    "include 'by', 'example', 'theorem', or any keyword — just the witness."
)


_LINE_RE = re.compile(r"^\s*(?:[-*•]\s+|\d+[.)]\s+)?(.+?)\s*$")
"""Match a witness line after stripping conservative bullet markers.

Accepts ``- ``, ``* ``, ``• `` and ``1. `` / ``1) `` prefixes. Deliberately
does *not* strip bare leading digits — witnesses for natural-number
statements are frequently just ``0`` or ``42`` and must survive parsing.
"""


def _propose_llm_witnesses(
    *,
    statement: str,
    llm: LLMBackend,
    limit: int,
) -> list[str]:
    """Ask the LLM for up to ``limit`` candidate witnesses.

    Raises are swallowed — the search must degrade to the built-in methods
    if the LLM is unreachable. Parsing is deliberately permissive: strip
    bullets and noise, let the kernel distinguish real witnesses from
    hallucinated ones.
    """
    from grd.core.lean.autoformalize.llm import LLMMessage  # noqa: PLC0415

    user_prompt = (
        f"Propose up to {limit} concrete Lean 4 witnesses (one per line) "
        f"that might falsify this statement:\n\n{statement}\n"
    )
    try:
        response = llm.complete(
            system=_LLM_SYSTEM,
            messages=[LLMMessage(role="user", content=user_prompt)],
            temperature=0.3,
        )
    except Exception:  # noqa: BLE001
        return []

    witnesses: list[str] = []
    seen: set[str] = set()
    for raw in response.splitlines():
        match = _LINE_RE.match(raw)
        if not match:
            continue
        line = match.group(1).strip()
        if not line or line.startswith("```") or line.endswith("```"):
            continue
        if line in seen:
            continue
        seen.add(line)
        witnesses.append(line)
        if len(witnesses) >= limit:
            break
    return witnesses
