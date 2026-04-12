"""Lean toolchain bootstrap — the engine behind ``/grd:lean-bootstrap``.

Idempotent, resumable, non-blocking. Every stage follows the same contract:

    detect() -> (already_installed: bool, version_or_path: str | None)
    install() -> BootstrapStageResult

Stage 0 (env check) is handled by the orchestrator itself. Stages 1–3 are
"quiet" — user-local, reversible, no prompts. Stages 4–5 auto-install if a
user-level package manager is available, otherwise degrade. Stages 6–7 are
opt-in with "ask once, remember" consent stored in ``.grd/lean-env.json``.

See PITCH.md §System Requirements & Bootstrap for the full spec; this module
implements those stages. Heavy work — curl-to-sh, pip install, lake cache —
is always gated behind an explicit caller flag so unit tests never touch the
network.
"""

from __future__ import annotations

import dataclasses
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

from grd.core.lean.env import detect_toolchain, load_env, pantograph_available, save_env
from grd.core.lean.protocol import BootstrapReport, BootstrapStageResult

__all__ = [
    "BOOTSTRAP_SCHEMA_VERSION",
    "BootstrapOptions",
    "run_bootstrap",
    "uninstall",
]


BOOTSTRAP_SCHEMA_VERSION = 1
"""Bumped only on breaking changes to the ``.grd/lean-env.json`` shape.

Minor additions (new optional keys) do not bump the version — the loader
treats unknown keys as ignorable. Downgrades after a bump re-run the bootstrap.
"""

_ELAN_INSTALL_URL = "https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh"
_DEFAULT_TOOLCHAIN = "leanprover/lean4:stable"

_PIP_PACKAGES: tuple[str, ...] = ("pantograph", "leanblueprint", "plastex")
"""Stage 3 pip install target set.

Pinned to the ones the PITCH calls out explicitly. ``pantograph`` is the one
that gates the daemon's REPL-reuse upgrade (see follow-up bead ``ge-nsd``);
the other two unlock Blueprint rendering once Phase 2 lands.
"""


@dataclasses.dataclass(frozen=True)
class BootstrapOptions:
    """Caller-supplied knobs. Defaults match ``/grd:lean-bootstrap`` with no flags."""

    yes: bool = False
    """Auto-answer any "ask once" consent prompts (stages 6–7). When False,
    we never initiate a consent-gated stage — the caller is responsible for
    asking the user and calling back with ``yes=True``."""

    with_graphviz: bool = False
    """Enable stage 4 (graphviz). Off by default — only turned on when the
    user invokes a workflow that needs SVG dep-graph rendering."""

    with_tectonic: bool = False
    """Enable stage 5 (tectonic). Off by default — only turned on when the
    user requests PDF output of a blueprint."""

    with_mathlib_cache: bool = False
    """Stage 6 — opt-in Mathlib olean cache. ``yes=True`` required to actually
    run; without it, the stage records ``skipped_user_declined`` so the skill
    knows to ask the user."""

    with_leandojo: bool = False
    """Stage 7 — opt-in LeanDojo premise index. Same consent rules as 6."""

    dry_run: bool = False
    """Report what would happen without touching anything — used by the
    skill's preview pass and by tests."""

    force: bool = False
    """Ignore cached ``skipped_user_declined`` / ``ok`` markers and re-attempt
    every stage. Users hit this via ``grd lean bootstrap --force``."""


# ─── Stage helpers ──────────────────────────────────────────────────────────


def _now_ms() -> int:
    return int(time.monotonic() * 1000)


def _run(
    cmd: list[str],
    *,
    timeout: float = 300.0,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
) -> tuple[int, str, str]:
    """Thin subprocess wrapper that never raises for process failures.

    Returns ``(returncode, stdout, stderr)``. Missing binary, timeout, or
    OSError collapse to ``(-1, "", message)`` so callers can branch on rc
    without try/except noise. Output is captured, not streamed, because the
    CLI renders the structured report after the fact.
    """
    try:
        proc = subprocess.run(  # noqa: S603 — caller-vetted argv, never a shell
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            input=input_text,
            check=False,
        )
    except FileNotFoundError as exc:
        return -1, "", f"binary not found: {exc}"
    except subprocess.TimeoutExpired:
        return -1, "", f"timeout after {timeout}s"
    except OSError as exc:
        return -1, "", f"OSError: {exc}"
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def _is_writable_dir(path: Path) -> bool:
    """Does the current user own or at least write to ``path``?"""
    try:
        return path.exists() and os.access(path, os.W_OK)
    except OSError:
        return False


