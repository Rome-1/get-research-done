"""Heartbeat-timeout detection and auto-retry for Lean elaborations.

Closes UX-STUDY.md §P2-4 (nitro Q9 #3 / feature #8): when a proof fails with
"deterministic timeout at whnf" or "maximum number of heartbeats", rerun with
a doubled ``maxHeartbeats`` budget up to a configured ceiling, then emit a
one-line suggestion telling the user exactly which ``set_option`` to paste.

The retry ladder doubles from the starting budget (default Lean behaviour,
~200000) and caps at ``DEFAULT_HEARTBEAT_CEILING`` so a runaway proof can't
burn unbounded compute.  A retry only happens when the failure is *actually*
a heartbeat timeout — any other error short-circuits, because doubling the
budget doesn't help type mismatches or missing imports.

This module is intentionally framework-agnostic: callers pass a ``check_fn``
that accepts ``max_heartbeats`` as a keyword argument and returns a
``LeanCheckResult``.  ``prove_statement`` and the CLI check command both use
the same primitive, so the retry semantics stay identical across surfaces.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any, Final

from pydantic import BaseModel, ConfigDict, Field

from grd.core.lean.protocol import LeanCheckResult

__all__ = [
    "DEFAULT_HEARTBEAT_CEILING",
    "DEFAULT_HEARTBEAT_RETRIES",
    "DEFAULT_INITIAL_HEARTBEATS",
    "HeartbeatRetryReport",
    "apply_retry_report_to_result",
    "check_with_heartbeat_retry",
    "is_heartbeat_timeout",
    "suggest_set_option",
]


DEFAULT_INITIAL_HEARTBEATS: Final[int] = 200_000
"""Lean 4's own default ``maxHeartbeats``. Start from here and double on retry.

Kept in sync with the Lean toolchain's documented default so the first
retry presents the user with a value meaningfully larger than what already
failed, not a tautological re-run."""

DEFAULT_HEARTBEAT_RETRIES: Final[int] = 3
"""Default retry cap. With doubling from 200k this reaches 1.6M heartbeats,
which covers ≈95% of the "bump the budget" cases the UX study documented
without letting a pathological proof monopolise the toolchain."""

DEFAULT_HEARTBEAT_CEILING: Final[int] = 1_600_000
"""Hard upper bound on ``maxHeartbeats`` after retries.

