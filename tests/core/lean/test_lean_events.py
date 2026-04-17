"""Tests for grd.core.lean.events — progress event protocol and emitters.

Covers:
  * Event model serialization (NDJSON-safe)
  * Built-in emitters: jsonl_emitter, tty_emitter, noop_emitter
  * Callback wiring in bootstrap, prove, and verify_claim
"""

from __future__ import annotations

import json
from io import StringIO
from unittest.mock import patch

import pytest

from grd.core.lean.events import (
    DiagnosticEmitted,
    StageCompleted,
    StageStarted,
    TacticAttempted,
    jsonl_emitter,
    noop_emitter,
    tty_emitter,
    tty_finish,
)


# ---------------------------------------------------------------------------
# Model serialization
# ---------------------------------------------------------------------------


class TestEventModels:
    def test_stage_started_serializes(self):
        ev = StageStarted(stage="elan", detail="installing")
        d = ev.model_dump(mode="json")
        assert d["kind"] == "stage_started"
        assert d["stage"] == "elan"
        assert isinstance(d["ts"], int)

    def test_stage_completed_serializes(self):
        ev = StageCompleted(stage="elan", status="ok", elapsed_ms=123)
        d = ev.model_dump(mode="json")
        assert d["kind"] == "stage_completed"
        assert d["status"] == "ok"
        assert d["elapsed_ms"] == 123

    def test_tactic_attempted_serializes(self):
        ev = TacticAttempted(tactic="rfl", index=0, total=8, ok=True, elapsed_ms=50)
        d = ev.model_dump(mode="json")
        assert d["kind"] == "tactic_attempted"
        assert d["tactic"] == "rfl"
        assert d["ok"] is True

    def test_diagnostic_emitted_serializes(self):
        ev = DiagnosticEmitted(severity="error", message="type mismatch", line=5, column=10)
        d = ev.model_dump(mode="json")
        assert d["kind"] == "diagnostic_emitted"
        assert d["line"] == 5
        assert d["column"] == 10

    def test_all_events_are_json_round_trippable(self):
        events = [
            StageStarted(stage="x"),
            StageCompleted(stage="x", status="ok"),
            TacticAttempted(tactic="rfl", index=0, total=1, ok=False),
            DiagnosticEmitted(severity="warning", message="unused var"),
        ]
        for ev in events:
            text = json.dumps(ev.model_dump(mode="json"))
            parsed = json.loads(text)
            assert parsed["kind"] == ev.kind


# ---------------------------------------------------------------------------
# Built-in emitters
# ---------------------------------------------------------------------------


class TestJsonlEmitter:
    def test_writes_one_line_per_event(self):
        buf = StringIO()
        ev = StageStarted(stage="test")
        with patch("sys.stdout", buf):
            jsonl_emitter(ev)
        lines = buf.getvalue().strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["kind"] == "stage_started"
        assert parsed["stage"] == "test"

    def test_multiple_events_produce_multiple_lines(self):
        buf = StringIO()
        with patch("sys.stdout", buf):
            jsonl_emitter(StageStarted(stage="a"))
            jsonl_emitter(StageCompleted(stage="a", status="ok"))
        lines = [l for l in buf.getvalue().strip().split("\n") if l]
        assert len(lines) == 2
        assert json.loads(lines[0])["kind"] == "stage_started"
        assert json.loads(lines[1])["kind"] == "stage_completed"


class TestTtyEmitter:
    def test_writes_to_stderr(self):
        buf = StringIO()
        ev = StageStarted(stage="bootstrap")
        with patch("sys.stderr", buf):
            tty_emitter(ev)
        output = buf.getvalue()
        assert "bootstrap" in output
        assert output.startswith("\r")

    def test_stage_completed_shows_status(self):
        buf = StringIO()
        ev = StageCompleted(stage="elan", status="ok", elapsed_ms=42)
        with patch("sys.stderr", buf):
            tty_emitter(ev)
        output = buf.getvalue()
        assert "OK" in output
        assert "42ms" in output

    def test_tactic_attempted_shows_result(self):
        buf = StringIO()
        ev = TacticAttempted(tactic="simp", index=2, total=8, ok=False)
        with patch("sys.stderr", buf):
            tty_emitter(ev)
        output = buf.getvalue()
        assert "simp" in output
        assert "fail" in output
        assert "3/8" in output


class TestTtyFinish:
    def test_clears_status_line(self):
        buf = StringIO()
        with patch("sys.stderr", buf):
            tty_finish()
        output = buf.getvalue()
        assert output.startswith("\r")
        assert output.strip() == ""


class TestNoopEmitter:
    def test_does_nothing(self):
        # Just ensure it doesn't raise
        noop_emitter(StageStarted(stage="x"))
        noop_emitter(StageCompleted(stage="x", status="ok"))


# ---------------------------------------------------------------------------
# Callback wiring — bootstrap
# ---------------------------------------------------------------------------