def _has_user_package_manager() -> str | None:
    """Return the first user-level package manager we recognise, else None.

    User-level = doesn't need sudo. ``brew`` and ``nix-env`` qualify; plain
    ``apt`` / ``pacman`` do not (they need root). We don't try to be clever
    about rootless container detection — if the user runs under one, they
    can install graphviz themselves.
    """
    for name in ("brew", "nix-env"):
        if shutil.which(name):
            return name
    return None


# ─── Stages ─────────────────────────────────────────────────────────────────


def _stage_elan(opts: BootstrapOptions) -> BootstrapStageResult:
    """Stage 1: install elan into ``~/.elan/``.

    Skips if ``elan`` is already on PATH. Uses the official installer script
    piped into ``sh -s -- -y`` so no tty prompt. Never touches system dirs.
    """
    start = _now_ms()
    tc = detect_toolchain()
    if tc.elan_path and not opts.force:
        return BootstrapStageResult(
            name="elan",
            status="skipped_already_installed",
            detail=f"elan already at {tc.elan_path}",
            version=tc.elan_version,
            path=tc.elan_path,
            elapsed_ms=_now_ms() - start,
        )

    if opts.dry_run:
        return BootstrapStageResult(
            name="elan",
            status="ok",
            detail="dry-run: would curl elan-init.sh | sh -s -- -y --default-toolchain none",
            elapsed_ms=_now_ms() - start,
        )

    if not shutil.which("curl") and not shutil.which("wget"):
        return BootstrapStageResult(
            name="elan",
            status="failed",
            detail="need curl or wget to fetch the elan installer",
            elapsed_ms=_now_ms() - start,
        )

    fetcher = "curl"
    fetch_cmd = [fetcher, "-sSfL", _ELAN_INSTALL_URL]
    if not shutil.which("curl"):
        fetcher = "wget"
        fetch_cmd = ["wget", "-qO-", _ELAN_INSTALL_URL]
    rc, script, err = _run(fetch_cmd, timeout=60.0)
    if rc != 0 or not script:
        return BootstrapStageResult(
            name="elan",
            status="failed",
            detail=f"{fetcher} failed to download installer: {err.strip() or 'empty body'}",
            elapsed_ms=_now_ms() - start,
        )

    rc, _out, err = _run(
        ["sh", "-s", "--", "-y", "--default-toolchain", "none"],
        timeout=600.0,
        input_text=script,
    )
    if rc != 0:
        return BootstrapStageResult(
            name="elan",
            status="failed",
            detail=f"elan-init.sh exited {rc}: {err.strip()[:500]}",
            elapsed_ms=_now_ms() - start,
        )

    # Re-detect now that ~/.elan/bin exists. elan-init.sh tries to amend shell
    # rc files, but in the current process we still need to look through the
    # expected install path manually.
    elan_bin = Path.home() / ".elan" / "bin"
    tc = detect_toolchain(env={**os.environ, "PATH": f"{elan_bin}{os.pathsep}{os.environ.get('PATH', '')}"})
    return BootstrapStageResult(
        name="elan",
        status="ok",
        detail="installed user-local to ~/.elan/",
        version=tc.elan_version,
        path=tc.elan_path or str(elan_bin / "elan"),
        elapsed_ms=_now_ms() - start,
    )


