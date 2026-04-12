"""Phase 1.5 integration: ``grd lean check`` → state.json verification_records.

The Phase 1 success gate from ge-9br: prove the evidence plumbing actually
works end-to-end. A simple theorem (``1 + 1 = 2``) is type-checked through
the client entry point, the ``LeanCheckResult`` is translated to a
``VerificationEvidence`` record, ``result_verify`` attaches it to an
intermediate result, and the state is flushed + reloaded from disk. We
assert the Lean provenance survives the round-trip.

A stub ``lean`` binary stands in for the real toolchain so CI and local test
runs don't require elan / Mathlib. The stub matches the pattern already used
by ``test_lean_client.py``.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from grd.core.lean import client as lean_client
from grd.core.lean.evidence import lean_result_to_evidence
from grd.core.lean.protocol import LeanCheckResult, LeanDiagnostic
from grd.core.results import result_add, result_verify
from grd.core.state import load_state_json, save_state_json


def _stub_lean(bin_dir: Path, *, exit_code: int = 0) -> Path:
    bin_dir.mkdir(parents=True, exist_ok=True)
    script = bin_dir / "lean"
    script.write_text(f"#!/bin/bash\nexit {exit_code}\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return script


def test_grd_lean_check_evidence_flows_into_state_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """End-to-end: typecheck a trivial theorem, persist evidence, re-load, assert."""
    (tmp_path / ".grd").mkdir()
    _stub_lean(tmp_path / "bin", exit_code=0)
    monkeypatch.setenv("PATH", str(tmp_path / "bin") + os.pathsep + os.environ["PATH"])

    state: dict = {}
    result_add(
        state,
        result_id="R-01",
        description="theorem test : 1 + 1 = 2 := by norm_num",
    )
    save_state_json(tmp_path, state)

    check = lean_client.check(
        code="theorem test : 1 + 1 = 2 := by norm_num",
        project_root=tmp_path,
        use_daemon=False,
    )
    assert check.ok is True, f"stub lean should succeed but got: {check}"
    assert check.backend == "subprocess"

    evidence = lean_result_to_evidence(check, evidence_path="artifacts/checks/R-01.lean")
    assert evidence.verifier == "grd-lean"
    assert evidence.method == "lean4_typecheck"
    assert evidence.confidence == "high"

    reloaded = load_state_json(tmp_path)
    assert reloaded is not None
    result_verify(
        reloaded,
        "R-01",
        verifier=evidence.verifier,
        method=evidence.method,
        confidence=evidence.confidence,
        evidence_path=evidence.evidence_path,
        notes=evidence.notes,
    )
    save_state_json(tmp_path, reloaded)

    raw = json.loads((tmp_path / ".grd" / "state.json").read_text(encoding="utf-8"))
    results = raw["intermediate_results"]
    assert len(results) == 1
    stored = results[0]
    assert stored["id"] == "R-01"
    assert stored["verified"] is True

    records = stored["verification_records"]
    assert len(records) == 1
    record = records[0]
    assert record["verifier"] == "grd-lean"
    assert record["method"] == "lean4_typecheck"
    assert record["confidence"] == "high"
    assert record["evidence_path"] == "artifacts/checks/R-01.lean"
    assert "backend=subprocess" in (record["notes"] or "")


def test_lean_check_failure_records_unreliable_confidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A failed type-check must NOT surface as high-confidence evidence."""
    (tmp_path / ".grd").mkdir()
    _stub_lean(tmp_path / "bin", exit_code=1)
    monkeypatch.setenv("PATH", str(tmp_path / "bin") + os.pathsep + os.environ["PATH"])

    check = lean_client.check(
        code="theorem nope : 1 + 1 = 3 := by norm_num",
        project_root=tmp_path,
        use_daemon=False,
    )
    assert check.ok is False
    evidence = lean_result_to_evidence(check)
    assert evidence.confidence == "unreliable"


def test_lean_result_to_evidence_confidence_mapping() -> None:
    ok = LeanCheckResult(ok=True, backend="subprocess")
    assert lean_result_to_evidence(ok).confidence == "high"

    warn = LeanCheckResult(
        ok=True,
        backend="subprocess",
        diagnostics=[LeanDiagnostic(severity="warning", message="unused var")],
    )
    assert lean_result_to_evidence(warn).confidence == "medium"

    elab_err = LeanCheckResult(
        ok=False,
        backend="subprocess",
        diagnostics=[LeanDiagnostic(severity="error", message="unsolved goals")],
    )
    assert lean_result_to_evidence(elab_err).confidence == "unreliable"

    not_found = LeanCheckResult(ok=False, error="lean_not_found", backend="subprocess")
    assert lean_result_to_evidence(not_found).confidence == "unreliable"


def test_lean_result_to_evidence_default_notes_embed_backend_and_diagnostics() -> None:
    r = LeanCheckResult(
        ok=True,
        backend="daemon",
        diagnostics=[LeanDiagnostic(severity="warning", message="x")],
    )
    notes = lean_result_to_evidence(r).notes or ""
    assert "backend=daemon" in notes
    assert "ok=True" in notes
    assert "diagnostics=1" in notes


def test_lean_result_to_evidence_preserves_explicit_notes_and_binding() -> None:
    r = LeanCheckResult(ok=True, backend="subprocess")
    e = lean_result_to_evidence(
        r,
        notes="manual override",
        claim_id="claim-pythagoras",
        deliverable_id="deliv-proof",
        acceptance_test_id="acc-smoke",
    )
    assert e.notes == "manual override"
    assert e.claim_id == "claim-pythagoras"
    assert e.deliverable_id == "deliv-proof"
    assert e.acceptance_test_id == "acc-smoke"
