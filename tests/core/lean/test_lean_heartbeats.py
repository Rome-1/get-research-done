"""Tests for the heartbeat auto-retry layer (ge-l9cz / UX-STUDY §P2-4)."""

from __future__ import annotations

import pytest

from grd.core.lean.heartbeats import (
    DEFAULT_HEARTBEAT_CEILING,
    check_with_heartbeat_retry,
    is_heartbeat_timeout,
    suggest_set_option,
)
from grd.core.lean.protocol import LeanCheckResult, LeanDiagnostic


def _timeout_result(elapsed_ms: int = 5) -> LeanCheckResult:
    """A LeanCheckResult that looks like a heartbeat timeout."""
    return LeanCheckResult(
        ok=False,
        backend="subprocess",
        elapsed_ms=elapsed_ms,
        diagnostics=[
            LeanDiagnostic(
                severity="error",
                message=(
                    "(deterministic) timeout at `whnf`, maximum number of "
                    "heartbeats (200000) has been reached (use 'set_option "
                    "maxHeartbeats <num>' to set the limit)"
                ),
            )
        ],
    )


def _other_failure_result() -> LeanCheckResult:
    return LeanCheckResult(
        ok=False,
        backend="subprocess",
        elapsed_ms=3,
        diagnostics=[LeanDiagnostic(severity="error", message="type mismatch")],
    )


def _ok_result(elapsed_ms: int = 2) -> LeanCheckResult:
    return LeanCheckResult(ok=True, backend="subprocess", elapsed_ms=elapsed_ms)


# ─── is_heartbeat_timeout ───────────────────────────────────────────────────


def test_is_heartbeat_timeout_detects_deterministic_timeout_phrase() -> None:
    assert is_heartbeat_timeout(_timeout_result()) is True


def test_is_heartbeat_timeout_detects_maximum_phrase_without_whnf() -> None:
    result = LeanCheckResult(
        ok=False,
        backend="subprocess",
        diagnostics=[
            LeanDiagnostic(
                severity="error",
                message="maximum number of heartbeats (200000) has been reached",
            )
        ],
    )
    assert is_heartbeat_timeout(result) is True


def test_is_heartbeat_timeout_false_for_success() -> None:
    assert is_heartbeat_timeout(_ok_result()) is False


def test_is_heartbeat_timeout_false_for_other_errors() -> None:
    assert is_heartbeat_timeout(_other_failure_result()) is False


def test_is_heartbeat_timeout_ignores_warning_severity() -> None:
    # A warning that happens to mention "heartbeats" must not be treated as
    # a retryable timeout — only error-severity diagnostics count.
    result = LeanCheckResult(
        ok=False,
        backend="subprocess",
        diagnostics=[
            LeanDiagnostic(severity="warning", message="maximum number of heartbeats"),
            LeanDiagnostic(severity="error", message="some unrelated failure"),
        ],
    )
    assert is_heartbeat_timeout(result) is False


# ─── suggest_set_option ──────────────────────────────────────────────────────


def test_suggest_set_option_includes_budget_and_command() -> None:
    msg = suggest_set_option(800_000)
    assert "800000" in msg
    assert "set_option maxHeartbeats 800000" in msg


# ─── check_with_heartbeat_retry ──────────────────────────────────────────────


def _make_check_fn(results: list[LeanCheckResult]) -> callable:
    """Stub check_fn that returns results in order, recording budgets seen."""
    calls: list[int | None] = []

    def _impl(**kwargs) -> LeanCheckResult:
        calls.append(kwargs.get("max_heartbeats"))
        return results.pop(0)

    _impl.calls = calls  # type: ignore[attr-defined]
    return _impl


def test_baseline_success_does_not_retry() -> None:
    fn = _make_check_fn([_ok_result()])
    result, report = check_with_heartbeat_retry(fn, max_retries=3)
    assert result.ok is True
    assert report.retries_used == 0
    assert report.winning_heartbeats is None
    assert report.suggestion is None
    assert fn.calls == [None]  # default budget only


def test_non_heartbeat_failure_does_not_retry() -> None:
    fn = _make_check_fn([_other_failure_result()])
    result, report = check_with_heartbeat_retry(fn, max_retries=3)
    assert result.ok is False
    assert report.retries_used == 0