def _stage_toolchain(opts: BootstrapOptions, project_root: Path) -> BootstrapStageResult:
    """Stage 2: ensure a Lean toolchain is installed.

    Honors ``lean-toolchain`` at project root if present (the PITCH says
    pinned toolchains take precedence). Otherwise falls back to
    ``leanprover/lean4:stable``. We go through ``elan toolchain install`` so
    the same code path works whether or not anything is currently default.
    """
    start = _now_ms()
    tc = detect_toolchain()
    if tc.lean_path and not opts.force:
        return BootstrapStageResult(
            name="toolchain",
            status="skipped_already_installed",
            detail=f"lean already at {tc.lean_path}",
            version=tc.lean_version,
            path=tc.lean_path,
            elapsed_ms=_now_ms() - start,
        )

    toolchain_file = project_root / "lean-toolchain"
    target = _DEFAULT_TOOLCHAIN
    if toolchain_file.exists():
        try:
            candidate = toolchain_file.read_text(encoding="utf-8").strip()
        except OSError:
            candidate = ""
        if candidate:
            target = candidate

    if opts.dry_run:
        return BootstrapStageResult(
            name="toolchain",
            status="ok",
            detail=f"dry-run: would install toolchain {target!r}",
            elapsed_ms=_now_ms() - start,
        )

    elan = tc.elan_path or str(Path.home() / ".elan" / "bin" / "elan")
    if not Path(elan).exists():
        return BootstrapStageResult(
            name="toolchain",
            status="failed",
            detail="elan not available; stage 1 must succeed first",
            elapsed_ms=_now_ms() - start,
        )

    rc, _out, err = _run([elan, "toolchain", "install", target], timeout=1800.0)
    if rc != 0:
        return BootstrapStageResult(
            name="toolchain",
            status="failed",
            detail=f"elan toolchain install {target!r} exited {rc}: {err.strip()[:500]}",
            elapsed_ms=_now_ms() - start,
        )

    # Set it as the default so plain ``lean`` works without cd'ing into a
    # project with a pinned toolchain file.
    _run([elan, "default", target], timeout=60.0)

    tc = detect_toolchain()
    return BootstrapStageResult(
        name="toolchain",
        status="ok",
        detail=f"installed {target!r}",
        version=tc.lean_version,
        path=tc.lean_path,
        elapsed_ms=_now_ms() - start,
    )


def _stage_pantograph(opts: BootstrapOptions) -> BootstrapStageResult:
    """Stage 3: pip install pantograph + leanblueprint + plastex into this venv.

    Uses ``sys.executable -m pip`` so whichever Python is running GRD is the
    one that gets the packages — no sudo, no venv-hopping. ``pantograph``
    availability drives the daemon's REPL-reuse upgrade (follow-up ``ge-nsd``).
    """
    start = _now_ms()
    needed = _missing_pip_packages()
    if not needed and not opts.force:
        return BootstrapStageResult(
            name="pantograph",
            status="skipped_already_installed",
            detail=f"all {len(_PIP_PACKAGES)} packages importable in this venv",
            elapsed_ms=_now_ms() - start,
        )

    install_list = list(_PIP_PACKAGES) if opts.force else needed
    if opts.dry_run:
        return BootstrapStageResult(
            name="pantograph",
            status="ok",
            detail=f"dry-run: would pip install {' '.join(install_list)}",
            elapsed_ms=_now_ms() - start,
        )

    rc, _out, err = _run(
        [sys.executable, "-m", "pip", "install", "--upgrade", *install_list],
        timeout=900.0,
    )
    if rc != 0:
        still_missing = _missing_pip_packages()
        return BootstrapStageResult(
            name="pantograph",
            status="failed",
            detail=(f"pip install exited {rc}. Still missing: {still_missing}. stderr: {err.strip()[:500]}"),
            elapsed_ms=_now_ms() - start,
        )

    return BootstrapStageResult(
        name="pantograph",
        status="ok",
        detail=f"installed: {' '.join(install_list)}",
        version=None,
        elapsed_ms=_now_ms() - start,
    )


def _missing_pip_packages() -> list[str]:
    """Return subset of ``_PIP_PACKAGES`` that can't be imported right now."""
    import importlib.util

    missing: list[str] = []
    for pkg in _PIP_PACKAGES:
        # pypi name != import name for leanblueprint (which is imported as
        # ``leanblueprint``) — they match today, so a simple find_spec works.
        mod_name = pkg.replace("-", "_")
        try:
            if importlib.util.find_spec(mod_name) is None:
                missing.append(pkg)
        except (ImportError, ValueError):
            missing.append(pkg)
    return missing


