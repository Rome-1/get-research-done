"""``grd lean demo`` — single-entry physicist demo path (ge-e2c1 / P1).

Rome-persona cold re-onboarding. Runs the MATHEMATICIAN-WORKFLOWS §7
transcript end-to-end against the ``simple-mechanics`` template:

    $ grd new-project demo-sho --domain physics --template simple-mechanics
    $ /grd:lean-bootstrap --for physicist
    $ /grd:progress
    $ /grd:verify-claim --phase 1 --claim derived-energy-conservation
    $ /grd:progress
    # → Blueprint URL

The demo is a scripted transcript: each stage is either REAL (runs live),
MOCK (emits a fixture — dependency ships, but the §7 output is expected-state
not live-state), or SKIPPED (long-running / LLM-backed — command printed,
not executed). The label is always shown inline so the viewer can see at
a glance which parts of the narrative are live.

Contract (from ge-e2c1):
  (a) screen-shareable
  (b) completes in <5 min wall
  (c) ``--dry-run`` labels every stage that is still mocked / skipped
  (d) only flags are ``--dry-run`` and ``--template``

Without ``--dry-run`` the only live side effect is stamping the template
into a disposable subdirectory under ``.grd/demo/<template>/``. Everything
else is labeled MOCK or SKIPPED so the demo never blows the 5-min budget
or silently pretends to have run a pipeline it didn't.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from grd.core.constants import PLANNING_DIR_NAME
from grd.core.templates import StampResult, get_project_template, stamp_project_template

__all__ = [
    "DEFAULT_TEMPLATE",
    "DemoResult",
    "DemoStage",
    "StageStatus",
    "run_demo",
]


DEFAULT_TEMPLATE = "simple-mechanics"
"""Canonical physicist-demo template (ge-bqdt)."""


StageStatus = Literal["real", "mock", "skipped"]
"""Honest status label for a demo stage.

``real``
    Ran live in this process. Narration reflects real output.
``mock``
    Dependency has shipped, but this stage emits a fixture transcript —
    the §7 narrative is the expected-state output, not live state.
    Used for the ``/grd:progress`` snapshots whose tier-phase wiring is
    still being filled in.
``skipped``
    Long-running or LLM-backed. Command is printed but not executed so
    the demo stays under 5 min. Run manually for the live experience.
"""


@dataclass(frozen=True)
class DemoStage:
    """One stage of the §7 transcript.

    ``command`` is the user-visible shell / skill invocation that the stage
    represents (e.g. ``/grd:verify-claim --phase 1 --claim …``). ``status``
    is the honesty label; ``narration`` is the multi-line transcript body
    that gets printed under the command. ``shipped_in`` names the bead
    that retired the dependency (so readers can trace the status).
    ``note`` carries an extra line the CLI prints right after the stage —
    typically the reason for MOCK/SKIPPED or the next-action to run live.
    """

    name: str
    command: str
    status: StageStatus
    narration: str
    shipped_in: str | None = None
    note: str | None = None
    duration_ms: int = 0


@dataclass(frozen=True)
class DemoResult:
    """Aggregate transcript + metadata for a ``grd lean demo`` run."""

    template: str
    dry_run: bool
    stages: list[DemoStage] = field(default_factory=list)
    project_dir: str | None = None
    stamp_result: StampResult | None = None
    duration_ms: int = 0
    warnings: list[str] = field(default_factory=list)


# ─── §7 fixture transcripts ─────────────────────────────────────────────────
#
# These are the expected-state outputs lifted from
# research/formal-proof-integration/MATHEMATICIAN-WORKFLOWS.md §7. Kept as
# fixtures so the demo narrative stays identical to the published demo even
# when the underlying pipeline hasn't yet wired a stage end-to-end. If you
# update §7, update these too.

_PROGRESS_PRE = """\
   Phase 1: derived-energy-conservation
     [✓] Tier 1: dimensional check
     [✓] Tier 2: limit ω→0 (free particle) recovered
     [✓] Tier 4: symmetry under time translation
     [ ] Tier 5: formal proof              ← available
"""

_VERIFY_CLAIM = """\
   ▸ Convention preamble: imported SI units + Mechanics.Hamiltonian
   ▸ Skeleton:
       theorem energy_conserved (m ω : ℝ) (hm : 0 < m) (hω : 0 < ω) :
         ∀ t, H q(t) p(t) = H q(0) p(0) := by sorry
   ▸ Faithfulness: ACCEPT (domain ℝ matches; hypotheses match; conclusion quantifier matches)
   ▸ Proof search: closed by `symm_energy_conservation` composed with `time_translation_symmetry`
   ✓ Verified in 4.1 s.
"""

_PROGRESS_POST = """\
   Phase 1: derived-energy-conservation
     [✓] Tier 1 … Tier 5 (Lean, 4.1 s)
   Blueprint: https://rome-1.github.io/demo-sho/blueprint/  ← \\leanok on energy_conserved
