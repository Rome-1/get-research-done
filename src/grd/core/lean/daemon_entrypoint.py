"""``python -m grd.core.lean.daemon_entrypoint`` — launch a Lean REPL daemon.

Thin wrapper that parses CLI flags and invokes ``daemon.serve``. Kept
separate from ``daemon.py`` so the main daemon module has no module-level
CLI side effects — import-only.

This is used by ``client.spawn_daemon`` to start the daemon detached from
the parent process. It is not a user-facing CLI command — ``grd lean
serve-repl`` is the supported front door.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from grd.core.lean.daemon import DEFAULT_IDLE_TIMEOUT_S, DEFAULT_READ_TIMEOUT_S, serve


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="grd-lean-daemon", add_help=True)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--idle-timeout", type=float, default=DEFAULT_IDLE_TIMEOUT_S)
    parser.add_argument("--read-timeout", type=float, default=DEFAULT_READ_TIMEOUT_S)
    args = parser.parse_args(argv)

    serve(
        args.project_root,
        idle_timeout_s=args.idle_timeout,
        read_timeout_s=args.read_timeout,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