def _stage_graphviz(opts: BootstrapOptions) -> BootstrapStageResult:
    """Stage 4: graphviz, but only if a user-local package manager exists.

    "Never prompt" is the rule from PITCH §Non-Blocking Dependency Handling —
    if no user-level PM is available we return ``degraded`` so the caller
    renders ASCII graphs, and we tell the user how to install it themselves.
    """
    start = _now_ms()
    dot = shutil.which("dot")
    if dot and not opts.force:
        return BootstrapStageResult(
            name="graphviz",
            status="skipped_already_installed",
            detail=f"graphviz already at {dot}",
            path=dot,
            elapsed_ms=_now_ms() - start,
        )

    if not opts.with_graphviz:
        return BootstrapStageResult(
            name="graphviz",
            status="skipped_not_requested",
            detail="pass --with-graphviz or invoke a skill that needs SVG rendering",
            elapsed_ms=_now_ms() - start,
        )

    pm = _has_user_package_manager()
    if pm is None:
        return BootstrapStageResult(
            name="graphviz",
            status="degraded",
            detail=(
                "no user-level package manager found (brew, nix-env). "
                "ASCII dep graphs will be used; for SVGs install graphviz manually "
                "(e.g. 'sudo apt install graphviz' or set GRD_GRAPHVIZ_PATH)."
            ),
            elapsed_ms=_now_ms() - start,
        )

    if opts.dry_run:
        return BootstrapStageResult(
            name="graphviz",
            status="ok",
            detail=f"dry-run: would install graphviz via {pm}",
            elapsed_ms=_now_ms() - start,
        )

    cmd = [pm, "install", "graphviz"] if pm == "brew" else [pm, "-iA", "nixpkgs.graphviz"]
    rc, _out, err = _run(cmd, timeout=900.0)
    if rc != 0:
        return BootstrapStageResult(
            name="graphviz",
            status="degraded",
            detail=f"{pm} failed (rc={rc}): {err.strip()[:300]}. Falling back to ASCII dep graphs.",
            elapsed_ms=_now_ms() - start,
        )

    dot = shutil.which("dot")
    return BootstrapStageResult(
        name="graphviz",
        status="ok",
        detail=f"installed via {pm}",
        path=dot,
        elapsed_ms=_now_ms() - start,
    )


def _stage_tectonic(opts: BootstrapOptions) -> BootstrapStageResult:
    """Stage 5: tectonic for LaTeX, preferred over pdflatex family.

    Skips entirely if any working LaTeX compiler is already present — the
    user already has a way to produce PDFs. Only installs when ``--with-tectonic``
    is explicitly set AND no compiler is around.
    """
    start = _now_ms()
    existing = next(
        (shutil.which(c) for c in ("tectonic", "pdflatex", "xelatex", "lualatex") if shutil.which(c)),
        None,
    )
    if existing and not opts.force:
        return BootstrapStageResult(
            name="tectonic",
            status="skipped_already_installed",
            detail=f"LaTeX compiler already at {existing}",
            path=existing,
            elapsed_ms=_now_ms() - start,
        )

    if not opts.with_tectonic:
        return BootstrapStageResult(
            name="tectonic",
            status="skipped_not_requested",
            detail="pass --with-tectonic or request PDF rendering to trigger install",
            elapsed_ms=_now_ms() - start,
        )

    # cargo-based install is the most portable user-local option; the tectonic
    # release-binary route needs OS/arch detection we'd rather not bake in here.
    if not shutil.which("cargo"):
        return BootstrapStageResult(
            name="tectonic",
            status="degraded",
            detail=(
                "cargo not found — skipping tectonic install. Blueprint HTML output still works. "
                "For PDF, install tectonic manually (https://tectonic-typesetting.github.io/en-US/install.html)."
            ),
            elapsed_ms=_now_ms() - start,
        )

    if opts.dry_run:
        return BootstrapStageResult(
            name="tectonic",
            status="ok",
            detail="dry-run: would cargo install tectonic",
            elapsed_ms=_now_ms() - start,
        )

    rc, _out, err = _run(["cargo", "install", "tectonic"], timeout=1800.0)
    if rc != 0:
        return BootstrapStageResult(
            name="tectonic",
            status="degraded",
            detail=f"cargo install tectonic failed (rc={rc}): {err.strip()[:300]}. HTML output still works.",
            elapsed_ms=_now_ms() - start,
        )

    tec = shutil.which("tectonic") or str(Path.home() / ".cargo" / "bin" / "tectonic")
    return BootstrapStageResult(
        name="tectonic",
        status="ok",
        detail="installed via cargo (~/.cargo/bin/tectonic)",
        path=tec,
        elapsed_ms=_now_ms() - start,
    )