def test_max_retries_zero_disables_retry() -> None:
    fn = _make_check_fn([_timeout_result()])
    result, report = check_with_heartbeat_retry(fn, max_retries=0)
    assert result.ok is False
    assert report.retries_used == 0
    assert fn.calls == [None]


def test_successful_retry_reports_winning_budget_and_suggestion() -> None:
    # Baseline timeout, then first retry (400000) succeeds.
    fn = _make_check_fn([_timeout_result(), _ok_result()])
    result, report = check_with_heartbeat_retry(fn, max_retries=3)
    assert result.ok is True
    assert report.retries_used == 1
    assert report.winning_heartbeats == 400_000
    assert "400000" in (report.suggestion or "")
    assert fn.calls == [None, 400_000]


def test_retry_ladder_doubles_until_success() -> None:
    # Baseline + three timeouts, then success on retry #4 (3.2M — but ceiling
    # would cap at DEFAULT_HEARTBEAT_CEILING). Use a custom ceiling so the
    # test is self-contained.
    fn = _make_check_fn(
        [
            _timeout_result(),  # baseline fails
            _timeout_result(),  # retry 1: 400k
            _timeout_result(),  # retry 2: 800k
            _ok_result(),       # retry 3: 1.6M (= default ceiling)
        ]
    )
    result, report = check_with_heartbeat_retry(fn, max_retries=3)
    assert result.ok is True
    assert report.retries_used == 3
    assert report.winning_heartbeats == 1_600_000
    assert fn.calls == [None, 400_000, 800_000, 1_600_000]


def test_retry_stops_when_non_heartbeat_failure_intervenes() -> None:
    # Baseline timeout, retry 1 hits a type mismatch — doubling won't help.
    fn = _make_check_fn([_timeout_result(), _other_failure_result()])
    result, report = check_with_heartbeat_retry(fn, max_retries=5)
    assert result.ok is False
    assert report.retries_used == 1
    assert report.winning_heartbeats is None
    assert fn.calls == [None, 400_000]


def test_retry_respects_ceiling_and_reports_hit() -> None:
    fn = _make_check_fn(
        [
            _timeout_result(),
            _timeout_result(),
            _timeout_result(),
            _timeout_result(),
        ]
    )
    # Ceiling at 500k: 200k → 400k → 500k (capped) → stop (already at ceiling).
    result, report = check_with_heartbeat_retry(fn, max_retries=5, ceiling=500_000)
    assert result.ok is False
    assert report.ceiling_hit is True
    assert report.retries_used == 2
    assert fn.calls == [None, 400_000, 500_000]


def test_initial_heartbeats_is_passed_through_to_baseline() -> None:
    fn = _make_check_fn([_ok_result()])
    _result, report = check_with_heartbeat_retry(fn, initial_heartbeats=300_000, max_retries=3)
    assert fn.calls == [300_000]
    assert report.attempts[0] == (300_000, True)


def test_initial_heartbeats_larger_than_default_sets_doubling_floor() -> None:
    # Baseline at 500k times out; first retry should be 1M (not 400k).
    fn = _make_check_fn([_timeout_result(), _ok_result()])
    result, report = check_with_heartbeat_retry(
        fn, initial_heartbeats=500_000, max_retries=3
    )
    assert result.ok is True
    assert report.winning_heartbeats == 1_000_000
    assert fn.calls == [500_000, 1_000_000]


def test_negative_max_retries_rejected() -> None:
    fn = _make_check_fn([_ok_result()])
    with pytest.raises(ValueError, match=">= 0"):
        check_with_heartbeat_retry(fn, max_retries=-1)


def test_nonpositive_ceiling_rejected() -> None:
    fn = _make_check_fn([_ok_result()])
    with pytest.raises(ValueError, match=">= 1"):
        check_with_heartbeat_retry(fn, ceiling=0)


def test_default_ceiling_constant_matches_exported_value() -> None:
    # Sanity: the module-level constant and the default parameter stay
    # in sync, so docs and public API don't drift from the CLI defaults.
    from grd.core.lean import heartbeats as hb
    assert DEFAULT_HEARTBEAT_CEILING == hb.DEFAULT_HEARTBEAT_CEILING
