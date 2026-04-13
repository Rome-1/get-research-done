"""Tests for the Pantograph-backed Lean REPL dispatch.

The whole point of this module is REPL reuse: one ``pantograph.Server`` per
daemon, reused across every ``check`` request (cold ~3 s, reused ~50 ms).
These tests inject a fake ``pantograph`` module into ``sys.modules`` so we
can exercise the reuse contract without installing the real package.
"""

from __future__ import annotations

import importlib
import json
import socket
import sys
import threading
import time
import types
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from grd.core.lean import daemon as lean_daemon
from grd.core.lean import pantograph_backend as pb
from grd.core.lean.env import socket_path
from grd.core.lean.protocol import LeanCheckResult

# ---------------------------------------------------------------------------
# Fake pantograph module helpers.
# ---------------------------------------------------------------------------


@dataclass
class _FakeUnit:
    """Stand-in for pantograph's CompilationUnit."""

    messages: list[str] = field(default_factory=list)


def _install_fake_pantograph(
    monkeypatch: pytest.MonkeyPatch,
    *,
    init_hook=None,
    load_sorry_hook=None,
    close_hook=None,
) -> dict[str, int]:
    """Install a minimal ``pantograph`` module in ``sys.modules``.

    Returns a dict of counters so tests can assert "Server constructed N times".
    ``init_hook`` / ``load_sorry_hook`` / ``close_hook`` let individual tests
    override behaviour (e.g. raise, record arguments).
    """
    counters = {"init": 0, "load_sorry": 0, "close": 0}

    class FakeServer:
        def __init__(self, imports: list[str] | None = None, **kwargs: object) -> None:
            counters["init"] += 1
            self.imports = list(imports or [])
            if init_hook is not None:
                init_hook(self, counters)

        def load_sorry(self, code: str) -> list[_FakeUnit]:
            counters["load_sorry"] += 1
            if load_sorry_hook is not None:
                hooked = load_sorry_hook(code, counters)
                if hooked is not None:
                    return hooked
            return [_FakeUnit(messages=[])]

        def close(self) -> None:
            counters["close"] += 1
            if close_hook is not None:
                close_hook(counters)

    mod = types.ModuleType("pantograph")
    mod.Server = FakeServer  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pantograph", mod)
    # Force find_spec to succeed and import_module to return our fake.
    monkeypatch.setattr(pb, "pantograph_importable", lambda: True)

    # importlib.import_module caches in sys.modules, so our insertion above
    # is what ``PantographBackend._ensure_server`` will pick up.
    importlib.invalidate_caches()
    return counters


# ---------------------------------------------------------------------------
# PantographBackend unit behaviour.
# ---------------------------------------------------------------------------


class TestAvailabilityGating:
    def test_unavailable_when_import_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(pb, "pantograph_importable", lambda: False)
        backend = pb.PantographBackend()
        assert backend.available is False
        assert backend.run_check(code="theorem t : True := trivial") is None

    def test_available_when_fake_module_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _install_fake_pantograph(monkeypatch)
        backend = pb.PantographBackend()
        assert backend.available is True


