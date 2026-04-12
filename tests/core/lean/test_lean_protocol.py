"""Tests for grd.core.lean.protocol wire-format models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from grd.core.lean.protocol import (
    LeanCheckRequest,
    LeanCheckResult,
    LeanDiagnostic,
    LeanEnvStatus,
)


class TestLeanCheckRequest:
    def test_default_op_is_check(self) -> None:
        req = LeanCheckRequest(code="example : 1 = 1 := rfl")
        assert req.op == "check"
        assert req.imports == []
        assert req.timeout_s == 30.0

    def test_timeout_bounds_enforced(self) -> None:
        with pytest.raises(ValidationError):
            LeanCheckRequest(code="x", timeout_s=0.0)
        with pytest.raises(ValidationError):
            LeanCheckRequest(code="x", timeout_s=10_000.0)

    def test_extra_fields_forbidden(self) -> None:
        # Extra fields would silently mask client/server version skew.
        with pytest.raises(ValidationError):
            LeanCheckRequest.model_validate({"op": "check", "code": "x", "bogus": True})

    def test_op_ping_and_shutdown_allowed(self) -> None:
        assert LeanCheckRequest(op="ping").op == "ping"
        assert LeanCheckRequest(op="shutdown").op == "shutdown"

    def test_unknown_op_rejected(self) -> None:
        with pytest.raises(ValidationError):
            LeanCheckRequest.model_validate({"op": "nuke"})


class TestLeanDiagnostic:
    def test_severity_enum_enforced(self) -> None:
        with pytest.raises(ValidationError):
            LeanDiagnostic(severity="fatal", message="boom")  # type: ignore[arg-type]

    def test_all_location_fields_optional(self) -> None:
        d = LeanDiagnostic(severity="info", message="hi")
        assert d.file is None
        assert d.line is None
        assert d.column is None


class TestLeanCheckResult:
    def test_json_roundtrip_preserves_diagnostics(self) -> None:
        original = LeanCheckResult(
            ok=False,
            diagnostics=[
                LeanDiagnostic(
                    severity="error",
                    file="/tmp/x.lean",
                    line=3,
                    column=12,
                    message="unknown identifier 'foo'",
                ),
            ],
            stderr="some stderr",
            exit_code=1,
            elapsed_ms=42,
            backend="subprocess",
        )
        payload = original.model_dump_json()
        roundtripped = LeanCheckResult.model_validate_json(payload)
        assert roundtripped == original


class TestLeanEnvStatus:
    def test_defaults_are_conservative(self) -> None:
        s = LeanEnvStatus(lean_found=False)
        assert s.elan_found is False
        assert s.lake_found is False
        assert s.pantograph_available is False
        assert s.daemon_running is False
