"""Bead-based human escalation for stage 6 ESCALATE / CLUSTER_CONSENSUS paths.

When the faithfulness gate can't accept a candidate, the pipeline files a
bead with ``-l human`` so the work surfaces in Rome's "needs you" queue. Per
AUTOFORMALIZATION.md §8.4 and the ge-48t bead: the escalation must surface
the *specific* ambiguity (e.g. "quantifier order uncertain between candidates
A/B"), not just "low similarity".

We shell out to ``bd create`` — the canonical beads CLI — rather than trying
to poke at the Dolt backend directly. That keeps us compatible with the same
workflows humans use and avoids coupling the formalization pipeline to the
beads database implementation.

``bd`` may not be on ``PATH`` (CI, docs builds, users without Gas Town).
We return a ``BeadEscalationResult`` that encodes the outcome instead of
raising; pipeline callers render it into the final JSON so the caller knows
the escalation was attempted even if it failed.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = [
    "BeadEscalationResult",
    "escalate_to_human",
]


@dataclass(frozen=True)
class BeadEscalationResult:
    """Outcome of a single ``bd create -l human`` call."""

    attempted: bool
    bead_id: str | None
    error: str | None = None
    title: str = ""
    command: tuple[str, ...] = ()


def escalate_to_human(
    *,
    title: str,
    body: str,
    project_root: Path | None = None,
    priority: int = 2,
    issue_type: str = "task",
    dry_run: bool = False,
) -> BeadEscalationResult:
    """File a ``bd create -l human`` bead describing the ambiguity.

    Returns a result with ``attempted=False`` when ``bd`` is missing — the
    pipeline still emits its JSON so downstream tooling (and the user) can see
    what would have been escalated. ``dry_run=True`` short-circuits the actual
    call for tests; it's ``False`` by default.
    """
    bd_bin = shutil.which("bd")
    if bd_bin is None:
        return BeadEscalationResult(
            attempted=False,
            bead_id=None,
            error="bd CLI not found on PATH; cannot file human-review bead",
            title=title,
        )

    cmd = (
        bd_bin,
        "create",
        "--title",
        title,
        "--description",
        body,
        "--type",
        issue_type,
        "--priority",
        str(priority),
        "-l",
        "human",
        "--json",
    )
    if dry_run:
        return BeadEscalationResult(attempted=False, bead_id=None, title=title, command=cmd)

    try:
        proc = subprocess.run(
            list(cmd),
            check=False,
            capture_output=True,
            text=True,
            timeout=30.0,
            cwd=str(project_root) if project_root else None,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return BeadEscalationResult(
            attempted=True,
            bead_id=None,
            error=f"bd create failed: {exc}",
            title=title,
            command=cmd,
        )

    if proc.returncode != 0:
        return BeadEscalationResult(
            attempted=True,
            bead_id=None,
            error=(f"bd create exited {proc.returncode}: {proc.stderr.strip() or proc.stdout.strip()}"),
            title=title,
            command=cmd,
        )

    bead_id = _extract_bead_id(proc.stdout)
    return BeadEscalationResult(
        attempted=True,
        bead_id=bead_id,
        error=None,
        title=title,
        command=cmd,
    )


def _extract_bead_id(stdout: str) -> str | None:
    """Pull the bead id out of ``bd create --json`` output.

    ``bd`` has two JSON shapes: a single object or a one-element list. We
    accept both and fall back to scanning the first token of the text output
    (useful when ``bd`` prints a confirmation line before the JSON).
    """
    if not stdout.strip():
        return None
    try:
        parsed = json.loads(stdout.strip())
    except json.JSONDecodeError:
        first = stdout.strip().split()[0]
        return first if first.startswith(("ge-", "bd-", "gt-")) else None

    if isinstance(parsed, dict):
        val = parsed.get("id") or parsed.get("bead_id")
        return str(val) if val else None
    if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
        val = parsed[0].get("id") or parsed[0].get("bead_id")
        return str(val) if val else None
    return None