def _stage_mathlib_cache(
    opts: BootstrapOptions,
    project_root: Path,
    prior: dict[str, object],
) -> BootstrapStageResult:
    """Stage 6: ``lake exe cache get`` — big (~10 GB), opt-in.

    Only runs when (a) the caller set ``with_mathlib_cache=True`` AND (b)
    ``yes=True`` was passed or a prior run recorded explicit consent. If the
    user previously declined ("never"), we honour that and don't re-ask
    unless ``--force``.
    """
    start = _now_ms()
    if not opts.with_mathlib_cache:
        return BootstrapStageResult(
            name="mathlib_cache",
            status="skipped_not_requested",
            detail="pass --with-mathlib-cache after confirming ~10 GB is acceptable",
            elapsed_ms=_now_ms() - start,
        )

    consent = _prior_consent(prior, "mathlib_cache")
    if consent == "never" and not opts.force:
        return BootstrapStageResult(
            name="mathlib_cache",
            status="skipped_user_declined",
            detail="user previously answered 'never'; run with --force to override",
            elapsed_ms=_now_ms() - start,
        )

    if not opts.yes and consent != "yes":
        return BootstrapStageResult(
            name="mathlib_cache",
            status="skipped_user_declined",
            detail="no consent recorded; re-run with --yes after the skill asks the user",
            elapsed_ms=_now_ms() - start,
        )

    lake = shutil.which("lake")
    if not lake:
        return BootstrapStageResult(
            name="mathlib_cache",
            status="failed",
            detail="lake not on PATH; stages 1–2 must have succeeded",
            elapsed_ms=_now_ms() - start,
        )

    lakefile = project_root / "lakefile.lean"
    if not lakefile.exists() and not (project_root / "lakefile.toml").exists():
        return BootstrapStageResult(
            name="mathlib_cache",
            status="skipped_not_requested",
            detail="no lakefile in project root; nothing to cache",
            elapsed_ms=_now_ms() - start,
        )

    if opts.dry_run:
        return BootstrapStageResult(
            name="mathlib_cache",
            status="ok",
            detail="dry-run: would run 'lake exe cache get'",
            elapsed_ms=_now_ms() - start,
        )

    rc, _out, err = _run([lake, "exe", "cache", "get"], timeout=3600.0)
    if rc != 0:
        return BootstrapStageResult(
            name="mathlib_cache",
            status="failed",
            detail=f"lake exe cache get exited {rc}: {err.strip()[:300]}",
            elapsed_ms=_now_ms() - start,
        )

    return BootstrapStageResult(
        name="mathlib_cache",
        status="ok",
        detail="downloaded via lake exe cache get",
        elapsed_ms=_now_ms() - start,
    )


def _stage_leandojo(opts: BootstrapOptions, prior: dict[str, object]) -> BootstrapStageResult:
    """Stage 7: LeanDojo premise index — even bigger, opt-in."""
    start = _now_ms()
    if not opts.with_leandojo:
        return BootstrapStageResult(
            name="leandojo",
            status="skipped_not_requested",
            detail="pass --with-leandojo to enable premise retrieval (~3–5 GB)",
            elapsed_ms=_now_ms() - start,
        )

    consent = _prior_consent(prior, "leandojo")
    if consent == "never" and not opts.force:
        return BootstrapStageResult(
            name="leandojo",
            status="skipped_user_declined",
            detail="user previously answered 'never'; run with --force to override",
            elapsed_ms=_now_ms() - start,
        )

    if not opts.yes and consent != "yes":
        return BootstrapStageResult(
            name="leandojo",
            status="skipped_user_declined",
            detail="no consent recorded; re-run with --yes after the skill asks the user",
            elapsed_ms=_now_ms() - start,
        )

    if opts.dry_run:
        return BootstrapStageResult(
            name="leandojo",
            status="ok",
            detail="dry-run: would pip install lean-dojo and build premise index",
            elapsed_ms=_now_ms() - start,
        )

    rc, _out, err = _run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "lean-dojo"],
        timeout=900.0,
    )
    if rc != 0:
        return BootstrapStageResult(
            name="leandojo",
            status="failed",
            detail=f"pip install lean-dojo exited {rc}: {err.strip()[:300]}",
            elapsed_ms=_now_ms() - start,
        )

    return BootstrapStageResult(
        name="leandojo",
        status="ok",
        detail="lean-dojo installed; premise index will build on first use",
        elapsed_ms=_now_ms() - start,
    )


def _prior_consent(prior: dict[str, object], stage: str) -> str | None:
    """Return the stored consent answer for an opt-in stage.

    ``.grd/lean-env.json`` records consent under ``consent.<stage>`` with
    values ``"yes" | "no" | "never"``. Any other shape is treated as absent.
    """
    consent = prior.get("consent")
    if not isinstance(consent, dict):
        return None
    answer = consent.get(stage)
    return answer if isinstance(answer, str) and answer in {"yes", "no", "never"} else None


