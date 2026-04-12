"""Detect the Lean toolchain and manage ``.grd/lean-env.json``.

``lean-env.json`` is the crash-safe, resumable record of which bootstrap
stages have completed (elan installed, toolchain pinned, pantograph installed,
optional Mathlib cache downloaded, etc.). This module handles only reading,
writing, and toolchain detection — the bootstrap logic itself (running the
installers) lives in the ``/grd:lean-bootstrap`` skill (bead ``ge-x7l``).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from grd.core.constants import PLANNING_DIR_NAME
from grd.core.lean.protocol import LeanEnvStatus

__all__ = [
    "LEAN_ENV_FILENAME",
    "LEAN_SOCKET_FILENAME",
    "LEAN_PID_FILENAME",
    "ToolchainInfo",
    "detect_toolchain",
    "env_file_path",
    "socket_path",
    "pid_file_path",
    "load_env",
    "save_env",
    "compute_env_status",
    "pantograph_available",
]


LEAN_ENV_FILENAME = "lean-env.json"
LEAN_SOCKET_FILENAME = "lean-repl.sock"
LEAN_PID_FILENAME = "lean-repl.pid"


@dataclass(frozen=True)
class ToolchainInfo:
    """Result of inspecting the host for a Lean 4 toolchain."""

    lean_path: str | None
    lean_version: str | None
    elan_path: str | None
    elan_version: str | None
    lake_path: str | None
    lake_version: str | None

    @property
    def lean_found(self) -> bool:
        return self.lean_path is not None


def env_file_path(project_root: Path) -> Path:
    """Return the path to ``.grd/lean-env.json`` for the project."""
    return project_root / PLANNING_DIR_NAME / LEAN_ENV_FILENAME


def socket_path(project_root: Path) -> Path:
    """Return the path to the per-project Lean REPL daemon socket.

    Unix-domain socket paths have a 108-byte limit on Linux and 104 on macOS.
    If the natural ``<project>/.grd/lean-repl.sock`` exceeds that, callers
    should fall back to the one-shot backend — we do not silently truncate.
    """
    return project_root / PLANNING_DIR_NAME / LEAN_SOCKET_FILENAME


def pid_file_path(project_root: Path) -> Path:
    return project_root / PLANNING_DIR_NAME / LEAN_PID_FILENAME


def _run_version(cmd: list[str], timeout: float = 2.0) -> str | None:
    """Run a ``<tool> --version`` style command, return stripped stdout or None.

    Failures (missing binary, nonzero exit, timeout, weird encoding) all
    collapse to ``None`` — callers just want to know "did it work."
    """
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    out = (proc.stdout or proc.stderr).strip()
    return out or None


def detect_toolchain(*, env: dict[str, str] | None = None) -> ToolchainInfo:
    """Probe ``PATH`` for lean / elan / lake.

    ``env`` overrides ``os.environ`` for testing. Detection is pure-read: no
    installation, no prompting. Versions are captured verbatim (Lean prints
    a multi-line banner; the full string is stored so callers can show it)."""
    path_env = (env or os.environ).get("PATH", os.defpath)
    lean = shutil.which("lean", path=path_env)
    elan = shutil.which("elan", path=path_env)
    lake = shutil.which("lake", path=path_env)
    return ToolchainInfo(
        lean_path=lean,
        lean_version=_run_version([lean, "--version"]) if lean else None,
        elan_path=elan,
        elan_version=_run_version([elan, "--version"]) if elan else None,
        lake_path=lake,
        lake_version=_run_version([lake, "--version"]) if lake else None,
    )


def pantograph_available() -> bool:
    """Return True iff the ``pantograph`` Python package is importable.

    Import-time is O(low-ms) so we probe rather than maintain a cached flag.
    Pantograph is an optional dependency — its absence just means the daemon
    falls back to one-shot subprocess execution.
    """
    try:
        import importlib.util

        spec = importlib.util.find_spec("pantograph")
        return spec is not None
    except (ImportError, ValueError):
        return False


def load_env(project_root: Path) -> dict[str, object]:
    """Read ``.grd/lean-env.json`` if it exists, else return an empty dict.

    Malformed JSON is treated as absent — we never crash callers over a
    corrupted bootstrap record. The bootstrap skill is responsible for
    detecting staleness and rewriting.
    """
    path = env_file_path(project_root)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_env(project_root: Path, data: dict[str, object]) -> None:
    """Atomically write ``.grd/lean-env.json``.

    Creates ``.grd/`` if missing (matches how ``/grd:lean-bootstrap`` is
    expected to behave on fresh projects). Uses a ``.tmp`` sibling + ``rename``
    so readers never see a half-written file.
    """
    path = env_file_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def _read_daemon_pid(project_root: Path) -> int | None:
    pid_file = pid_file_path(project_root)
    if not pid_file.exists():
        return None
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None
    return pid if pid > 0 else None


def _pid_alive(pid: int) -> bool:
    """Return True if a process with ``pid`` exists (POSIX semantics)."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but is owned by someone else.
        return True
    except OSError:
        return False
    return True


def compute_env_status(project_root: Path) -> LeanEnvStatus:
    """Build the ``grd lean env`` / status response from live host state."""
    tc = detect_toolchain()
    env_path = env_file_path(project_root)
    sock = socket_path(project_root)
    pid = _read_daemon_pid(project_root)
    daemon_running = pid is not None and _pid_alive(pid) and sock.exists()
    return LeanEnvStatus(
        lean_found=tc.lean_found,
        lean_path=tc.lean_path,
        lean_version=tc.lean_version,
        elan_found=tc.elan_path is not None,
        elan_version=tc.elan_version,
        lake_found=tc.lake_path is not None,
        lake_version=tc.lake_version,
        pantograph_available=pantograph_available(),
        env_file=str(env_path),
        env_file_exists=env_path.exists(),
        socket_path=str(sock),
        daemon_running=daemon_running,
        daemon_pid=pid if daemon_running else None,
    )
