"""Progress-event protocol for long-running Lean operations.

Defines NDJSON-safe event models emitted by ``bootstrap``, ``prove``,
``verify-claim``, and ``check`` during execution. The CLI layer decides
how to render them: NDJSON to stdout (``--events jsonl``), a compact TTY
status line, or silently (``--raw`` / default).

Events are Pydantic models so they serialise cleanly via ``.model_dump()``.
The ``EventCallback`` type alias is the only coupling between core and CLI:
core functions accept ``on_event: EventCallback = None`` and call it; the
CLI binds the callback to a renderer before invoking the core function.
"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable
from typing import Literal, Union

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "DiagnosticEmitted",
    "EventCallback",
    "ProgressEvent",
    "StageCompleted",
    "StageStarted",
    "TacticAttempted",
    "jsonl_emitter",
    "noop_emitter",
    "tty_emitter",
]


def _now_ms() -> int:
    return int(time.monotonic() * 1000)


# ---------------------------------------------------------------------------
# Event models
# ---------------------------------------------------------------------------


class StageStarted(BaseModel):
    """A named stage has begun execution."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["stage_started"] = "stage_started"
    ts: int = Field(default_factory=_now_ms)
    stage: str
    detail: str = ""


class StageCompleted(BaseModel):
    """A named stage finished (any outcome)."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["stage_completed"] = "stage_completed"
    ts: int = Field(default_factory=_now_ms)
    stage: str
    status: str  # ok, failed, skipped_already_installed, degraded, etc.
    elapsed_ms: int = 0
    detail: str = ""


class TacticAttempted(BaseModel):
    """One tactic candidate was tried during a proof search."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["tactic_attempted"] = "tactic_attempted"
    ts: int = Field(default_factory=_now_ms)
    tactic: str
    index: int
    total: int
    ok: bool
    elapsed_ms: int = 0


class DiagnosticEmitted(BaseModel):
    """A Lean diagnostic surfaced during type-checking."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["diagnostic_emitted"] = "diagnostic_emitted"
    ts: int = Field(default_factory=_now_ms)
    severity: str
    message: str
    line: int | None = None
    column: int | None = None


ProgressEvent = Union[StageStarted, StageCompleted, TacticAttempted, DiagnosticEmitted]
"""Discriminated union of all progress events."""

EventCallback = Callable[[ProgressEvent], None] | None
"""Optional callback that core functions invoke on each progress tick."""


# ---------------------------------------------------------------------------
# Built-in emitters
# ---------------------------------------------------------------------------


def noop_emitter(event: ProgressEvent) -> None:  # noqa: ARG001
    """Silently discard events."""


def jsonl_emitter(event: ProgressEvent) -> None:
    """Write one JSON line per event to stdout and flush immediately."""
    import json  # noqa: PLC0415

    line = json.dumps(event.model_dump(mode="json"), separators=(",", ":"))
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def tty_emitter(event: ProgressEvent) -> None:
    """Render a compact, in-place status line on stderr.

    Only meaningful when stderr is a TTY — the caller should fall back to
    ``noop_emitter`` otherwise. Uses ``\\r`` to overwrite the previous line
    so long-running operations show a single updating status rather than
    flooding the terminal.
    """
    if isinstance(event, StageStarted):
        _tty_write(f"  [{event.stage}] starting…")
    elif isinstance(event, StageCompleted):
        icon = "OK" if event.status == "ok" else event.status[:6]
        ms = f" ({event.elapsed_ms}ms)" if event.elapsed_ms else ""
        _tty_write(f"  [{event.stage}] {icon}{ms}")
    elif isinstance(event, TacticAttempted):
        result = "pass" if event.ok else "fail"
        _tty_write(f"  tactic {event.index + 1}/{event.total} {event.tactic}: {result}")
    elif isinstance(event, DiagnosticEmitted):
        loc = f":{event.line}" if event.line else ""
        _tty_write(f"  {event.severity}{loc}: {event.message[:80]}")


def _tty_write(text: str) -> None:
    """Overwrite the current stderr line with *text*."""
    cols = 80
    try:
        import shutil  # noqa: PLC0415

        cols = shutil.get_terminal_size((80, 24)).columns
    except Exception:  # noqa: BLE001
        pass
    truncated = text[:cols - 1]
    sys.stderr.write(f"\r{truncated:<{cols - 1}}")
    sys.stderr.flush()


def tty_finish() -> None:
    """Clear the status line after a TTY-emitted operation completes."""
    cols = 80
    try:
        import shutil  # noqa: PLC0415

        cols = shutil.get_terminal_size((80, 24)).columns
    except Exception:  # noqa: BLE001
        pass
    sys.stderr.write(f"\r{' ' * (cols - 1)}\r")
    sys.stderr.flush()
