"""LLM backend abstraction for the autoformalization pipeline.

Defines a narrow ``LLMBackend`` protocol so the pipeline can:

* be tested without network (monkeypatch ``MockLLM``),
* run against real Claude Sonnet 4.5 when the anthropic SDK is installed
  (``AnthropicLLM``), and
* grow an ensemble path (Opus + GPT-5 + DeepSeek-Prover) without rewriting the
  consumers — the pipeline only sees ``LLMBackend``.

``classify_compile_error`` maps Lean diagnostics to the error taxonomy from
AUTOFORMALIZATION.md §7 so the APOLLO repair loop can tailor its follow-up
prompts. The taxonomy is data, not code — keeping it here in ``llm.py`` keeps
the repair loop free of heuristic detail.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable

from grd.core.lean.protocol import LeanCheckResult, LeanDiagnostic

logger = logging.getLogger(__name__)

__all__ = [
    "AnthropicLLM",
    "ErrorKind",
    "LLMBackend",
    "LLMMessage",
    "MockLLM",
    "build_back_translation_messages",
    "build_candidate_messages",
    "build_repair_messages",
    "classify_compile_error",
]


ErrorKind = Literal[
    "hallucinated_identifier",
    "lean3_syntax",
    "universe",
    "arg_order",
    "typeclass_missing",
    "namespace",
    "elaboration",
    "unknown",
]
"""Lean compile-error classes from AUTOFORMALIZATION.md §7 (auto-detectable half)."""


@dataclass(frozen=True)
class LLMMessage:
    """One chat message sent to an LLM backend.

    We keep the shape identical to the Anthropic/OpenAI conventions so the
    backends can pass it through verbatim without re-packing.
    """

    role: Literal["user", "assistant", "system"]
    content: str


@runtime_checkable
class LLMBackend(Protocol):
    """Minimal LLM surface used by the pipeline.

    ``complete`` returns one response; callers ask for ``n`` completions by
    calling ``generate`` (default implementation loops ``complete``). Keeping
    the API this small means a real Anthropic client only has to implement
    ``complete``.
    """

    def complete(self, *, system: str, messages: list[LLMMessage], temperature: float = 0.7) -> str:
        """Return a single assistant message text. Raise on transport failures."""
        ...


@dataclass
class MockLLM:
    """Deterministic in-memory LLM used by tests and the --no-llm CLI mode.

    ``responses`` is a round-robin queue — every call to ``complete`` pops the
    next entry. An empty queue raises so tests notice when the pipeline asked
    for more completions than the fixture supplied. ``calls`` records every
    invocation so assertions can inspect the assembled prompt.
    """

    responses: list[str] = field(default_factory=list)
    calls: list[tuple[str, list[LLMMessage], float]] = field(default_factory=list)

    def complete(self, *, system: str, messages: list[LLMMessage], temperature: float = 0.7) -> str:
        self.calls.append((system, list(messages), temperature))
        if not self.responses:
            raise RuntimeError("MockLLM: no more scripted responses")
        return self.responses.pop(0)


class AnthropicLLM:
    """Thin adapter over the anthropic SDK, imported lazily.

    We do NOT add ``anthropic`` as a required dependency — the CLI default is
    ``--no-llm`` (returns a deterministic "skipped" result) and users who want
    real autoformalization install the ``autoformalize`` optional extra. This
    keeps import-time overhead at zero for the 99% of phases that never touch
    formal proofs.
    """

    def __init__(self, *, model_id: str, api_key: str | None = None) -> None:
        try:
            from anthropic import Anthropic  # noqa: PLC0415  (lazy import intentional)
        except ImportError as exc:  # pragma: no cover - dep not installed
            raise RuntimeError(
                "anthropic SDK is not installed. Install with "
                "`pip install 'get-research-done[autoformalize]'` to enable real LLM calls."
            ) from exc
        self._client = Anthropic(api_key=api_key) if api_key else Anthropic()
        self._model_id = model_id

    def complete(self, *, system: str, messages: list[LLMMessage], temperature: float = 0.7) -> str:
        # Anthropic's Messages API takes system as a separate arg and does not
        # accept a role=system entry in the messages list.
        payload = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        response = self._client.messages.create(  # type: ignore[union-attr]
            model=self._model_id,
            max_tokens=2048,
            temperature=temperature,
            system=system,
            messages=payload,
        )
        # anthropic returns a list of content blocks; concatenate text blocks.
        out: list[str] = []
        for block in response.content:
            text = getattr(block, "text", None)
            if text:
                out.append(text)
        return "".join(out)


# ─── Prompt composition ─────────────────────────────────────────────────────


_LEAN4_ONLY_REMINDER = (
    "Output Lean 4 syntax only. Never emit `begin...end` blocks, `by { }`, or "
    "other Lean 3 idioms — frontier models commonly slip back into Lean 3, and "
    "this project rejects such output."
)


def _format_conventions(conventions: dict[str, object] | None) -> str:
    if not conventions:
        return "(no active convention lock — flag this to the user if it matters)"
    lines = []
    for key, value in conventions.items():
        if value in (None, "", "NOT-SPECIFIED"):
            continue
        lines.append(f"- {key}: {value}")
    return "\n".join(lines) or "(convention lock present but empty)"


def _format_names(sample: list[str], total: int) -> str:
    if not sample:
        return "(no Mathlib4/PhysLean name index available)"
    head = ", ".join(sample[:20])
    return f"{total} known identifiers; sample: {head}"


def build_candidate_messages(
    *,
    claim: str,
    conventions: dict[str, object] | None,
    index_sample: list[str],
    index_total: int,
    physics: bool,
) -> tuple[str, list[LLMMessage]]:
    """DRAFT-SKETCH-PROVE framing for stage 3 candidate generation.

    Returns ``(system, messages)`` — callers pass this straight to
    ``LLMBackend.complete``. The prompt bakes in:

    * convention lock (biggest lever vs. silent convention drift per §8.5),
    * Mathlib4 (and optionally PhysLean) name-index sample (grounded retrieval),
    * explicit Lean-4-only reminder (frontier models still emit Lean 3).
    """
    library_line = (
        "Mathlib4 + PhysLean (physics — prefer PhysLean identifiers for field theory, "
        "gauge, spacetime, quantum mechanics)"
        if physics
        else "Mathlib4"
    )
    system = (
        "You are an autoformalization assistant for GRD (Get Research Done). "
        "Given an informal research claim, produce a candidate Lean 4 "
        "`theorem` statement that is type-correct against the pinned "
        f"{library_line} snapshot. Follow DRAFT-SKETCH-PROVE: first sketch the "
        "structure of the statement, then emit the final Lean 4 theorem. Do not "
        "include a proof body — leave ` := sorry`. " + _LEAN4_ONLY_REMINDER
    )
    user = (
        f"INFORMAL CLAIM:\n{claim}\n\n"
        f"ACTIVE CONVENTION LOCK:\n{_format_conventions(conventions)}\n\n"
        f"KNOWN IDENTIFIERS (ground your output against these):\n"
        f"{_format_names(index_sample, index_total)}\n\n"
        "Return ONE Lean 4 `theorem` with a descriptive name, ending in `:= sorry`. "
        "Put the theorem inside a fenced ```lean code block."
    )
    return system, [LLMMessage(role="user", content=user)]


def build_repair_messages(
    *,
    claim: str,
    previous_source: str,
    lean_result: LeanCheckResult,
    error_kind: ErrorKind,
    conventions: dict[str, object] | None,
) -> tuple[str, list[LLMMessage]]:
    """APOLLO-style repair prompt for stage 4.

    The LLM is shown the failing source, the classified error kind, and the
    first few diagnostics verbatim so it can target the fix. We tell the model
    explicitly what *kind* of fix is expected (e.g. "rename the hallucinated
    identifier" vs. "rewrite in Lean 4 syntax") — that shaping buys a large
    fraction of the APOLLO win from §5.
    """
    diag_lines = _format_diagnostics(lean_result.diagnostics)
    guidance = _ERROR_KIND_GUIDANCE.get(
        error_kind,
        "Identify the failing line and make a minimal, targeted edit.",
    )
    system = (
        "You are repairing a candidate Lean 4 theorem that failed to "
        "type-check. Emit the smallest, most targeted edit that could make it "
        "compile. " + _LEAN4_ONLY_REMINDER
    )
    user = (
        f"INFORMAL CLAIM:\n{claim}\n\n"
        f"ACTIVE CONVENTION LOCK:\n{_format_conventions(conventions)}\n\n"
        f"FAILING SOURCE:\n```lean\n{previous_source.strip()}\n```\n\n"
        f"LEAN DIAGNOSTICS:\n{diag_lines}\n\n"
        f"ERROR CLASS: {error_kind}\nREPAIR GUIDANCE: {guidance}\n\n"
        "Return the full repaired Lean 4 source inside a fenced ```lean code block. "
        "Keep the theorem name unchanged unless the rename is the whole fix."
    )
    return system, [LLMMessage(role="user", content=user)]


def build_back_translation_messages(*, lean_source: str) -> tuple[str, list[LLMMessage]]:
    """Stage 5 back-translation: Lean 4 theorem → English paraphrase.

    A deliberately minimal prompt — the point is to catch convention / quantifier
    / domain-of-validity drift by recovering what the Lean statement *actually*
    says. We explicitly ask the model not to invent hypotheses that aren't in
    the Lean source, otherwise the SBERT similarity check is fooled.
    """
    system = (
        "You back-translate Lean 4 theorem statements into a single sentence "
        "of plain English. Describe EXACTLY what the Lean statement says — do "
        "not add hypotheses, context, or intuition that isn't in the source."
    )
    user = (
        f"LEAN 4 STATEMENT:\n```lean\n{lean_source.strip()}\n```\n\n"
        "Produce one clear English sentence that states the same mathematical "
        "claim. No preamble, no explanation, no list — just the sentence."
    )
    return system, [LLMMessage(role="user", content=user)]


_ERROR_KIND_GUIDANCE: dict[ErrorKind, str] = {
    "hallucinated_identifier": (
        "The identifier does not exist in Mathlib4 / PhysLean. Replace it with "
        "a known name, or open the correct namespace so the resolver finds it."
    ),
    "lean3_syntax": (
        "The source uses Lean 3 syntax. Convert to Lean 4: `by { ... }` → "
        "`by ...`, `begin ... end` → `by ...`, remove `import tactic.*`, etc."
    ),
    "universe": (
        "Universe levels disagree. Prefer the simpler candidate (drop explicit "
        "universe polymorphism unless the statement truly needs it)."
    ),
    "arg_order": (
        "Argument order or implicit/explicit markers are wrong. Align the call site to the declaration signature."
    ),
    "typeclass_missing": (
        "A typeclass instance is missing. Add the required `[Inst]` binder or "
        "import the module that provides the instance."
    ),
    "namespace": (
        "The identifier is in a different namespace. Either qualify it (`Nat.Prime` vs `Prime`) or open the namespace."
    ),
    "elaboration": (
        "Elaboration failed for a reason not covered by the other categories. "
        "Simplify the statement, remove decorative casts, and try again."
    ),
    "unknown": (
        "Error class could not be auto-detected. Read the diagnostic literally "
        "and apply the smallest edit consistent with it."
    ),
}


def _format_diagnostics(diagnostics: list[LeanDiagnostic]) -> str:
    if not diagnostics:
        return "(no diagnostics — orchestration error?)"
    shown = diagnostics[:3]  # enough to steer repair, not so many we blow tokens
    lines = []
    for d in shown:
        loc = ""
        if d.line is not None:
            loc = f" at line {d.line}"
            if d.column is not None:
                loc += f", col {d.column}"
        lines.append(f"- [{d.severity}]{loc}: {d.message.strip().splitlines()[0] if d.message else ''}")
    if len(diagnostics) > 3:
        lines.append(f"... ({len(diagnostics) - 3} more)")
    return "\n".join(lines)


# ─── Error classification ───────────────────────────────────────────────────


_LEAN3_MARKERS = (
    "begin ",
    "begin\n",
    "end\n",
    "by { ",
    "by {\n",
    "import tactic.",
)


def classify_compile_error(result: LeanCheckResult, source: str) -> ErrorKind:
    """Map a failing ``LeanCheckResult`` to the §7 error taxonomy.

    We look at the orchestration error first (timeout/missing Lean are their
    own beast), then scan diagnostic messages with cheap keyword heuristics.
    The taxonomy itself is derived from [Autoformalization in the Wild, 2025]
    and IndiMathBench; no attempt at a true ML classifier — the repair prompt
    handles nuance.
    """
    if not result.diagnostics and result.error is not None:
        return "elaboration"

    # Lean-3 bleed is often detectable in the source itself regardless of the
    # specific diagnostic, because Lean 4 will complain about the block syntax
    # before elaborating the interesting identifiers.
    lowered_src = source.lower()
    if any(marker in lowered_src for marker in _LEAN3_MARKERS):
        return "lean3_syntax"

    joined = " \n".join((d.message or "") for d in result.diagnostics).lower()

    if "unknown identifier" in joined or "unknown constant" in joined:
        return "hallucinated_identifier"
    if "failed to synthesize" in joined and "instance" in joined:
        return "typeclass_missing"
    if "universe" in joined and ("mismatch" in joined or "level" in joined):
        return "universe"
    if "expected" in joined and ("got" in joined or "but" in joined) and "argument" in joined:
        return "arg_order"
    if "unknown namespace" in joined or "ambiguous" in joined:
        return "namespace"
    if joined.strip():
        return "elaboration"
    return "unknown"
