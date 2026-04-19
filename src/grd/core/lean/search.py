"""Premise retrieval for Lean 4 / Mathlib: Loogle + LeanExplore + Lean Finder.

``search(query)`` classifies the query by intent and dispatches to the right
backend(s):

- **type signature** (contains ``→`` / ``->`` / wildcards / structural syntax)
  → Loogle (exact type-pattern matching)
- **identifier** (dot-separated CamelCase name like ``List.map``)
  → Loogle (name search)
- **natural language** (everything else)
  → LeanExplore *and* Lean Finder in parallel, results shown side-by-side

Each backend is a thin HTTP wrapper over the upstream service's public API.
Failures are recorded in ``SearchResponse.errors`` — a down backend never
hard-fails the search, it just returns fewer results.

No external Python dependencies beyond stdlib (``urllib``).
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "SearchHit",
    "SearchError",
    "SearchResponse",
    "classify_intent",
    "search",
]


# ─── Models ──────────────────────────────────────────────────────────────────

SearchBackend = Literal["loogle", "lean_explore", "lean_finder"]
QueryIntent = Literal["signature", "name", "prose"]


class SearchHit(BaseModel):
    """One result from a search backend."""

    model_config = ConfigDict(extra="forbid")

    name: str
    type: str | None = None
    module: str | None = None
    doc: str | None = None
    source_url: str | None = None
    informal: str | None = Field(
        default=None,
        description="Informal / natural-language description of the result (from LeanExplore / Lean Finder).",
    )
    backend: SearchBackend


class SearchError(BaseModel):
    """Non-fatal error from one backend."""

    model_config = ConfigDict(extra="forbid")

    backend: SearchBackend
    message: str


class SearchResponse(BaseModel):
    """Aggregate result from one or more backends."""

    model_config = ConfigDict(extra="forbid")

    query: str
    intent: QueryIntent
    hits: list[SearchHit] = Field(default_factory=list)
    backends_queried: list[str] = Field(default_factory=list)
    errors: list[SearchError] = Field(default_factory=list)
    elapsed_ms: int = 0


# ─── Intent classification ──────────────────────────────────────────────────

# Lean type-signature indicators: arrows, turnstile, underscores as wildcards.
_SIGNATURE_PATTERN = re.compile(
    r"→|->|⊢|∀|∃|Prop|Sort|Type"
    r"|(?:^|\s)_(?:\s|$)"  # standalone underscore as wildcard
)

# Lean identifier: dot-separated, at least one CamelCase or all-lower segment.
_IDENT_PATTERN = re.compile(
    r"^[A-Z][A-Za-z0-9]*(?:\.[A-Za-z][A-Za-z0-9]*)+$"  # Nat.Prime, List.map
    r"|^[a-z][a-zA-Z0-9]*(?:\.[a-z][a-zA-Z0-9]*)+$"  # init.core
    r"|^#check\s"  # #check prefix
)


def classify_intent(query: str) -> QueryIntent:
    """Classify a search query as signature, name, or prose.

    This is the "never asks the user to choose a backend" heuristic from the
    bead.  It's intentionally conservative: anything that *might* be a type
    signature gets routed to Loogle, where it will still work.
    """
    q = query.strip()
    if _SIGNATURE_PATTERN.search(q):
        return "signature"
    if _IDENT_PATTERN.match(q):
        return "name"
    return "prose"


# ─── Backend: Loogle ────────────────────────────────────────────────────────

_LOOGLE_URL = "https://loogle.lean-lang.org/json"
_LOOGLE_DOC_BASE = "https://leanprover-community.github.io/mathlib4_docs/find/#doc/"


def _loogle_search(
    query: str,
    *,
    timeout_s: float = 10.0,
    limit: int = 20,
) -> list[SearchHit]:
    """Query Loogle's public JSON API."""
    url = f"{_LOOGLE_URL}?{urllib.parse.urlencode({'q': query})}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if "error" in data:
        raise ValueError(data["error"])

    hits: list[SearchHit] = []
    for h in (data.get("hits") or [])[:limit]:
        name = h.get("name", "")
        module = h.get("module")
        doc_url = f"{_LOOGLE_DOC_BASE}{urllib.parse.quote(name)}" if name else None
        hits.append(
            SearchHit(
                name=name,
                type=(h.get("type") or "").strip() or None,
                module=module,
                doc=h.get("doc"),
                source_url=doc_url,
                backend="loogle",
            )
        )
    return hits


# ─── Backend: LeanExplore ───────────────────────────────────────────────────

_LEAN_EXPLORE_URL = "https://www.leanexplore.com/api/v2/search"


