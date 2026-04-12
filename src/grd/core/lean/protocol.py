"""Wire-format models for the Lean backend.

Shared by the one-shot subprocess runner, the Unix-socket daemon, the
high-level client, and the CLI. Pure Pydantic — no filesystem or subprocess
dependencies, so these can be imported cheaply and used in tests.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
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


class LeanEnvStatus(BaseModel):
    """Snapshot of the host's Lean toolchain + daemon state."""

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