class TestBootstrapEvents:
    def test_run_bootstrap_emits_stage_events(self, tmp_path, monkeypatch):
        from grd.core.lean import bootstrap
        from grd.core.lean import env as lean_env_mod
        from grd.core.lean.protocol import BootstrapStageResult

        # Stub all stage functions to return ok without doing anything
        def _fake_stage(*_args, **_kwargs):
            return BootstrapStageResult(name="fake", status="ok", elapsed_ms=1)

        for stage_name in (
            "_stage_elan", "_stage_toolchain", "_stage_pantograph",
            "_stage_graphviz", "_stage_tectonic", "_stage_mathlib_cache",
            "_stage_leandojo",
        ):
            monkeypatch.setattr(bootstrap, stage_name, _fake_stage)

        monkeypatch.setattr(bootstrap, "load_env", lambda _p: {})
        monkeypatch.setattr(bootstrap, "save_env", lambda _p, _d: None)
        monkeypatch.setattr(lean_env_mod, "env_file_path", lambda _p: tmp_path / "lean-env.json")

        (tmp_path / ".grd").mkdir(exist_ok=True)

        collected = []
        report = bootstrap.run_bootstrap(tmp_path, on_event=collected.append)
        assert report.ok

        started = [e for e in collected if isinstance(e, StageStarted)]
        completed = [e for e in collected if isinstance(e, StageCompleted)]
        assert len(started) == 7  # 7 stages
        assert len(completed) == 7
        # Each completed event has a status
        assert all(c.status == "ok" for c in completed)


# ---------------------------------------------------------------------------
# Callback wiring — prove
# ---------------------------------------------------------------------------


class TestProveEvents:
    def test_prove_statement_emits_tactic_events(self, tmp_path, monkeypatch):
        from grd.core.lean.protocol import LeanCheckResult
        from grd.core.lean import prove as prove_mod

        call_count = 0

        def _fake_check(*, code, **_kwargs):
            nonlocal call_count
            call_count += 1
            # Third tactic succeeds
            return LeanCheckResult(ok=(call_count == 3), elapsed_ms=10)

        monkeypatch.setattr(prove_mod, "lean_check", _fake_check)

        collected = []
        result = prove_mod.prove_statement(
            "1 + 1 = 2",
            project_root=tmp_path,
            tactics=["rfl", "decide", "norm_num", "ring"],
            on_event=collected.append,
        )
        assert result.ok
        assert len(collected) == 3  # stopped at third (success)
        assert all(isinstance(e, TacticAttempted) for e in collected)
        assert collected[0].tactic == "rfl"
        assert collected[0].ok is False
        assert collected[2].tactic == "norm_num"
        assert collected[2].ok is True
        assert all(e.total == 4 for e in collected)

    def test_prove_statement_no_callback_still_works(self, tmp_path, monkeypatch):
        from grd.core.lean.protocol import LeanCheckResult
        from grd.core.lean import prove as prove_mod

        monkeypatch.setattr(
            prove_mod, "lean_check",
            lambda *, code, **_kw: LeanCheckResult(ok=True, elapsed_ms=1),
        )
        result = prove_mod.prove_statement(
            "1 + 1 = 2", project_root=tmp_path, tactics=["rfl"],
        )
        assert result.ok  # No crash — on_event defaults to None


# ---------------------------------------------------------------------------
# Callback wiring — verify_claim
# ---------------------------------------------------------------------------


class TestVerifyClaimEvents:
    def test_verify_claim_emits_pipeline_events(self, tmp_path, monkeypatch):
        from grd.core.lean.autoformalize import pipeline as pipeline_mod
        from grd.core.lean.autoformalize.blueprint import BlueprintContext
        from grd.core.lean.autoformalize.candidates import Candidate
        from grd.core.lean.autoformalize.config import AutoformalizeConfig
        from grd.core.lean.autoformalize.decision import FaithfulnessDecision
        from grd.core.lean.autoformalize.faithfulness import FaithfulnessReport
        from grd.core.lean.autoformalize.index import NameIndex
        from grd.core.lean.autoformalize.repair import RepairOutcome

        # Stub extract
        monkeypatch.setattr(
            pipeline_mod, "extract_blueprint_context",
            lambda **_kw: BlueprintContext(claim="test", conventions={}),
        )
        # Stub index
        monkeypatch.setattr(
            pipeline_mod, "load_default_index",
            lambda _p, _c: NameIndex.empty(),
        )
        # Stub generate
        monkeypatch.setattr(
            pipeline_mod, "generate_candidates",
            lambda **_kw: [Candidate(index=0, source="theorem T : True := sorry", raw="stub", temperature=0.0)],
        )
        # Stub repair — returns a compiled candidate
        monkeypatch.setattr(
            pipeline_mod, "repair_candidate",
            lambda **_kw: RepairOutcome(ok=True, final_source="theorem T : True := trivial", steps=[]),
        )
        # Stub faithfulness
        monkeypatch.setattr(
            pipeline_mod, "assess_faithfulness",
            lambda **_kw: FaithfulnessReport(
                back_translation="For all T, T is true",
                similarity=0.95,
                backend="jaccard",
            ),
        )
        # Stub decision
        monkeypatch.setattr(
            pipeline_mod, "decide_faithfulness",
            lambda **_kw: FaithfulnessDecision(
                outcome="auto_accept", similarity=0.95,
                reason="similarity 0.950 >= auto-accept threshold 0.85",
            ),
        )

        class MockLLM:
            def generate(self, prompt):
                return "stub"

        collected = []
        result = pipeline_mod.verify_claim(
            claim="test claim",
            project_root=tmp_path,
            llm=MockLLM(),
            config=AutoformalizeConfig(),
            on_event=collected.append,
        )

        started = [e for e in collected if isinstance(e, StageStarted)]
        completed = [e for e in collected if isinstance(e, StageCompleted)]

        stage_names = [e.stage for e in started]
        assert "extract" in stage_names
        assert "retrieve" in stage_names
        assert "generate" in stage_names
        assert "compile_repair" in stage_names
        assert "faithfulness" in stage_names
        assert "gate" in stage_names

        # Each started has a matching completed
        assert len(started) == len(completed)