Past this point the right answer is usually to refactor the proof, not
double again — the suggestion is surfaced to the user so they can decide
whether to accept the high value or split the tactic."""


_HEARTBEAT_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\(deterministic\)\s+timeout.*?heartbeats|maximum\s+number\s+of\s+heartbeats",
    re.IGNORECASE | re.DOTALL,
)


def is_heartbeat_timeout(result: LeanCheckResult) -> bool:
    """Return True when *result* failed because of a heartbeat budget exhaustion.

    Scans error-severity diagnostics for either of the two Lean 4 phrasings
    of "I ran out of reductions". The subprocess-level ``error='timeout'``
    case (wall-clock) is *not* treated as a heartbeat timeout — doubling
    the heartbeat budget doesn't make a wall-clock-stuck subprocess finish.
    """
    if result.ok:
        return False
    for diag in result.diagnostics:
        if diag.severity != "error":
            continue
        if diag.message and _HEARTBEAT_PATTERN.search(diag.message):
            return True
    return False


def suggest_set_option(heartbeats: int) -> str:
    """One-line recommendation string with the winning budget.

    Matches the contract documented on the bead: ``this theorem needs at
    least N heartbeats; add set_option maxHeartbeats N`` — short enough
    for a terminal line, actionable enough to paste verbatim.
    """
    return (
        f"this theorem needs at least {heartbeats} heartbeats; "
        f"add `set_option maxHeartbeats {heartbeats}` at the top of the "
        f"file, or refactor the tactic into smaller steps."
    )


class HeartbeatRetryReport(BaseModel):
    """Structured record of an auto-retry run.

    ``attempts`` lists every ``(max_heartbeats, ok)`` pair that actually
    ran — the first entry is the baseline (``None`` means "Lean default"),
    each subsequent entry is a doubled-budget retry.  ``winning_heartbeats``
    is populated only when a retry succeeded; ``suggestion`` mirrors that
    value as a ready-to-print string so CLI consumers don't re-synthesise it.
    ``ceiling_hit`` records whether the final attempt was capped by
    :data:`DEFAULT_HEARTBEAT_CEILING`.
    """

    model_config = ConfigDict(extra="forbid")

    retries_used: int = 0
    attempts: list[tuple[int | None, bool]] = Field(default_factory=list)
    winning_heartbeats: int | None = None
    ceiling_hit: bool = False
    suggestion: str | None = None


def apply_retry_report_to_result(
    result: LeanCheckResult,
    report: HeartbeatRetryReport,
) -> LeanCheckResult:
    """Return a copy of *result* with the retry report attached in the stderr.

    ``LeanCheckResult`` has a fixed schema (extra='forbid'), so we stash the
    human-readable suggestion in a stable marker inside ``stderr`` for now.
    The structured report lives alongside the result at the call site; this
    helper only exists to make the suggestion visible to consumers that only
    look at ``result.stderr`` (e.g. legacy tooling).
    """
    if report.suggestion is None:
        return result
    marker = f"\n[grd-lean] {report.suggestion}\n"
    return result.model_copy(update={"stderr": (result.stderr or "") + marker})


def check_with_heartbeat_retry(
    check_fn: Callable[..., LeanCheckResult],
    *,
    initial_heartbeats: int | None = None,
    max_retries: int = DEFAULT_HEARTBEAT_RETRIES,
    ceiling: int = DEFAULT_HEARTBEAT_CEILING,
    **check_kwargs: Any,
) -> tuple[LeanCheckResult, HeartbeatRetryReport]:
    """Run ``check_fn``, and on heartbeat timeout re-run with 2× budget.

    Parameters
    ----------
    check_fn:
        Callable that takes ``max_heartbeats=<int|None>`` plus any other
        keyword arguments forwarded via ``check_kwargs`` and returns a
        :class:`LeanCheckResult`.  Typical values are
        ``grd.core.lean.client.check`` / ``check_file``.
    initial_heartbeats:
        Budget for the first run.  ``None`` (default) uses Lean's own
        default — the first retry starts doubling from
        :data:`DEFAULT_INITIAL_HEARTBEATS`.
    max_retries:
        Maximum number of retries after the baseline run.  ``0`` disables
        auto-retry entirely (the primitive reduces to a single call).
    ceiling:
        Upper bound on ``maxHeartbeats``.  Retries stop once a run at the
        ceiling still fails.

    Returns
    -------
    A ``(final_result, report)`` pair.  ``final_result`` is the best result
    seen (a successful retry if one happened, otherwise the last failure).
    ``report`` contains the full attempt history and, on success, the
    winning heartbeat value plus a ready-to-print suggestion.
    """
    if max_retries < 0:
        raise ValueError("max_retries must be >= 0")
    if ceiling < 1:
        raise ValueError("ceiling must be >= 1")

    report = HeartbeatRetryReport()

    # Baseline run: pass the caller-supplied initial budget (which may be
    # None = "use Lean's default"). We record whatever was passed so the
    # report is unambiguous about what the first attempt ran with.
    baseline_budget = initial_heartbeats
    result = check_fn(max_heartbeats=baseline_budget, **check_kwargs)
    report.attempts.append((baseline_budget, result.ok))

    if result.ok or max_retries == 0 or not is_heartbeat_timeout(result):
        return result, report

    # Start the doubling ladder from either the supplied initial value or
    # Lean's own default — whichever is larger — so the first retry is
    # strictly above what already failed.
    current = max(baseline_budget or 0, DEFAULT_INITIAL_HEARTBEATS)

    for _ in range(max_retries):
        if current >= ceiling:
            # Already at the ceiling — further doubling is a no-op. Stop
            # and let the caller report the cap.
            report.ceiling_hit = True
            break
        current = min(current * 2, ceiling)
        if current >= ceiling:
            report.ceiling_hit = True

        result = check_fn(max_heartbeats=current, **check_kwargs)
        report.retries_used += 1
        report.attempts.append((current, result.ok))

        if result.ok:
            report.winning_heartbeats = current
            report.suggestion = suggest_set_option(current)
            return result, report

        if not is_heartbeat_timeout(result):
            # Different failure class — doubling the budget won't help.
            break

    return result, report