class TestReplReuse:
    """The core contract of this bead: one Server across N requests."""

    def test_single_server_across_n_check_requests_via_handle_request(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        counters = _install_fake_pantograph(monkeypatch)
        backend = pb.PantographBackend()

        n = 7
        for _ in range(n):
            result = lean_daemon.handle_request(
                json.dumps({"op": "check", "code": "theorem t : True := trivial"}),
                pantograph_backend=backend,
            )
            assert isinstance(result, LeanCheckResult)
            assert result.ok is True
            assert result.backend == "pantograph"

        assert counters["init"] == 1, (
            f"Pantograph Server must be constructed once across {n} requests; "
            f"got {counters['init']} constructions (REPL reuse broken)."
        )
        assert counters["load_sorry"] == n

    def test_server_rebuilt_when_imports_change(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Lean imports are fixed at elaboration-env creation; mismatched
        imports force a rebuild. Reuse is still the rule for matching imports."""
        counters = _install_fake_pantograph(monkeypatch)
        backend = pb.PantographBackend()

        # Three calls with the same imports → one construction.
        for _ in range(3):
            backend.run_check(code="example : True := trivial", imports=["Mathlib.Tactic"])
        assert counters["init"] == 1
        # One call with different imports → second construction.
        backend.run_check(code="example : True := trivial", imports=["Mathlib.Data.Nat.Basic"])
        assert counters["init"] == 2
        # And the previous server got closed.
        assert counters["close"] == 1


class TestFallbackSemantics:
    def test_server_init_failure_disables_backend_permanently(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def _raise(_self: object, _counters: dict[str, int]) -> None:
            raise RuntimeError("toolchain missing")

        _install_fake_pantograph(monkeypatch, init_hook=_raise)
        backend = pb.PantographBackend()

        first = backend.run_check(code="theorem t : True := trivial")
        assert first is None
        assert backend.available is False
        # Subsequent calls short-circuit without reattempting the Server.
        second = backend.run_check(code="theorem t : True := trivial")
        assert second is None

    def test_load_sorry_failure_falls_back_once_but_keeps_backend_live(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        calls = {"n": 0}

        def _sometimes_raise(_code: str, _counters: dict[str, int]):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("REPL hiccup")
            return [_FakeUnit(messages=[])]

        counters = _install_fake_pantograph(monkeypatch, load_sorry_hook=_sometimes_raise)
        backend = pb.PantographBackend()

        first = backend.run_check(code="theorem t : True := trivial")
        assert first is None  # per-call fallback
        assert backend.available is True  # backend still usable

        second = backend.run_check(code="theorem t : True := trivial")
        assert second is not None
        assert second.backend == "pantograph"
        # The Server was constructed once — the failing call didn't tear it down.
        assert counters["init"] == 1

    def test_handle_request_falls_back_to_subprocess_when_backend_unavailable(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When pantograph can't run, the one-shot backend still answers.

        We stub ``lean_backend.run_check`` instead of running real Lean — this
        test cares about the dispatch wiring, not Lean itself.
        """
        from grd.core.lean import backend as lean_backend

        called: dict[str, bool] = {"ran": False}

        def fake_run_check(**kwargs: object) -> LeanCheckResult:
            called["ran"] = True
            return LeanCheckResult(ok=True, backend="subprocess")

        monkeypatch.setattr(lean_backend, "run_check", fake_run_check)
        monkeypatch.setattr(pb, "pantograph_importable", lambda: False)
        backend = pb.PantographBackend()  # permanently disabled

        result = lean_daemon.handle_request(
            json.dumps({"op": "check", "code": "theorem t : True := trivial"}),
            pantograph_backend=backend,
        )
        assert called["ran"] is True
        assert result.backend == "daemon"  # re-tagged by handle_request


class TestDiagnosticParsing:
    def test_error_message_surfaces_as_diagnostic(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _fake_error(_code: str, _counters: dict[str, int]):
            # Lean-style diagnostic header + indented continuation.
            return [_FakeUnit(messages=["test.lean:1:5: error: unknown identifier 'foo'"])]

        _install_fake_pantograph(monkeypatch, load_sorry_hook=_fake_error)
        backend = pb.PantographBackend()

        result = backend.run_check(code="theorem t : True := foo")
        assert result is not None
        assert result.ok is False
        assert any("unknown identifier" in d.message for d in result.diagnostics)
        assert result.backend == "pantograph"


# ---------------------------------------------------------------------------
# End-to-end: daemon loop actually reuses one Server across socket requests.
# ---------------------------------------------------------------------------


class TestDaemonEndToEnd:
    def _start(self, tmp_path: Path, backend: pb.PantographBackend) -> tuple[lean_daemon.LeanDaemon, threading.Thread]:
        (tmp_path / ".grd").mkdir(exist_ok=True)
        daemon = lean_daemon.LeanDaemon(
            project_root=tmp_path,
            idle_timeout_s=5.0,
            read_timeout_s=2.0,
            pantograph_backend=backend,
        )
        thread = threading.Thread(target=daemon.run, daemon=True)
        thread.start()
        sock = socket_path(tmp_path)
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            if sock.exists():
                probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                probe.settimeout(0.2)
                try:
                    probe.connect(str(sock))
                    probe.close()
                    return daemon, thread
                except OSError:
                    probe.close()
            time.sleep(0.02)
        raise AssertionError("daemon never bound its socket")

    def _send(self, tmp_path: Path, payload: dict) -> LeanCheckResult:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(3.0)
        s.connect(str(socket_path(tmp_path)))
        try:
            s.sendall((json.dumps(payload) + "\n").encode("utf-8"))
            buf = bytearray()
            while b"\n" not in buf:
                chunk = s.recv(4096)
                if not chunk:
                    break
                buf.extend(chunk)
            line = buf.split(b"\n", 1)[0].decode("utf-8")
            return LeanCheckResult.model_validate_json(line)
        finally:
            s.close()

    def test_real_daemon_reuses_one_server_across_n_socket_requests(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        counters = _install_fake_pantograph(monkeypatch)
        backend = pb.PantographBackend()
        daemon, thread = self._start(tmp_path, backend)
        try:
            n = 5
            for _ in range(n):
                result = self._send(
                    tmp_path,
                    {"op": "check", "code": "theorem t : True := trivial"},
                )
                assert result.ok is True
                assert result.backend == "pantograph"
            assert counters["init"] == 1, (
                f"REPL reuse broken: {counters['init']} Server constructions across {n} socket requests"
            )
            assert counters["load_sorry"] == n
            # Drive a clean shutdown via the wire op so the daemon's finally
            # block runs deterministically (select() won't wake from stop()).
            self._send(tmp_path, {"op": "shutdown"})
            thread.join(timeout=5)
            assert not thread.is_alive()
            # One persistent Server was torn down on daemon exit.
            assert counters["close"] == 1
        finally:
            daemon.stop()
            thread.join(timeout=5)