# ─── Orchestrator ───────────────────────────────────────────────────────────


def run_bootstrap(
    project_root: Path,
    *,
    options: BootstrapOptions | None = None,
) -> BootstrapReport:
    """Run all stages, write progress to ``.grd/lean-env.json`` after each.

    On any stage failure we continue — the whole point of the "non-blocking"
    design is that later stages (e.g. pantograph) still run even if an
    earlier one (e.g. a one-off elan hiccup) had a transient failure. The
    report's ``ok`` flag is False iff any *required* stage failed; opt-in
    skips don't count against it.
    """
    opts = options or BootstrapOptions()
    from grd.core.lean.env import env_file_path

    started = _now_ms()
    env_path = env_file_path(project_root)
    prior = load_env(project_root)
    stages: list[BootstrapStageResult] = []
    degraded_notes: list[str] = []

    def _record(result: BootstrapStageResult) -> None:
        stages.append(result)
        _persist(project_root, prior, stages, opts, in_progress=True)
        if result.status == "degraded":
            degraded_notes.append(f"{result.name}: {result.detail}")

    _record(_stage_elan(opts))
    _record(_stage_toolchain(opts, project_root))
    _record(_stage_pantograph(opts))
    _record(_stage_graphviz(opts))
    _record(_stage_tectonic(opts))
    _record(_stage_mathlib_cache(opts, project_root, prior))
    _record(_stage_leandojo(opts, prior))

    required = {"elan", "toolchain", "pantograph"}
    ok = all(s.status != "failed" for s in stages if s.name in required)

    report = BootstrapReport(
        ok=ok,
        stages=stages,
        env_file=str(env_path),
        elapsed_ms=_now_ms() - started,
        degraded_notes=degraded_notes,
    )
    _persist(project_root, prior, stages, opts, in_progress=False, report=report)
    return report


def _persist(
    project_root: Path,
    prior: dict[str, object],
    stages: list[BootstrapStageResult],
    opts: BootstrapOptions,
    *,
    in_progress: bool,
    report: BootstrapReport | None = None,
) -> None:
    """Write ``.grd/lean-env.json`` atomically after every stage.

    Preserves prior state (consent answers, unknown keys future GRD versions
    might set) so a partial re-run doesn't clobber the user's earlier
    decisions.
    """
    data: dict[str, object] = dict(prior)
    data["schema_version"] = BOOTSTRAP_SCHEMA_VERSION
    data["stages"] = [s.model_dump() for s in stages]
    data["in_progress"] = in_progress
    data["options"] = {
        "with_graphviz": opts.with_graphviz,
        "with_tectonic": opts.with_tectonic,
        "with_mathlib_cache": opts.with_mathlib_cache,
        "with_leandojo": opts.with_leandojo,
    }
    if report is not None:
        data["last_report"] = report.model_dump()
    save_env(project_root, data)


# ─── Teardown ───────────────────────────────────────────────────────────────


def uninstall(
    project_root: Path,
    *,
    dry_run: bool = False,
    runner: Callable[[list[str]], tuple[int, str, str]] | None = None,
) -> dict[str, object]:
    """Remove GRD-added Lean artifacts. Keeps system-level graphviz/tectonic.

    Returns a dict listing each path we touched and the action taken. Tests
    pass ``runner`` to capture the ``rm -rf`` calls without hitting disk.
    """
    paths = [
        Path.home() / ".elan",
        Path.home() / ".cache" / "leandojo",
        Path.home() / ".cache" / "Tectonic",
        project_root / ".lake",
        project_root / "blueprint" / ".lake",
    ]
    run = runner or _run_rm
    results: list[dict[str, object]] = []
    for p in paths:
        if not p.exists():
            results.append({"path": str(p), "action": "absent"})
            continue
        if dry_run:
            results.append({"path": str(p), "action": "would_remove"})
            continue
        rc, _out, err = run(["rm", "-rf", str(p)])
        results.append({"path": str(p), "action": "removed" if rc == 0 else "failed", "detail": err.strip()[:200]})
    return {"paths": results, "dry_run": dry_run}


def _run_rm(cmd: list[str]) -> tuple[int, str, str]:
    return _run(cmd, timeout=60.0)


# Re-export helpers some tests reach for.
__all__ += ["pantograph_available"]
