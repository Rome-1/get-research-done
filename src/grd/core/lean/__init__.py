"""Lean 4 verification backend for GRD.

Layered design (each layer importable on its own):

    protocol.py   — wire-format dataclasses (LeanCheckRequest, LeanCheckResult,
                    LeanDiagnostic). No Lean or filesystem dependency.
    env.py        — detect the Lean toolchain on the host, read/write
                    ``.grd/lean-env.json``.
    backend.py    — one-shot Lean subprocess execution (``lean <tempfile>``).
                    This is the worker used by both the direct client path and
                    the socket daemon.
    daemon.py     — Unix-socket daemon. JSON-line protocol. Idle timeout.
                    Currently dispatches every request to the one-shot backend;
                    structured so a Pantograph-backed persistent REPL can be
                    swapped in without changing the wire protocol.
    client.py     — high-level ``check(...)`` entrypoint used by the CLI.
                    Prefers the daemon socket (auto-spawning if absent); falls
                    back to the one-shot backend when the daemon is unavailable
                    or the caller passes ``use_daemon=False``.

Why no MCP? The ``grd-lean`` feature is opt-in: most phases never touch formal
proofs. An MCP server's tool schemas are injected into every agent turn
regardless, which would tax every project for a feature most don't use. The
CLI + lazy skill surface keeps the context tax at zero for non-formal phases.
See ``research/formal-proof-integration/PITCH.md`` §Architecture Design.
"""

from __future__ import annotations

from grd.core.lean.evidence import (
    LEAN_METHOD_TYPECHECK,
    LEAN_VERIFIER,
    lean_result_to_evidence,
)
from grd.core.lean.protocol import (
    LeanCheckRequest,
    LeanCheckResult,
    LeanDiagnostic,
    LeanEnvStatus,
)

__all__ = [
    "LEAN_METHOD_TYPECHECK",
    "LEAN_VERIFIER",
    "LeanCheckRequest",
    "LeanCheckResult",
    "LeanDiagnostic",
    "LeanEnvStatus",
    "lean_result_to_evidence",
]
