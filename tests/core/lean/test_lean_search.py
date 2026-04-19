"""Tests for ``grd.core.lean.search`` — premise retrieval (ge-1r1).

All HTTP calls are stubbed via monkeypatching ``urllib.request.urlopen`` —
these tests exercise intent classification, response parsing, error handling,
and the parallel dispatch logic without hitting any real backend.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from grd.cli import app
from grd.core.lean.search import (
    SearchHit,
    SearchResponse,
    _lean_explore_search,
    _lean_finder_search,
    _loogle_search,
    classify_intent,
    search,
)

runner = CliRunner()


# ─── Intent classification ──────────────────────────────────────────────────


class TestClassifyIntent:
    def test_arrow_is_signature(self) -> None:
        assert classify_intent("(_ → _) → List _ → List _") == "signature"

    def test_ascii_arrow_is_signature(self) -> None:
        assert classify_intent("Nat -> Nat") == "signature"

    def test_turnstile_is_signature(self) -> None:
        assert classify_intent("⊢ False") == "signature"

    def test_forall_is_signature(self) -> None:
        assert classify_intent("∀ n, n + 0 = n") == "signature"

    def test_type_keyword_is_signature(self) -> None:
        assert classify_intent("Type → Prop") == "signature"

    def test_standalone_underscore_is_signature(self) -> None:
        assert classify_intent("_ → List _") == "signature"

    def test_dotted_camelcase_is_name(self) -> None:
        assert classify_intent("Nat.Prime") == "name"

    def test_dotted_lowercase_is_name(self) -> None:
        assert classify_intent("init.core") == "name"

    def test_multipart_dotted_is_name(self) -> None:
        assert classify_intent("List.map") == "name"

    def test_hash_check_is_name(self) -> None:
        assert classify_intent("#check Nat.Prime") == "name"

    def test_natural_language_is_prose(self) -> None:
        assert classify_intent("continuous function bounded on compact set") == "prose"

    def test_single_word_is_prose(self) -> None:
        assert classify_intent("prime") == "prose"

    def test_question_is_prose(self) -> None:
        assert classify_intent("is there a lemma about primes?") == "prose"


# ─── Backend: Loogle ────────────────────────────────────────────────────────


def _mock_urlopen(response_data: dict, status: int = 200):
    """Create a mock for urllib.request.urlopen that returns response_data."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(response_data).encode("utf-8")
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestLoogleSearch:
    def test_parses_hits(self) -> None:
        data = {
            "count": 2,
            "hits": [
                {
                    "name": "List.map",
                    "type": "{α β} → (α → β) → List α → List β",
                    "module": "Init.Prelude",
                    "doc": "Applies f to each element.",
                },
                {
                    "name": "List.filter",
                    "type": "{α} → (α → Bool) → List α → List α",
                    "module": "Init.Data.List",
                    "doc": None,
                },
            ],
        }
        with patch("grd.core.lean.search.urllib.request.urlopen", return_value=_mock_urlopen(data)):
            hits = _loogle_search("List.map")

        assert len(hits) == 2
        assert hits[0].name == "List.map"
        assert hits[0].backend == "loogle"
        assert hits[0].module == "Init.Prelude"
        assert hits[0].type is not None
        assert hits[0].source_url is not None
        assert "List.map" in hits[0].source_url

    def test_error_response_raises(self) -> None:
        data = {"error": "unknown identifier 'FooBar'", "suggestions": []}
        with patch("grd.core.lean.search.urllib.request.urlopen", return_value=_mock_urlopen(data)):
            with pytest.raises(ValueError, match="unknown identifier"):
                _loogle_search("FooBar")

    def test_empty_hits(self) -> None:
        data = {"count": 0, "hits": []}
        with patch("grd.core.lean.search.urllib.request.urlopen", return_value=_mock_urlopen(data)):
            hits = _loogle_search("nonexistent_xyz")
        assert hits == []

    def test_respects_limit(self) -> None:
        data = {"count": 5, "hits": [{"name": f"Hit{i}", "module": "M"} for i in range(5)]}
        with patch("grd.core.lean.search.urllib.request.urlopen", return_value=_mock_urlopen(data)):
            hits = _loogle_search("query", limit=2)
        assert len(hits) == 2


# ─── Backend: LeanExplore ───────────────────────────────────────────────────


class TestLeanExploreSearch:
    def test_parses_results(self) -> None:
        data = {
            "results": [
                {
                    "id": 1,
                    "name": "Nat.add_comm",
                    "module": "Mathlib.Data.Nat.Basic",
                    "docstring": "Addition is commutative.",
                    "source_link": "https://github.com/example/Basic.lean#L42",
                    "informalization": "The sum of two natural numbers is the same regardless of order.",
                },
            ],
            "count": 1,
        }
        with patch("grd.core.lean.search.urllib.request.urlopen", return_value=_mock_urlopen(data)):
            hits = _lean_explore_search("commutative addition", api_key="test-key")

        assert len(hits) == 1
        assert hits[0].name == "Nat.add_comm"
        assert hits[0].backend == "lean_explore"
        assert hits[0].source_url == "https://github.com/example/Basic.lean#L42"
        assert hits[0].informal is not None

    def test_missing_api_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("LEANEXPLORE_API_KEY", raising=False)
        with pytest.raises(ValueError, match="LEANEXPLORE_API_KEY"):
            _lean_explore_search("query")


# ─── Backend: Lean Finder ───────────────────────────────────────────────────


