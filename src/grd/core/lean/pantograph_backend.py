"""Pantograph-backed persistent REPL for the Lean daemon.

The one-shot ``backend.run_check`` pays ~3 s per call for Lean cold-start.
Pantograph (``pip install pantograph``) wraps a long-lived Lean 4 process
and talks to it via a JSON REPL, so subsequent elaborations cost ~50 ms.
This module holds one ``pantograph.Server`` instance per daemon and reuses
it across every ``check`` request.

Fallback policy: when ``pantograph`` isn't importable, when constructing
the ``Server`` raises, or when a single ``load_sorry`` call raises, the
backend returns ``None`` so the daemon can dispatch that request (and all
future requests, in the permanent-failure cases) to the one-shot subprocess
path.  The wire protocol and ``LeanCheckResult`` shape are unchanged — this
is a pure latency optimisation.
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import time
from typing import TYPE_CHECKING

from grd.core.lean.backend import parse_diagnostics
from grd.core.lean.protocol import LeanCheckResult

if TYPE_CHECKING:
    from collections.abc import Iterable

__all__ = ["PantographBackend", "pantograph_importable"]

logger = logging.getLogger("grd.lean.pantograph")


def pantograph_importable() -> bool:
    """Return True iff the ``pantograph`` Python package can be imported."""
    try:
        return importlib.util.find_spec("pantograph") is not None
    except (ImportError, ValueError):
        return False


class PantographBackend:
    """Lazy wrapper around ``pantograph.Server`` with REPL reuse.

    One ``Server`` is constructed on the first ``run_check`` call and reused
    for every subsequent call — this is the whole point of the daemon.  If
    the imports set changes across calls, the current ``Server`` is closed and
    a fresh one is constructed (Lean 4 imports are fixed at elaboration-env
    creation time), which still beats the one-shot path amortised across
    subsequent calls with the same imports.

    The backend is resilient: any construction or ``load_sorry`` failure is
    caught and surfaced as ``None`` from ``run_check`` so the daemon falls
    back to the subprocess path rather than losing the ability to check.
    """

    def __init__(self) -> None:
        self._server: object | None = None
        self._server_imports: tuple[str, ...] | None = None
        self._permanently_disabled: bool = not pantograph_importable()

    @property
    def available(self) -> bool:
        """Whether this backend may handle requests. Monotonically non-increasing."""
        return not self._permanently_disabled

    def close(self) -> None:
        """Tear down the underlying ``Server`` if one is live."""
        server = self._server
        self._server = None
        self._server_imports = None
        if server is None:
            return
        close_fn = getattr(server, "close", None)
        if callable(close_fn):
            try:
                close_fn()
            except Exception:  # pragma: no cover — best-effort cleanup
                logger.debug("Pantograph Server.close raised", exc_info=True)

    def _ensure_server(self, imports: tuple[str, ...]) -> object | None:
        if self._permanently_disabled:
            return None
        if self._server is not None and self._server_imports == imports:
            return self._server
        # Imports changed (or no server yet) — rebuild with the new set so
        # Lean's elaboration env sees the right modules.
        if self._server is not None:
            self.close()
        try:
            pantograph = importlib.import_module("pantograph")
            server_cls = pantograph.Server
            self._server = server_cls(imports=list(imports)) if imports else server_cls()
            self._server_imports = imports
        except Exception as exc:
            # A failing Server init is usually structural (bad toolchain,
            # missing deps) and unlikely to recover within this daemon's
            # lifetime — disable permanently so we don't thrash on every
            # request.
            logger.warning("Pantograph Server init failed; disabling backend: %s", exc)
            self._permanently_disabled = True
            self._server = None
            self._server_imports = None
            return None
        return self._server

    def run_check(
        self,
        *,
        code: str,
        imports: Iterable[str] | None = None,
    ) -> LeanCheckResult | None:
        """Elaborate ``code`` via the reused ``Server``. Returns ``None`` on fallback."""
        if self._permanently_disabled:
            return None

        imports_tuple: tuple[str, ...] = tuple(imports or ())
        server = self._ensure_server(imports_tuple)
        if server is None:
            return None

        start = time.monotonic()
        try:
            units = server.load_sorry(code)
        except Exception as exc:
            # Single-request failure: don't disable the backend (the REPL may
            # still be usable for other inputs), just fall back for this call.
            logger.warning("Pantograph load_sorry raised; falling back: %s", exc)
            return None
        elapsed_ms = int((time.monotonic() - start) * 1000)

        messages: list[str] = []
        for unit in units or []:
            unit_msgs = getattr(unit, "messages", None) or ()
            for m in unit_msgs:
                messages.append(str(m))
        stderr = "\n".join(messages)
        diagnostics = parse_diagnostics(stderr)
        has_error_diag = any(d.severity == "error" for d in diagnostics)

        return LeanCheckResult(
            ok=not has_error_diag,
            diagnostics=diagnostics,
            stdout="",
            stderr=stderr,
            exit_code=0 if not has_error_diag else 1,
            elapsed_ms=elapsed_ms,
            backend="pantograph",
        )