def _lean_explore_search(
    query: str,
    *,
    timeout_s: float = 10.0,
    limit: int = 10,
    api_key: str | None = None,
) -> list[SearchHit]:
    """Query LeanExplore's public API (requires ``LEANEXPLORE_API_KEY``)."""
    key = api_key or os.environ.get("LEANEXPLORE_API_KEY", "")
    if not key:
        raise ValueError(
            "LEANEXPLORE_API_KEY not set — get one at https://www.leanexplore.com and export LEANEXPLORE_API_KEY=<key>"
        )

    params = urllib.parse.urlencode({"q": query, "limit": limit})
    url = f"{_LEAN_EXPLORE_URL}?{params}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {key}",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    hits: list[SearchHit] = []
    for r in (data.get("results") or [])[:limit]:
        hits.append(
            SearchHit(
                name=r.get("name", ""),
                module=r.get("module"),
                doc=r.get("docstring"),
                source_url=r.get("source_link"),
                informal=r.get("informalization"),
                backend="lean_explore",
            )
        )
    return hits


# ─── Backend: Lean Finder ───────────────────────────────────────────────────

_LEAN_FINDER_URL = "https://delta-lab-ai-lean-finder.hf.space/run/retrieve"


def _lean_finder_search(
    query: str,
    *,
    timeout_s: float = 15.0,
    limit: int = 10,
) -> list[SearchHit]:
    """Query the Lean Finder Gradio space via its REST API.

    Lean Finder is hosted on HuggingFace Spaces as a Gradio app; no API key
    required.  The endpoint may be slow (~5-15s cold start) or down — callers
    must handle timeouts gracefully.
    """
    payload = json.dumps({"data": [query, limit, "Normal"]}).encode("utf-8")
    req = urllib.request.Request(
        _LEAN_FINDER_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    raw_results = data.get("data", [])
    hits: list[SearchHit] = []
    # Gradio returns the results as the first element of the data array.
    if raw_results and isinstance(raw_results[0], list):
        for entry in raw_results[0][:limit]:
            if isinstance(entry, dict):
                name = entry.get("name", "")
                hits.append(
                    SearchHit(
                        name=name,
                        doc=entry.get("formal_statement"),
                        informal=entry.get("informal_statement"),
                        source_url=entry.get("url"),
                        backend="lean_finder",
                    )
                )
            elif isinstance(entry, str):
                # Fallback: some Gradio responses are plain strings.
                hits.append(
                    SearchHit(
                        name=entry.split(" : ")[0].strip() if " : " in entry else entry[:80],
                        doc=entry,
                        backend="lean_finder",
                    )
                )
    elif raw_results and isinstance(raw_results[0], str):
        # Single-string response: the whole output is rendered text.
        text = raw_results[0]
        for line in text.strip().splitlines():
            line = line.strip()
            if line and "⊢" not in line:
                hits.append(SearchHit(name=line[:120], backend="lean_finder"))

    return hits


# ─── Top-level search ───────────────────────────────────────────────────────


def search(
    query: str,
    *,
    limit: int = 10,
    timeout_s: float = 10.0,
) -> SearchResponse:
    """Search Lean 4 / Mathlib by dispatching to the right backend(s).

    Signature / name queries → Loogle only.
    Prose queries → LeanExplore + Lean Finder in parallel (side-by-side).
    """
    intent = classify_intent(query)
    start = time.monotonic()

    all_hits: list[SearchHit] = []
    errors: list[SearchError] = []
    backends: list[str] = []

    if intent in ("signature", "name"):
        backends.append("loogle")
        try:
            all_hits.extend(_loogle_search(query, timeout_s=timeout_s, limit=limit))
        except Exception as exc:
            errors.append(SearchError(backend="loogle", message=str(exc)))
    else:
        # Prose: query both NL backends in parallel.
        backends.extend(["lean_explore", "lean_finder"])

        def _run_lean_explore() -> tuple[str, list[SearchHit]]:
            return "lean_explore", _lean_explore_search(query, timeout_s=timeout_s, limit=limit)

        def _run_lean_finder() -> tuple[str, list[SearchHit]]:
            return "lean_finder", _lean_finder_search(query, timeout_s=timeout_s + 5, limit=limit)

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(_run_lean_explore), pool.submit(_run_lean_finder)]
            for future in as_completed(futures):
                try:
                    backend_name, hits = future.result()
                    all_hits.extend(hits)
                except Exception as exc:
                    # Figure out which backend failed from the exception context.
                    backend_name = _infer_backend_from_error(exc)
                    errors.append(SearchError(backend=backend_name, message=str(exc)))

    elapsed_ms = int((time.monotonic() - start) * 1000)

    return SearchResponse(
        query=query,
        intent=intent,
        hits=all_hits,
        backends_queried=backends,
        errors=errors,
        elapsed_ms=elapsed_ms,
    )


def _infer_backend_from_error(exc: Exception) -> SearchBackend:
    """Best-effort: figure out which backend threw from the URL in the error."""
    msg = str(exc)
    if "leanexplore" in msg.lower() or "LEANEXPLORE" in msg:
        return "lean_explore"
    if "lean-finder" in msg.lower() or "hf.space" in msg.lower():
        return "lean_finder"
    if "loogle" in msg.lower():
        return "loogle"
    # Fallback — lean_explore is tried first and fails most commonly (API key).
    return "lean_explore"
