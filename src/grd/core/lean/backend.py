"""One-shot Lean subprocess backend.

Writes inline Lean source to a tempfile, runs ``lean <file>``, parses stderr
for diagnostics, returns a ``LeanCheckResult``. This is the straightforward
path that always works as long as ``lean`` is on ``PATH``.

The daemon (``daemon.py``) wraps this same function today. When Pantograph
REPL reuse lands (follow-up bead), the daemon will prefer the Pantograph path
and fall back here only when Pantograph is unavailable — the result schema
stays the same.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from grd.core.lean.protocol import LeanCheckResult, LeanDiagnostic

__all__ = [
    "run_check",
    "parse_diagnostics",
]


# Lean 4 prints messages like:
#     /tmp/abc.lean:3:12: error: unknown identifier 'foo'
# Multi-line diagnostics (e.g. "unsolved goals") have continuation lines
# indented with leading whitespace — we accumulate those into ``message``.
_DIAG_HEAD = re.compile(
    r"^(?P<file>[^:\n]+):(?P<line>\d+):(?P<col>\d+):\s*"
    r"(?P<severity>error|warning|info):\s*(?P<msg>.*)$"
)


def parse_diagnostics(text: str) -> list[LeanDiagnostic]:
    """Parse Lean's stderr/stdout into structured diagnostics.

    Lean emits one header line per diagnostic followed by indented
    continuation lines. Any line that doesn't match the header and isn't a
    continuation (not indented, not empty) is ignored — Lean occasionally
    prints banners or env warnings we don't need to surface as diagnostics.
    """
    diags: list[LeanDiagnostic] = []
    current: dict[str, object] | None = None
    buf: list[str] = []

    def _flush() -> None:
        if current is None:
            return
        msg = current["msg"]
        if buf:
            msg = str(msg) + "\n" + "\n".join(buf)
        diags.append(
            LeanDiagnostic(
                severity=current["severity"],  # type: ignore[arg-type]
                file=current["file"],  # type: ignore[arg-type]
                line=current["line"],  # type: ignore[arg-type]
                column=current["column"],  # type: ignore[arg-type]
                message=str(msg).rstrip(),
            )
        )

    for raw_line in text.splitlines():
        m = _DIAG_HEAD.match(raw_line)
        if m:
            _flush()
            current = {
                "severity": m["severity"],
                "file": m["file"],
                "line": int(m["line"]),
                "column": int(m["col"]),
                "msg": m["msg"],
            }
            buf = []
            continue
        if current is not None and (raw_line.startswith((" ", "\t")) or raw_line == ""):
            buf.append(raw_line)
            continue
        # Line doesn't belong to a diagnostic — close the current one.
        if current is not None:
            _flush()
            current = None
            buf = []

    _flush()
    return diags


def _resolve_lean_binary(lean_path: str | None) -> str | None:
    """Return an absolute path to the Lean binary, or None if missing."""
    if lean_path:
        candidate = Path(lean_path)
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
        resolved = shutil.which(lean_path)
        if resolved:
            return resolved
        return None
    return shutil.which("lean")


def run_check(
    *,
    code: str | None = None,
    path: str | None = None,
    imports: list[str] | None = None,
    timeout_s: float = 30.0,
    lean_path: str | None = None,
    cwd: Path | None = None,
) -> LeanCheckResult:
    """Type-check a Lean source (inline or file) via a one-shot subprocess.

    Exactly one of ``code`` / ``path`` must be set. For inline ``code``, the
    text is written to a private tempfile and removed after the run. For
    ``path``, the file is passed directly (no copy), so callers keep control
    of the on-disk source.
    """
    if (code is None) == (path is None):
        return LeanCheckResult(
            ok=False,
            error="invalid_request",
            error_detail="Provide exactly one of 'code' or 'path'.",
        )

    binary = _resolve_lean_binary(lean_path)
    if binary is None:
        return LeanCheckResult(
            ok=False,
            error="lean_not_found",
            error_detail=(
                "No 'lean' binary found on PATH. Run /grd:lean-bootstrap to "
                "install the Lean toolchain, or set GRD_LEAN_BIN to a lean "
                "executable."
            ),
        )

    imports = imports or []
    tempfile_to_cleanup: Path | None = None

    if code is not None:
        prelude = "\n".join(f"import {m}" for m in imports)
        src = (prelude + "\n" if prelude else "") + code
        fd, tmp_name = tempfile.mkstemp(suffix=".lean", prefix="grd_lean_check_")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(src)
        except Exception:
            os.close(fd)
            raise
        target_path = tmp_name
        tempfile_to_cleanup = Path(tmp_name)
    else:
        target_path = str(Path(path).resolve())  # type: ignore[arg-type]
        if not Path(target_path).is_file():
            return LeanCheckResult(
                ok=False,
                error="io_error",
                error_detail=f"File not found: {target_path}",
            )

    start = time.monotonic()
    stdout = ""
    stderr = ""
    exit_code: int | None = None
    error_kind = None
    error_detail: str | None = None

    try:
        proc = subprocess.run(
            [binary, target_path],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            cwd=str(cwd) if cwd is not None else None,
            check=False,
        )
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        exit_code = proc.returncode
    except subprocess.TimeoutExpired as exc:
        error_kind = "timeout"
        error_detail = f"Lean exceeded timeout of {timeout_s}s"
        stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
    except FileNotFoundError as exc:
        error_kind = "lean_not_found"
        error_detail = str(exc)
    except OSError as exc:
        error_kind = "io_error"
        error_detail = str(exc)
    finally:
        if tempfile_to_cleanup is not None:
            try:
                tempfile_to_cleanup.unlink(missing_ok=True)
            except OSError:
                pass

    elapsed_ms = int((time.monotonic() - start) * 1000)

    diagnostics = parse_diagnostics(stderr) + parse_diagnostics(stdout)
    has_error_diag = any(d.severity == "error" for d in diagnostics)

    if error_kind is not None:
        ok = False
    else:
        ok = exit_code == 0 and not has_error_diag

    return LeanCheckResult(
        ok=ok,
        diagnostics=diagnostics,
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        elapsed_ms=elapsed_ms,
        error=error_kind,
        error_detail=error_detail,
        backend="subprocess",
    )
