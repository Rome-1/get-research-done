"""Validation subcommands and review-preflight logic."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import typer
from pydantic import ValidationError as PydanticValidationError

from grd.cli._helpers import (
    _PROJECT_AWARE_EXPLICIT_INPUTS,
    CommandContextCheck,
    CommandContextPreflightResult,
    ReviewPreflightCheck,
    ReviewPreflightResult,
    _build_project_aware_guidance,
    _error,
    _first_existing_path,
    _format_display_path,
    _get_cwd,
    _has_simple_positional_inputs,
    _load_json_document,
    _output,
    _raise_pydantic_schema_error,
    _resolve_registry_command,
    _run_frontmatter_validation,
)
from grd.core.errors import GRDError

validate_app = typer.Typer(help="Validation checks")


# ─── Internal preflight helpers ─────────────────────────────────────────────


def _find_manuscript_main(cwd: Path) -> Path | None:
    """Locate the primary manuscript entry point if one exists."""
    for rel_path in ("paper/main.tex", "manuscript/main.tex", "draft/main.tex"):
        candidate = cwd / rel_path
        if candidate.exists():
            return candidate
    return None


def _resolve_review_preflight_manuscript(cwd: Path, subject: str | None) -> tuple[Path | None, str]:
    """Resolve a review-preflight manuscript target from an explicit subject or defaults."""
    if subject:
        target = Path(subject)
        if not target.is_absolute():
            target = cwd / target

        if not target.exists():
            return None, f"missing explicit manuscript target {_format_display_path(target)}"

        if target.is_file():
            if target.suffix in {".tex", ".md"}:
                return target, f"{_format_display_path(target)} present"
            return None, f"explicit manuscript target must be a .tex or .md file: {_format_display_path(target)}"

        if target.is_dir():
            candidate = _first_existing_path(target / "main.tex", target / "main.md")
            if candidate is None:
                direct_files = sorted(
                    path for path in target.iterdir() if path.is_file() and path.suffix in {".tex", ".md"}
                )
                if direct_files:
                    candidate = direct_files[0]
            if candidate is not None:
                return candidate, f"{_format_display_path(target)} resolved to {_format_display_path(candidate)}"
            return None, f"no manuscript entry point found under {_format_display_path(target)}"

    manuscript = _find_manuscript_main(cwd)
    if manuscript is not None:
        return manuscript, f"{_format_display_path(manuscript)} present"
    return None, "no paper/main.tex, manuscript/main.tex, or draft/main.tex found"


_REVIEW_PRECHECK_BLOCKING_CONDITIONS: dict[str, tuple[str, ...]] = {
    "project_state": ("missing project state",),
    "state_integrity": ("degraded review integrity",),
    "roadmap": ("missing roadmap",),
    "conventions": ("missing conventions",),
    "research_artifacts": ("no research artifacts",),
    "summary_frontmatter": ("degraded review integrity",),
    "verification_frontmatter": ("degraded review integrity",),
    "manuscript": ("missing manuscript",),
    "phase_lookup": ("missing phase artifacts",),
    "phase_summaries": ("missing phase artifacts",),
}

_REVIEW_PRECHECK_REQUIRED_EVIDENCE: dict[str, tuple[str, ...]] = {
    "research_artifacts": ("phase summaries or milestone digest",),
    "verification_reports": ("verification reports",),
    "artifact_manifest": ("artifact manifest",),
    "bibliography_audit": ("bibliography audit",),
    "bibliography_audit_clean": ("bibliography audit",),
    "reproducibility_manifest": ("reproducibility manifest",),
    "reproducibility_ready": ("reproducibility manifest",),
}

_PHASE_EXECUTED_STATUSES = {
    "phase complete — ready for verification",
    "verifying",
    "complete",
    "milestone complete",
}


def _normalized_contract_entries(values: list[str]) -> set[str]:
    """Normalize review-contract strings for case-insensitive membership checks."""
    return {value.strip().lower() for value in values if value and value.strip()}


def _review_preflight_check_is_blocking(contract: object, check_name: str) -> bool:
    """Return True when the typed review contract marks a check as hard-blocking."""
    blocking_conditions = _normalized_contract_entries(getattr(contract, "blocking_conditions", []))
    required_evidence = _normalized_contract_entries(getattr(contract, "required_evidence", []))

    return any(
        alias in blocking_conditions for alias in _REVIEW_PRECHECK_BLOCKING_CONDITIONS.get(check_name, ())
    ) or any(alias in required_evidence for alias in _REVIEW_PRECHECK_REQUIRED_EVIDENCE.get(check_name, ()))


def _evaluate_review_required_state(
    contract: object,
    *,
    cwd: Path,
    subject: str | None,
    phase_info: object | None,
) -> tuple[bool, str] | None:
    """Evaluate review_contract.required_state in a way that matches phase-scoped workflows."""
    from grd.core.phases import find_phase
    from grd.core.state import load_state_json
    from grd.core.utils import phase_normalize

    required_state = str(getattr(contract, "required_state", "") or "").strip()
    if not required_state:
        return None
    if required_state != "phase_executed":
        return False, f'unhandled required_state="{required_state}"'

    state_obj = load_state_json(cwd)
    if not isinstance(state_obj, dict):
        return False, "required_state=phase_executed could not load state.json"

    position = state_obj.get("position")
    if not isinstance(position, dict):
        return False, "required_state=phase_executed could not read position from state.json"

    current_phase = phase_normalize(str(position.get("current_phase") or "")).strip()
    current_status = str(position.get("status") or "").strip()
    current_status_normalized = current_status.lower()

    target_phase = ""
    if phase_info is not None:
        target_phase = str(getattr(phase_info, "phase_number", "") or "").strip()
    elif subject:
        target_phase = phase_normalize(subject).strip()
    elif current_phase:
        target_phase = current_phase

    if target_phase and current_phase and target_phase == current_phase:
        if current_status_normalized in _PHASE_EXECUTED_STATUSES:
            return True, (
                f'required_state=phase_executed satisfied for current phase {current_phase} (status "{current_status}")'
            )
        expected_statuses = "Phase complete \u2014 ready for verification, Verifying, Complete, or Milestone complete"
        return False, (
            f"required_state=phase_executed expects current phase {current_phase} to be in one of: "
            f'{expected_statuses}; found "{current_status or "unknown"}"'
        )

    resolved_phase_info = (
        phase_info if phase_info is not None else (find_phase(cwd, target_phase) if target_phase else None)
    )
    if resolved_phase_info is not None:
        summary_count = len(getattr(resolved_phase_info, "summaries", []))
        has_verification = bool(getattr(resolved_phase_info, "has_verification", False))
        if summary_count or has_verification:
            detail = (
                f'required_state=phase_executed satisfied for phase "{resolved_phase_info.phase_number}" '
                f"via {summary_count} summary artifact(s)"
                if summary_count
                else f'required_state=phase_executed satisfied for phase "{resolved_phase_info.phase_number}" '
                "via existing verification artifacts"
            )
            if current_phase and target_phase and current_phase != target_phase:
                detail = f"{detail}; current state is focused on phase {current_phase}"
            return True, detail

    if target_phase:
        return False, f'required_state=phase_executed is not satisfied for phase "{target_phase}"'
    return False, "required_state=phase_executed could not determine a target phase"


def _current_review_phase_subject(cwd: Path) -> str | None:
    """Return the current phase number from state.json for phase-scoped review preflights."""
    from grd.core.state import load_state_json
    from grd.core.utils import phase_normalize

    state_obj = load_state_json(cwd)
    if not isinstance(state_obj, dict):
        return None
    position = state_obj.get("position")
    if not isinstance(position, dict):
        return None
    current_phase = phase_normalize(str(position.get("current_phase") or "")).strip()
    return current_phase or None


def _has_any_phase_summary(phases_dir: Path) -> bool:
    """Return True when any numbered or standalone summary exists."""
    if not phases_dir.exists():
        return False
    return any(path.is_file() for path in phases_dir.rglob("*SUMMARY.md"))


def _validate_phase_artifacts(phases_dir: Path, schema_name: str) -> list[str]:
    """Return per-file frontmatter validation failures for phase artifacts."""
    from grd.core.frontmatter import validate_frontmatter

    if not phases_dir.exists():
        return []

    suffix = "*SUMMARY.md" if schema_name == "summary" else "*VERIFICATION.md"
    failures: list[str] = []
    for path in sorted(phases_dir.rglob(suffix)):
        try:
            content = path.read_text(encoding="utf-8")
            validation = validate_frontmatter(content, schema_name, source_path=path)
        except Exception as exc:  # pragma: no cover - defensive file parsing guard
            failures.append(f"{_format_display_path(path)}: could not validate frontmatter ({exc})")
            continue
        if validation.valid:
            continue
        detail_parts = [*validation.missing, *validation.errors]
        detail = "; ".join(detail_parts[:3]) if detail_parts else "frontmatter invalid"
        failures.append(f"{_format_display_path(path)}: {detail}")
    return failures


def _build_command_context_preflight(
    command_name: str,
    *,
    arguments: str | None = None,
) -> CommandContextPreflightResult:
    """Evaluate whether a command can run in the current workspace context."""
    from grd.core.constants import ProjectLayout

    cwd = _get_cwd()
    layout = ProjectLayout(cwd)
    command, public_command_name = _resolve_registry_command(command_name)
    project_exists = layout.project_md.exists()

    checks: list[CommandContextCheck] = []

    def add_check(name: str, passed: bool, detail: str, *, blocking: bool = True) -> None:
        checks.append(CommandContextCheck(name=name, passed=passed, detail=detail, blocking=blocking))

    add_check("context_mode", True, f"context_mode={command.context_mode}", blocking=False)

    if command.context_mode == "global":
        add_check("project_context", True, "command runs without project context", blocking=False)
        return CommandContextPreflightResult(
            command=public_command_name,
            context_mode=command.context_mode,
            passed=True,
            project_exists=project_exists,
            explicit_inputs=[],
            guidance="",
            checks=checks,
        )

    if command.context_mode == "projectless":
        add_check(
            "project_context",
            True,
            ("initialized project detected" if project_exists else "no initialized project required"),
            blocking=False,
        )
        return CommandContextPreflightResult(
            command=public_command_name,
            context_mode=command.context_mode,
            passed=True,
            project_exists=project_exists,
            explicit_inputs=[],
            guidance="",
            checks=checks,
        )

    if command.context_mode == "project-required":
        add_check(
            "project_exists",
            project_exists,
            (
                f"{_format_display_path(layout.project_md)} present"
                if project_exists
                else f"missing {_format_display_path(layout.project_md)}"
            ),
        )
        guidance = (
            "" if project_exists else "This command requires an initialized GRD project. Run `grd init new-project`."
        )
        return CommandContextPreflightResult(
            command=public_command_name,
            context_mode=command.context_mode,
            passed=project_exists,
            project_exists=project_exists,
            explicit_inputs=[],
            guidance=guidance,
            checks=checks,
        )

    explicit_inputs, predicate = _PROJECT_AWARE_EXPLICIT_INPUTS.get(
        command.name,
        (
            [command.argument_hint.strip()] if command.argument_hint.strip() else ["explicit command inputs"],
            _has_simple_positional_inputs,
        ),
    )
    explicit_inputs_ok = predicate(arguments)
    add_check(
        "project_exists",
        project_exists,
        (
            f"{_format_display_path(layout.project_md)} present"
            if project_exists
            else f"missing {_format_display_path(layout.project_md)}"
        ),
        blocking=False,
    )
    add_check(
        "explicit_inputs",
        explicit_inputs_ok,
        (
            "explicit standalone inputs detected"
            if explicit_inputs_ok
            else f"missing explicit standalone inputs ({', '.join(explicit_inputs)})"
        ),
        blocking=not project_exists,
    )
    passed = project_exists or explicit_inputs_ok
    guidance = "" if passed else _build_project_aware_guidance(explicit_inputs)
    return CommandContextPreflightResult(
        command=public_command_name,
        context_mode=command.context_mode,
        passed=passed,
        project_exists=project_exists,
        explicit_inputs=explicit_inputs,
        guidance=guidance,
        checks=checks,
    )


def _build_review_preflight(
    command_name: str,
    *,
    subject: str | None = None,
    strict: bool = False,
) -> ReviewPreflightResult:
    """Evaluate lightweight filesystem/state prerequisites for a review command."""
    from grd.core.constants import ProjectLayout
    from grd.core.phases import find_phase
    from grd.core.state import state_validate

    cwd = _get_cwd()
    layout = ProjectLayout(cwd)
    command, public_command_name = _resolve_registry_command(command_name)
    contract = command.review_contract
    if contract is None:
        raise GRDError(f"Command {public_command_name} does not expose a review contract")

    checks: list[ReviewPreflightCheck] = []
    phase_subject = subject
    if phase_subject is None and "phase_artifacts" in contract.preflight_checks:
        phase_subject = _current_review_phase_subject(cwd)
    phase_info = (
        find_phase(cwd, phase_subject) if phase_subject and "phase_artifacts" in contract.preflight_checks else None
    )

    def add_check(name: str, passed: bool, detail: str, *, blocking: bool | None = None) -> None:
        checks.append(
            ReviewPreflightCheck(
                name=name,
                passed=passed,
                detail=detail,
                blocking=_review_preflight_check_is_blocking(contract, name) if blocking is None else blocking,
            )
        )

    context_preflight = _build_command_context_preflight(command_name, arguments=subject)
    add_check(
        "command_context",
        context_preflight.passed,
        context_preflight.guidance or f"context_mode={command.context_mode}",
        blocking=True,
    )

    if "project_state" in contract.preflight_checks:
        state_ok = layout.state_json.exists() and layout.state_md.exists()
        add_check(
            "project_state",
            state_ok,
            (
                f"state.json={layout.state_json.exists()}, STATE.md={layout.state_md.exists()}"
                if not state_ok
                else f"{_format_display_path(layout.state_json)} and {_format_display_path(layout.state_md)} present"
            ),
        )
        if strict:
            validation = state_validate(cwd, integrity_mode="review")
            detail = f"integrity_status={validation.integrity_status}"
            if validation.issues:
                detail = f"{detail}; {'; '.join(validation.issues)}"
            add_check("state_integrity", validation.valid, detail)

    if "roadmap" in contract.preflight_checks:
        add_check(
            "roadmap",
            layout.roadmap.exists(),
            (
                f"{_format_display_path(layout.roadmap)} present"
                if layout.roadmap.exists()
                else f"missing {_format_display_path(layout.roadmap)}"
            ),
        )

    if "conventions" in contract.preflight_checks:
        add_check(
            "conventions",
            layout.conventions_md.exists(),
            (
                f"{_format_display_path(layout.conventions_md)} present"
                if layout.conventions_md.exists()
                else f"missing {_format_display_path(layout.conventions_md)}"
            ),
        )

    if "research_artifacts" in contract.preflight_checks:
        digest_exists = layout.milestones_dir.exists() and any(layout.milestones_dir.rglob("RESEARCH-DIGEST.md"))
        summary_exists = _has_any_phase_summary(layout.phases_dir)
        passed = digest_exists or summary_exists
        detail = "milestone digest or phase summaries present" if passed else "no digest or phase summaries found"
        add_check("research_artifacts", passed, detail)
        if strict and summary_exists:
            summary_failures = _validate_phase_artifacts(layout.phases_dir, "summary")
            add_check(
                "summary_frontmatter",
                not summary_failures,
                "all phase summaries satisfy the summary schema"
                if not summary_failures
                else "; ".join(summary_failures[:3]),
            )
        if strict:
            verification_exists = layout.phases_dir.exists() and any(layout.phases_dir.rglob("*VERIFICATION.md"))
            add_check(
                "verification_reports",
                verification_exists,
                "verification reports present" if verification_exists else "no verification reports found",
            )
            if verification_exists:
                verification_failures = _validate_phase_artifacts(layout.phases_dir, "verification")
                add_check(
                    "verification_frontmatter",
                    not verification_failures,
                    "all verification reports satisfy the verification schema"
                    if not verification_failures
                    else "; ".join(verification_failures[:3]),
                )

    if "manuscript" in contract.preflight_checks:
        manuscript, manuscript_detail = (
            _resolve_review_preflight_manuscript(cwd, subject)
            if command.name in {"grd:peer-review", "grd:arxiv-submission"}
            else (
                _find_manuscript_main(cwd),
                "",
            )
        )
        add_check(
            "manuscript",
            manuscript is not None,
            manuscript_detail
            if command.name in {"grd:peer-review", "grd:arxiv-submission"}
            else (
                f"{_format_display_path(manuscript)} present"
                if manuscript is not None
                else "no paper/main.tex, manuscript/main.tex, or draft/main.tex found"
            ),
        )
        if subject and command.name == "grd:respond-to-referees" and subject != "paste":
            report_path = Path(subject)
            if not report_path.is_absolute():
                report_path = cwd / report_path
            add_check(
                "referee_report_source",
                report_path.exists(),
                (
                    f"{_format_display_path(report_path)} present"
                    if report_path.exists()
                    else f"missing {_format_display_path(report_path)}"
                ),
                blocking=True,
            )
        if strict and manuscript is not None:
            artifact_manifest = _first_existing_path(
                manuscript.parent / "ARTIFACT-MANIFEST.json",
                cwd / ".grd" / "paper" / "ARTIFACT-MANIFEST.json",
            )
            bibliography_audit = _first_existing_path(
                manuscript.parent / "BIBLIOGRAPHY-AUDIT.json",
                cwd / ".grd" / "paper" / "BIBLIOGRAPHY-AUDIT.json",
            )
            reproducibility_manifest = _first_existing_path(
                manuscript.parent / "reproducibility-manifest.json",
                manuscript.parent / "REPRODUCIBILITY-MANIFEST.json",
                cwd / ".grd" / "paper" / "reproducibility-manifest.json",
            )
            add_check(
                "artifact_manifest",
                artifact_manifest is not None,
                (
                    f"{_format_display_path(artifact_manifest)} present"
                    if artifact_manifest is not None
                    else "no ARTIFACT-MANIFEST.json found near the manuscript"
                ),
            )
            add_check(
                "bibliography_audit",
                bibliography_audit is not None,
                (
                    f"{_format_display_path(bibliography_audit)} present"
                    if bibliography_audit is not None
                    else "no BIBLIOGRAPHY-AUDIT.json found near the manuscript"
                ),
            )
            add_check(
                "reproducibility_manifest",
                reproducibility_manifest is not None,
                (
                    f"{_format_display_path(reproducibility_manifest)} present"
                    if reproducibility_manifest is not None
                    else "no reproducibility manifest found near the manuscript"
                ),
            )
            if strict and command.name == "grd:peer-review" and bibliography_audit is not None:
                try:
                    audit_payload = json.loads(bibliography_audit.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    add_check("bibliography_audit_clean", False, f"could not parse bibliography audit: {exc}")
                else:
                    clean = (
                        int(audit_payload.get("resolved_sources", 0)) == int(audit_payload.get("total_sources", 0))
                        and int(audit_payload.get("partial_sources", 0)) == 0
                        and int(audit_payload.get("unverified_sources", 0)) == 0
                        and int(audit_payload.get("failed_sources", 0)) == 0
                    )
                    add_check(
                        "bibliography_audit_clean",
                        clean,
                        (
                            "all bibliography sources resolved and verified"
                            if clean
                            else "bibliography audit still has unresolved, partial, unverified, or failed sources"
                        ),
                    )
            if (
                strict
                and command.name in {"grd:peer-review", "grd:write-paper"}
                and reproducibility_manifest is not None
            ):
                from grd.core.reproducibility import validate_reproducibility_manifest

                try:
                    repro_payload = json.loads(reproducibility_manifest.read_text(encoding="utf-8"))
                    repro_validation = validate_reproducibility_manifest(repro_payload)
                except Exception as exc:  # pragma: no cover - defensive parsing guard
                    add_check("reproducibility_ready", False, f"could not validate reproducibility manifest: {exc}")
                else:
                    ready = (
                        repro_validation.valid and repro_validation.ready_for_review and not repro_validation.warnings
                    )
                    detail = (
                        "reproducibility manifest is review-ready"
                        if ready
                        else (
                            f"valid={repro_validation.valid}, ready_for_review={repro_validation.ready_for_review}, "
                            f"warnings={len(repro_validation.warnings)}, issues={len(repro_validation.issues)}"
                        )
                    )
                    add_check("reproducibility_ready", ready, detail)

    if "phase_artifacts" in contract.preflight_checks:
        if subject:
            phase_exists = phase_info is not None
            add_check(
                "phase_lookup",
                phase_exists,
                (
                    f'phase "{subject}" found in {_format_display_path(layout.phases_dir)}'
                    if phase_exists
                    else f'phase "{subject}" not found'
                ),
            )
            if phase_exists:
                summary_exists = bool(phase_info.summaries)
                add_check(
                    "phase_summaries",
                    summary_exists,
                    (
                        f'phase "{subject}" has {len(phase_info.summaries)} summary file(s)'
                        if summary_exists
                        else f'phase "{subject}" has no SUMMARY artifacts'
                    ),
                )
        else:
            summary_exists = (
                bool(getattr(phase_info, "summaries", []))
                if phase_info is not None
                else _has_any_phase_summary(layout.phases_dir)
            )
            add_check(
                "phase_summaries",
                summary_exists,
                (
                    f'current phase "{phase_info.phase_number}" has {len(phase_info.summaries)} summary file(s)'
                    if phase_info is not None and summary_exists
                    else (
                        f'current phase "{phase_info.phase_number}" has no SUMMARY artifacts'
                        if phase_info is not None
                        else ("phase summaries present" if summary_exists else "no phase summaries found")
                    )
                ),
            )

    required_state_check = _evaluate_review_required_state(contract, cwd=cwd, subject=subject, phase_info=phase_info)
    if required_state_check is not None:
        add_check("required_state", required_state_check[0], required_state_check[1], blocking=True)

    passed = all(check.passed or not check.blocking for check in checks)
    return ReviewPreflightResult(
        command=public_command_name,
        review_mode=contract.review_mode,
        strict=strict,
        passed=passed,
        checks=checks,
        required_outputs=contract.required_outputs,
        required_evidence=contract.required_evidence,
        blocking_conditions=contract.blocking_conditions,
    )


# ─── CLI commands ────────────────────────────────────────────────────────────


@validate_app.command("consistency")
def validate_consistency() -> None:
    """Validate cross-phase consistency."""
    from grd.core.health import run_health

    report = run_health(_get_cwd())
    _output(report)
    if report.overall == "fail":
        raise typer.Exit(code=1)


@validate_app.command("command-context", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def validate_command_context(
    ctx: typer.Context,
    command_name: str = typer.Argument(..., help="Command registry key or grd:name"),
) -> None:
    """Run centralized command-context preflight based on command metadata."""
    arguments = " ".join(str(arg) for arg in ctx.args) or None
    result = _build_command_context_preflight(command_name, arguments=arguments)
    _output(result)
    if not result.passed:
        raise typer.Exit(code=1)


@validate_app.command("review-contract")
def validate_review_contract(
    command_name: str = typer.Argument(..., help="Command registry key or grd:name"),
) -> None:
    """Show the typed review contract for a review-grade command."""
    command, public_command_name = _resolve_registry_command(command_name)
    if command.review_contract is None:
        _error(f"Command {public_command_name} has no review contract")
    _output(
        {
            "command": public_command_name,
            "context_mode": command.context_mode,
            "review_contract": dataclasses.asdict(command.review_contract),
        }
    )


@validate_app.command("review-preflight")
def validate_review_preflight(
    command_name: str = typer.Argument(..., help="Command registry key or grd:name"),
    subject: str | None = typer.Argument(None, help="Optional phase number or report path"),
    strict: bool = typer.Option(False, "--strict", help="Enable stricter evidence-oriented checks"),
) -> None:
    """Run lightweight executable preflight checks for review-grade workflows."""
    result = _build_review_preflight(command_name, subject=subject, strict=strict)
    _output(result)
    if not result.passed:
        raise typer.Exit(code=1)


@validate_app.command("paper-quality")
def validate_paper_quality(
    input_path: str | None = typer.Argument(None, help="Path to a paper-quality JSON file, or '-' for stdin"),
    from_project: str | None = typer.Option(
        None,
        "--from-project",
        help="Build the PaperQualityInput directly from project artifacts at this root",
    ),
) -> None:
    """Score a machine-readable paper-quality manifest and fail on blockers."""
    from grd.core.paper_quality import PaperQualityInput, score_paper_quality
    from grd.core.paper_quality_artifacts import build_paper_quality_input

    if from_project:
        report = score_paper_quality(build_paper_quality_input(Path(from_project)))
    else:
        if not input_path:
            _error("Provide a PaperQualityInput path or use --from-project <root>")
        payload = _load_json_document(input_path)
        try:
            paper_quality_input = PaperQualityInput.model_validate(payload)
        except PydanticValidationError as exc:
            _raise_pydantic_schema_error(
                label="paper-quality input",
                exc=exc,
                schema_reference="templates/paper/paper-quality-input-schema.md",
            )
        report = score_paper_quality(paper_quality_input)
    _output(report)
    if not report.ready_for_submission:
        raise typer.Exit(code=1)


@validate_app.command("project-contract")
def validate_project_contract_cmd(
    input_path: str = typer.Argument(..., help="Path to a project contract JSON file, or '-' for stdin"),
    mode: str = typer.Option("approved", "--mode", help="Validation mode: approved or draft"),
) -> None:
    """Validate a project-scoping contract before downstream artifact generation."""
    from grd.core.contract_validation import validate_project_contract

    normalized_mode = mode.strip().lower()
    if normalized_mode not in {"draft", "approved"}:
        raise GRDError(f"Invalid --mode {mode!r}. Expected 'draft' or 'approved'.")

    payload = _load_json_document(input_path)
    result = validate_project_contract(payload, mode=normalized_mode)
    _output(result)
    if not result.valid:
        raise typer.Exit(code=1)


@validate_app.command("plan-contract")
def validate_plan_contract_cmd(
    input_path: str = typer.Argument(..., help="Path to a PLAN.md file"),
) -> None:
    """Validate PLAN frontmatter, including the contract block and cross-links."""
    _run_frontmatter_validation(input_path, "plan")


@validate_app.command("summary-contract")
def validate_summary_contract_cmd(
    input_path: str = typer.Argument(..., help="Path to a SUMMARY.md file"),
) -> None:
    """Validate SUMMARY frontmatter and contract-result alignment."""
    _run_frontmatter_validation(input_path, "summary")


@validate_app.command("verification-contract")
def validate_verification_contract_cmd(
    input_path: str = typer.Argument(..., help="Path to a VERIFICATION.md file"),
) -> None:
    """Validate VERIFICATION frontmatter and contract-result alignment."""
    _run_frontmatter_validation(input_path, "verification")


@validate_app.command("review-ledger")
def validate_review_ledger_cmd(
    input_path: str = typer.Argument(..., help="Path to a review-ledger JSON file, or '-' for stdin"),
) -> None:
    """Validate a staged peer-review issue ledger."""
    from grd.mcp.paper.models import ReviewLedger

    payload = _load_json_document(input_path)
    try:
        ledger = ReviewLedger.model_validate(payload)
    except PydanticValidationError as exc:
        _raise_pydantic_schema_error(
            label="review-ledger",
            exc=exc,
            schema_reference="templates/paper/review-ledger-schema.md",
        )
    _output(ledger)


@validate_app.command("referee-decision")
def validate_referee_decision(
    input_path: str = typer.Argument(..., help="Path to a referee-decision JSON file, or '-' for stdin"),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Require staged peer-review artifact coverage in addition to recommendation-floor consistency",
    ),
    ledger_path: str | None = typer.Option(
        None,
        "--ledger",
        help="Optional path to the matching review-ledger JSON for cross-artifact consistency checks",
    ),
) -> None:
    """Validate a staged peer-review decision against hard recommendation gates."""
    from grd.core.referee_policy import RefereeDecisionInput, evaluate_referee_decision
    from grd.mcp.paper.models import ReviewLedger

    if input_path == "-" and ledger_path == "-":
        _error("Cannot read both referee-decision and review-ledger from stdin in the same command.")

    payload = _load_json_document(input_path)
    try:
        decision = RefereeDecisionInput.model_validate(payload)
    except PydanticValidationError as exc:
        _raise_pydantic_schema_error(
            label="referee-decision",
            exc=exc,
            schema_reference="templates/paper/referee-decision-schema.md",
        )

    review_ledger = None
    if ledger_path is not None:
        ledger_payload = _load_json_document(ledger_path)
        try:
            review_ledger = ReviewLedger.model_validate(ledger_payload)
        except PydanticValidationError as exc:
            _raise_pydantic_schema_error(
                label="review-ledger",
                exc=exc,
                schema_reference="templates/paper/review-ledger-schema.md",
            )

    report = evaluate_referee_decision(
        decision,
        strict=strict,
        review_ledger=review_ledger,
        project_root=_get_cwd(),
    )
    _output(report)
    if not report.valid:
        raise typer.Exit(code=1)


@validate_app.command("reproducibility-manifest")
def validate_reproducibility_manifest_cmd(
    input_path: str = typer.Argument(..., help="Path to a reproducibility-manifest JSON file, or '-' for stdin"),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Require review-ready coverage in addition to structural validity",
    ),
) -> None:
    """Validate a machine-readable reproducibility manifest."""
    from grd.core.reproducibility import validate_reproducibility_manifest

    payload = _load_json_document(input_path)
    result = validate_reproducibility_manifest(payload)
    _output(result)
    if not result.valid or (strict and (not result.ready_for_review or bool(result.warnings))):
        raise typer.Exit(code=1)