"""


# ─── Stage builders ─────────────────────────────────────────────────────────


def _stage_new_project(
    project_dir: Path,
    template: str,
    *,
    dry_run: bool,
) -> tuple[DemoStage, StampResult | None]:
    """Stage 1: stamp the template. REAL unless --dry-run."""
    started = time.monotonic()
    command = f"grd init new-project --template {template}"
    if dry_run:
        narration = f"   (would stamp template {template!r} into {project_dir}/{PLANNING_DIR_NAME}/)"
        return (
            DemoStage(
                name="new-project",
                command=command,
                status="mock",
                narration=narration,
                shipped_in="ge-bqdt",
                note="--dry-run: no filesystem writes.",
                duration_ms=int((time.monotonic() - started) * 1000),
            ),
            None,
        )

    project_dir.mkdir(parents=True, exist_ok=True)
    stamp = stamp_project_template(project_dir, template, force=True)
    planning_rel = Path(stamp.planning_dir).name
    written = "\n".join(f"   ✓ {planning_rel}/{f}" for f in stamp.files_written)
    narration = f"   → project root: {project_dir}\n{written}"
    return (
        DemoStage(
            name="new-project",
            command=command,
            status="real",
            narration=narration,
            shipped_in="ge-bqdt",
            duration_ms=int((time.monotonic() - started) * 1000),
        ),
        stamp,
    )


def _stage_bootstrap(*, dry_run: bool) -> DemoStage:
    """Stage 2: bootstrap — SKIPPED (installer; well outside a 5-min demo)."""
    narration = (
        "   (elan + Lean toolchain + Pantograph + Mathlib cache; persona: physicist)\n"
        "   (installer is always side-effectful — run manually the first time;\n"
        "    subsequent demos re-use the installed toolchain.)"
    )
    note = "Run manually: `grd lean bootstrap --for physicist --yes`"
    return DemoStage(
        name="lean-bootstrap",
        command="/grd:lean-bootstrap --for physicist",
        status="skipped",
        narration=narration,
        shipped_in="ge-5o8",
        note=note,
    )


def _stage_progress_pre(*, dry_run: bool) -> DemoStage:
    """Stage 3: /grd:progress snapshot before verify-claim."""
    return DemoStage(
        name="progress-pre",
        command="/grd:progress",
        status="mock",
        narration=_PROGRESS_PRE.rstrip(),
        note="Fixture from MATHEMATICIAN-WORKFLOWS §7: Tier 2/4 phase wiring is narrative-only.",
    )


def _stage_verify_claim(*, dry_run: bool) -> DemoStage:
    """Stage 4: verify-claim — SKIPPED (live LLM + Lean blows the 5-min budget)."""
    note = "Run live: `grd lean verify-claim --phase 1 --claim derived-energy-conservation`"
    return DemoStage(
        name="verify-claim",
        command="/grd:verify-claim --phase 1 --claim derived-energy-conservation",
        status="skipped",
        narration=_VERIFY_CLAIM.rstrip(),
        shipped_in="ge-ln7 + ge-cla + ge-j8k",
        note=note,
    )


def _stage_progress_post(*, dry_run: bool) -> DemoStage:
    """Stage 5: /grd:progress snapshot after verify-claim."""
    return DemoStage(
        name="progress-post",
        command="/grd:progress",
        status="mock",
        narration=_PROGRESS_POST.rstrip(),
        shipped_in="ge-8g5",
        note="Blueprint URL is the expected-state format from §7.",
    )


# ─── Public entry point ─────────────────────────────────────────────────────


def run_demo(
    cwd: Path,
    *,
    template: str = DEFAULT_TEMPLATE,
    dry_run: bool = False,
) -> DemoResult:
    """Run the §7 transcript end-to-end against ``template``.

    Always produces a deterministic stage sequence; the only live side effect
    (absent ``--dry-run``) is stamping ``template`` into ``cwd/.grd/demo/<template>/``.
    Every other stage is labeled MOCK or SKIPPED so the screen-shared viewer
    can tell at a glance what was really executed vs narrated.
    """
    started = time.monotonic()

    # Validate the template up front so the transcript doesn't half-emit.
    try:
        get_project_template(template)
    except KeyError as exc:
        raise ValueError(str(exc)) from exc

    project_dir = (cwd / ".grd" / "demo" / template).resolve()

    stages: list[DemoStage] = []
    stamp_result: StampResult | None = None

    stage1, stamp_result = _stage_new_project(project_dir, template, dry_run=dry_run)
    stages.append(stage1)
    stages.append(_stage_bootstrap(dry_run=dry_run))
    stages.append(_stage_progress_pre(dry_run=dry_run))
    stages.append(_stage_verify_claim(dry_run=dry_run))
    stages.append(_stage_progress_post(dry_run=dry_run))

    warnings: list[str] = []
    if not dry_run and stamp_result is not None and stamp_result.skipped:
        warnings.append("some template files already existed and were overwritten: " + ", ".join(stamp_result.skipped))

    return DemoResult(
        template=template,
        dry_run=dry_run,
        stages=stages,
        project_dir=str(project_dir) if not dry_run else None,
        stamp_result=stamp_result,
        duration_ms=int((time.monotonic() - started) * 1000),
        warnings=warnings,
    )
