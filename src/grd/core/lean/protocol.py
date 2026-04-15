"""Wire-format models for the Lean backend.

Shared by the one-shot subprocess runner, the Unix-socket daemon, the
high-level client, and the CLI. Pure Pydantic — no filesystem or subprocess
dependencies, so these can be imported cheaply and used in tests.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "BootstrapReport",
    "BootstrapStageResult",
    "BootstrapStageStatus",
    "LeanCheckRequest",
    "LeanCheckResult",
    "LeanDiagnostic",
    "LeanEnvStatus",
    "LeanErrorKind",
]


LeanErrorKind = Literal[
    "lean_not_found",
    "timeout",
    "daemon_unavailable",
    "invalid_request",
    "io_error",
    "internal_error",
]
"""Machine-readable error taxonomy for failures *other* than Lean diagnostics.

A successful Lean run with elaboration errors has ``ok=False`` but
``error=None`` — the diagnostics array carries the per-line messages. The
``error`` field is reserved for orchestration failures (Lean missing, daemon
crashed, request malformed, etc.) that callers may want to route differently.
"""


DiagnosticSeverity = Literal["error", "warning", "info"]


class LeanDiagnostic(BaseModel):
    """One message parsed from Lean's output.

    Locations are 1-indexed to match Lean's own output and editor convention.
    ``file`` is the path Lean printed (typically the tempfile), not the
    logical source the caller supplied.
    """

    model_config = ConfigDict(extra="forbid")

    severity: DiagnosticSeverity
    file: str | None = None
    line: int | None = None
    column: int | None = None
    message: str
    hint: str | None = Field(
        default=None,
        description=(
            "Human-readable explanation of this Lean message plus a concrete "
            "next step, populated by the error-explanation layer. None when "
            "the message isn't recognized by any known pattern. Contract: one "
            "line, cause + suggested action, no Lean jargon without a gloss."
        ),
    )


class LeanCheckRequest(BaseModel):
    """Single type-check request passed to the backend or over the socket."""

    model_config = ConfigDict(extra="forbid")

    op: Literal["check", "typecheck_file", "ping", "shutdown"] = "check"
    code: str | None = Field(
        default=None,
        description="Inline Lean 4 source to elaborate. Ignored for 'typecheck_file'.",
    )
    path: str | None = Field(
        default=None,
        description="Absolute path to a .lean file to elaborate. Required for 'typecheck_file'.",
    )
    imports: list[str] = Field(
        default_factory=list,
        description="Module names to prepend as 'import <name>' lines (e.g. ['Mathlib.Tactic']).",
    )
    timeout_s: float = Field(
        default=30.0,
        ge=0.1,
        le=600.0,
        description="Hard wall-clock timeout for the Lean subprocess.",
    )


class LeanCheckResult(BaseModel):
    """Outcome of a single Lean run.

    ``ok`` is True only when Lean exited cleanly with no error-severity
    diagnostics. A successful compile with warnings is still ``ok=True``.
    ``error`` is populated only for orchestration failures; Lean's own
    elaboration errors live in ``diagnostics``.
    """

    model_config = ConfigDict(extra="forbid")

    ok: bool
    diagnostics: list[LeanDiagnostic] = Field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    elapsed_ms: int = 0
    error: LeanErrorKind | None = None
    error_detail: str | None = None
    backend: Literal["subprocess", "daemon", "pantograph"] = "subprocess"


BootstrapStageStatus = Literal[
    "ok",
    "skipped_already_installed",
    "skipped_user_declined",
    "skipped_not_requested",
    "degraded",
    "failed",
]
"""Outcome of a single bootstrap stage.

``ok`` means we actually ran the installer and it succeeded.
``skipped_already_installed`` means detection found the component in place.
``skipped_user_declined`` means a stage requiring consent was answered "no"
(remembered in ``.grd/lean-env.json`` so we don't re-ask).
``skipped_not_requested`` means an optional stage wasn't enabled by the caller
(e.g. ``--with-graphviz`` not passed).
``degraded`` means the stage can't install cleanly but the surrounding
workflow can proceed with reduced functionality — the canonical example is
graphviz needing root on a non-user-package-manager host.
``failed`` means an unexpected error; the report is saved with diagnostic detail
but the overall bootstrap continues so later stages still get a chance.
"""


class BootstrapStageResult(BaseModel):
    """Structured outcome of one stage in ``/grd:lean-bootstrap``."""

    model_config = ConfigDict(extra="forbid")

    name: str
    status: BootstrapStageStatus
    detail: str = ""
    elapsed_ms: int = 0
    version: str | None = None
    path: str | None = None


class BootstrapReport(BaseModel):
    """Aggregate result of a bootstrap run written to ``.grd/lean-env.json``."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    stages: list[BootstrapStageResult] = Field(default_factory=list)
    env_file: str
    elapsed_ms: int = 0
    degraded_notes: list[str] = Field(default_factory=list)


class LeanEnvStatus(BaseModel):
    """Snapshot of the host's Lean toolchain + daemon state.

    ``ready`` is a synthesized verdict: True iff every component required to
    run ``grd lean check`` / ``prove`` / ``verify-claim`` is in place. When
    False, ``blocked_by`` enumerates the missing components so callers (agents
    in particular) can branch without re-implementing the check. Daemon state
    is reported separately in ``daemon_running`` and deliberately does NOT
    feed into ``ready`` — the client auto-spawns a daemon on first request
    when the toolchain is available, so a stopped daemon is not a blocker.
    """

    model_config = ConfigDict(extra="forbid")

    lean_found: bool
    lean_path: str | None = None
    lean_version: str | None = None
    elan_found: bool = False
    elan_version: str | None = None
    lake_found: bool = False
    lake_version: str | None = None
    pantograph_available: bool = False
    env_file: str | None = None
    env_file_exists: bool = False
    socket_path: str | None = None
    daemon_running: bool = False
    daemon_pid: int | None = None
    ready: bool = False
    blocked_by: list[str] = Field(default_factory=list)