class TestLeanFinderSearch:
    def test_parses_dict_results(self) -> None:
        data = {
            "data": [
                [
                    {
                        "name": "IsContinuous.bounded_of_isCompact",
                        "formal_statement": "theorem ...",
                        "informal_statement": "A continuous function on a compact set is bounded.",
                        "url": "https://leanprover-community.github.io/mathlib4_docs/...",
                    },
                ]
            ]
        }
        with patch("grd.core.lean.search.urllib.request.urlopen", return_value=_mock_urlopen(data)):
            hits = _lean_finder_search("continuous bounded compact")

        assert len(hits) == 1
        assert hits[0].backend == "lean_finder"
        assert hits[0].informal is not None

    def test_parses_string_results(self) -> None:
        data = {"data": [["Nat.Prime.eq_one_or_self_of_dvd : ∀ p, p.Prime → ∀ n, n ∣ p → n = 1 ∨ n = p"]]}
        with patch("grd.core.lean.search.urllib.request.urlopen", return_value=_mock_urlopen(data)):
            hits = _lean_finder_search("prime divisor")

        assert len(hits) == 1
        assert hits[0].backend == "lean_finder"


# ─── Top-level search ───────────────────────────────────────────────────────


class TestSearch:
    def test_signature_query_routes_to_loogle(self) -> None:
        loogle_data = {"count": 1, "hits": [{"name": "List.map", "module": "Init"}]}
        with patch("grd.core.lean.search.urllib.request.urlopen", return_value=_mock_urlopen(loogle_data)):
            result = search("(_ → _) → List _ → List _")

        assert result.intent == "signature"
        assert "loogle" in result.backends_queried
        assert len(result.hits) == 1
        assert result.hits[0].backend == "loogle"

    def test_name_query_routes_to_loogle(self) -> None:
        loogle_data = {"count": 1, "hits": [{"name": "Nat.Prime", "module": "Mathlib"}]}
        with patch("grd.core.lean.search.urllib.request.urlopen", return_value=_mock_urlopen(loogle_data)):
            result = search("Nat.Prime")

        assert result.intent == "name"
        assert "loogle" in result.backends_queried

    def test_prose_query_routes_to_both_nl_backends(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Prose queries dispatch to LeanExplore + Lean Finder in parallel."""
        monkeypatch.setenv("LEANEXPLORE_API_KEY", "test-key")

        explore_data = {"results": [{"name": "Nat.add_comm", "module": "M"}], "count": 1}
        finder_data = {"data": [[{"name": "Nat.add_comm", "informal_statement": "comm", "url": "u"}]]}

        call_count = {"n": 0}

        def _mock_open(req, timeout=None):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            call_count["n"] += 1
            if "leanexplore" in url:
                return _mock_urlopen(explore_data)
            return _mock_urlopen(finder_data)

        with patch("grd.core.lean.search.urllib.request.urlopen", side_effect=_mock_open):
            result = search("commutative addition")

        assert result.intent == "prose"
        assert "lean_explore" in result.backends_queried
        assert "lean_finder" in result.backends_queried
        backends_in_hits = {h.backend for h in result.hits}
        assert "lean_explore" in backends_in_hits or "lean_finder" in backends_in_hits

    def test_backend_failure_recorded_as_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When a backend fails, the error is recorded but the search doesn't crash."""
        monkeypatch.delenv("LEANEXPLORE_API_KEY", raising=False)

        finder_data = {"data": [[{"name": "Foo", "informal_statement": "bar", "url": "u"}]]}

        def _mock_open(req, timeout=None):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            if "hf.space" in url:
                return _mock_urlopen(finder_data)
            raise Exception("connection refused")

        with patch("grd.core.lean.search.urllib.request.urlopen", side_effect=_mock_open):
            result = search("some prose query")

        # At least one error recorded (LeanExplore missing API key).
        assert len(result.errors) >= 1
        # Lean Finder should still have returned results.
        assert any(h.backend == "lean_finder" for h in result.hits)

    def test_response_model_roundtrips_json(self) -> None:
        resp = SearchResponse(
            query="test",
            intent="prose",
            hits=[SearchHit(name="Foo", backend="loogle")],
            backends_queried=["loogle"],
            elapsed_ms=42,
        )
        payload = resp.model_dump_json()
        roundtripped = SearchResponse.model_validate_json(payload)
        assert roundtripped == resp


# ─── CLI wiring ──────────────────────────────────────────────────────────────


class TestCLI:
    def test_search_emits_json_on_raw(self, monkeypatch: pytest.MonkeyPatch) -> None:
        loogle_data = {"count": 1, "hits": [{"name": "List.map", "type": "α → β", "module": "Init"}]}
        with patch("grd.core.lean.search.urllib.request.urlopen", return_value=_mock_urlopen(loogle_data)):
            result = runner.invoke(app, ["--raw", "lean", "search", "List.map"])

        assert result.exit_code == 0, result.stdout
        parsed = json.loads(result.stdout)
        assert parsed["intent"] == "name"
        assert len(parsed["hits"]) == 1
        assert parsed["hits"][0]["name"] == "List.map"

    def test_search_exit_1_no_results(self) -> None:
        """Name-style query that returns no Loogle hits → exit 1."""
        loogle_data = {"count": 0, "hits": []}
        with patch("grd.core.lean.search.urllib.request.urlopen", return_value=_mock_urlopen(loogle_data)):
            result = runner.invoke(app, ["--raw", "lean", "search", "Nonexistent.Xyz"])

        assert result.exit_code == 1
        parsed = json.loads(result.stdout)
        assert parsed["hits"] == []
