"""Isar-style narrative rendering of Lean 4 tactic proofs (ge-epra / P3-1).

As AI-generated proofs dominate 2026+, reviewability of million-line tactic
scripts becomes table stakes. Isabelle's Isar shows the way — ``have X by Y``,
``thus Z from W``, ``finally show Q``. This module takes a Lean 4 source file,
extracts one or more theorem declarations, and emits a narrative Markdown or
LaTeX rendering alongside the original tactic script.

**Not a verifier.** This is a reviewability tool: no daemon, no kernel check,
no faithfulness guarantee. The narrative is a lightweight heuristic translation
of the tactic layer, tuned to help a human skim a proof. If the Lean source
isn't well-formed, we best-effort the parse and surface the raw text.

Architecture:

    parse.py logic lives inline below — a newline/brace-aware scanner that
    finds top-level ``theorem``/``lemma`` blocks, splits the signature from
    the proof body, and tokenizes a ``by`` block into nested tactic steps.
    Term-mode proofs (``:= foo``) are reported as a single step with the
    term verbatim and a narrative that quotes the term.

The renderer is intentionally monolithic: one pass over the parsed tree
emits Markdown or LaTeX. Both formats share a common narrative template
so copy evolves in one place.
"""

from __future__ import annotations

import re
import textwrap
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ProofRenderFormat",
    "RenderedProof",
    "RenderProofResult",
    "TacticStep",
    "TheoremBlock",
    "extract_theorems",
    "render_proof",
]


ProofRenderFormat = Literal["markdown", "latex", "json"]
ProofMode = Literal["tactic", "term", "unknown"]

_DECL_KEYWORDS = ("theorem", "lemma", "example", "def")
_BULLETS = ("·", "•")


# ─── Models ──────────────────────────────────────────────────────────────────


class TacticStep(BaseModel):
    """One tactic invocation rendered into narrative form.

    Nesting is explicit: a ``have h : P := by ...`` or a bullet block
    produces a step whose ``sub_steps`` list carries the inner tactics.
    Renderers walk depth-first to emit indented prose.
    """

    model_config = ConfigDict(extra="forbid")

    tactic: str = Field(..., description="Original tactic source, whitespace-trimmed.")
    narrative: str = Field(..., description="Isar-style narrative gloss for this tactic.")
    depth: int = Field(0, ge=0, description="Nesting depth (0 = top-level of the proof).")
    sub_steps: list[TacticStep] = Field(
        default_factory=list,
        description="Nested steps (inner by-block, bullet sub-proof, or case-split branch).",
    )


class TheoremBlock(BaseModel):
    """One theorem (or lemma/example) extracted from the source file."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(..., description="Declaration keyword — theorem, lemma, example, def.")
    name: str = Field("", description="Declared identifier, empty for anonymous examples.")
    signature: str = Field(..., description="Everything from the keyword through ':=', whitespace-normalized.")
    proof_mode: ProofMode = Field(..., description="tactic (``by ...``), term (direct term), or unknown.")
    raw_proof: str = Field(..., description="Verbatim proof body (after the ':=' separator).")
    steps: list[TacticStep] = Field(default_factory=list, description="Top-level tactic steps.")
    warnings: list[str] = Field(default_factory=list, description="Reviewability flags (e.g. ``sorry``).")


class RenderedProof(BaseModel):
    """One theorem plus its emitted narrative text for a single format."""

    model_config = ConfigDict(extra="forbid")

    theorem: TheoremBlock
    narrative: str = Field(..., description="Rendered Markdown or LaTeX text for this theorem.")


class RenderProofResult(BaseModel):
    """CLI result payload for ``grd lean render-proof``."""

    model_config = ConfigDict(extra="forbid")

    source_path: str = Field(..., description="Path that was read, as supplied by the caller.")
    format: ProofRenderFormat = Field(..., description="Emitted format.")
    theorems: list[RenderedProof] = Field(default_factory=list)
    skipped: list[str] = Field(
        default_factory=list,
        description="Names of theorems in the file that were filtered out by --theorem.",
    )
    warnings: list[str] = Field(default_factory=list, description="File-level warnings (e.g. no theorems found).")

    @property
    def combined_narrative(self) -> str:
        """Concatenate all per-theorem narratives with blank separators."""
        return "\n\n".join(rendered.narrative for rendered in self.theorems).rstrip() + "\n"


# ─── Parsing ────────────────────────────────────────────────────────────────


def _strip_lean_comments(source: str) -> str:
    """Remove ``--`` line comments and ``/- ... -/`` block comments.

    Block comments nest in Lean 4 — the scanner tracks depth. Strings and
    char literals are respected minimally (``"..."`` with backslash escapes)
    so a ``--`` inside a string doesn't trigger comment mode.
    """
    result: list[str] = []
    i = 0
    n = len(source)
    block_depth = 0
    in_line_comment = False
    in_string = False
    while i < n:
        ch = source[i]
        nxt = source[i + 1] if i + 1 < n else ""
        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
                result.append("\n")
            i += 1
            continue
        if block_depth > 0:
            if ch == "-" and nxt == "/":
                block_depth -= 1
                i += 2
                continue
            if ch == "/" and nxt == "-":
                block_depth += 1
                i += 2
                continue
            if ch == "\n":
                result.append("\n")
            i += 1
            continue
        if in_string:
            result.append(ch)
            if ch == "\\" and i + 1 < n:
                result.append(source[i + 1])
                i += 2
                continue
            if ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            result.append(ch)
            i += 1
            continue
        if ch == "-" and nxt == "-":
            in_line_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "-":
            block_depth += 1
            i += 2
            continue
        result.append(ch)
        i += 1
    return "".join(result)


_DECL_RE = re.compile(
    r"(?m)^(?P<kw>theorem|lemma|example|def)\b",
)


def _find_decl_starts(source: str) -> list[tuple[int, str]]:
    """Return (offset, keyword) for every top-level theorem/lemma/example.

    We consider an occurrence "top-level" when it starts at column 0 of a
    line. Anything more ambitious would require a real Lean parser; this
    heuristic catches the vast majority of real-world formalizations.
    """
    return [(match.start(), match.group("kw")) for match in _DECL_RE.finditer(source)]


def _find_assignment(source: str, start: int, end: int) -> int | None:
    """Return the offset of the top-level ``:=`` between start and end, or None.

    Skips ``:=`` that appear inside balanced ``(...)``, ``[...]``, ``{...}``,
    ``⟨...⟩`` and string literals. This lets us split a theorem declaration
    into signature and body even when the signature contains default values
    or structure notation with its own ``:=``.
    """
    depth_paren = depth_bracket = depth_brace = depth_angle = 0
    in_string = False
    i = start
    while i < end - 1:
        ch = source[i]
        nxt = source[i + 1]
        if in_string:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            i += 1
            continue
        if ch == "(":
            depth_paren += 1
        elif ch == ")":
            depth_paren -= 1
        elif ch == "[":
            depth_bracket += 1
        elif ch == "]":
            depth_bracket -= 1
        elif ch == "{":
            depth_brace += 1
        elif ch == "}":
            depth_brace -= 1
        elif ch == "⟨":
            depth_angle += 1
        elif ch == "⟩":
            depth_angle -= 1
        if (
            depth_paren == 0
            and depth_bracket == 0
            and depth_brace == 0
            and depth_angle == 0
            and ch == ":"
            and nxt == "="
        ):
            return i
        i += 1
    return None


def _next_decl_start(source: str, after: int) -> int:
    """Return the start offset of the next top-level declaration after ``after``.

    Looks for lines beginning with ``theorem``/``lemma``/``example``/``def``
    or ``#check`` / ``#eval`` / ``namespace`` / ``end`` (terminators). If no
    such marker exists, returns ``len(source)``.
    """
    terminators = ("#check", "#eval", "#print", "namespace", "end", "section", "open", "import", "variable", "instance")
    for match in re.finditer(r"(?m)^[ \t]*(\S+)", source[after:]):
        token = match.group(1).strip()
        if token.startswith(_DECL_KEYWORDS + terminators):
            return after + match.start()
    return len(source)


def _extract_name_from_signature(signature: str, kind: str) -> str:
    """Pull the declared name out of a signature like ``theorem foo {α : Type} ...``."""
    stripped = signature.strip()
    if not stripped:
        return ""
    remainder = stripped[len(kind) :].lstrip()
    match = re.match(r"([A-Za-z_\u03b1-\u03c9\u0391-\u03a9][\w.'\u03b1-\u03c9\u0391-\u03a9]*)", remainder)
    return match.group(1) if match else ""


def extract_theorems(source: str) -> list[TheoremBlock]:
    """Parse a Lean source string into a list of theorem blocks with rendered steps.

    Callers typically won't use this directly — :func:`render_proof` is the
    full pipeline — but it's useful for tooling that wants the structured
    tree without a rendered string.
    """
    cleaned = _strip_lean_comments(source)
    decls = _find_decl_starts(cleaned)
    blocks: list[TheoremBlock] = []
    for index, (offset, kind) in enumerate(decls):
        next_start = decls[index + 1][0] if index + 1 < len(decls) else _next_decl_start(cleaned, offset + 1)
        chunk = cleaned[offset:next_start]
        assignment_rel = _find_assignment(chunk, 0, len(chunk))
        if assignment_rel is None:
            continue
        signature = chunk[:assignment_rel].strip()
        body = chunk[assignment_rel + 2 :].strip()
        proof_mode: ProofMode
        steps: list[TacticStep]
        warnings: list[str] = []
        if body.startswith("by"):
            proof_mode = "tactic"
            # Drop ``by``, trim only leading newlines so each line keeps its
            # indentation relative to the block. ``dedent`` then rebases the
            # block at column 0 so nested tactics keep a positive delta.
            tactic_block = textwrap.dedent(body[2:].lstrip("\n"))
            steps = _parse_tactic_block(tactic_block, depth=0)
        elif body:
            proof_mode = "term"
            steps = [
                TacticStep(
                    tactic=body,
                    narrative=f"The proof is the term ``{_one_line(body)}``.",
                    depth=0,
                )
            ]
        else:
            proof_mode = "unknown"
            steps = []
            warnings.append("empty proof body")
        if "sorry" in body:
            warnings.append("proof contains `sorry` — incomplete")
        if "admit" in re.split(r"\W+", body):
            warnings.append("proof contains `admit` — incomplete")
        name = _extract_name_from_signature(signature, kind)
        blocks.append(
            TheoremBlock(
                kind=kind,
                name=name,
                signature=_normalize_whitespace(signature),
                proof_mode=proof_mode,
                raw_proof=body,
                steps=steps,
                warnings=warnings,
            )
        )
    return blocks


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _one_line(text: str, limit: int = 120) -> str:
    collapsed = _normalize_whitespace(text)
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1] + "…"


# ─── Tactic tokenization ─────────────────────────────────────────────────────


def _split_tactic_lines(block: str) -> list[tuple[int, str]]:
    """Split a ``by`` block into ``(indent, tactic_text)`` pairs.

    Lean 4 tactic blocks are indentation-sensitive. We preserve indentation
    for nesting detection and split on newlines, then further split each
    line on top-level ``;`` separators (respecting brackets). Bullet
    characters (``·``, ``•``) open a sub-block captured as a single step
    whose body is the bullet's indented continuation.
    """
    lines = block.splitlines()
    result: list[tuple[int, str]] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        if not stripped:
            i += 1
            continue
        indent = len(line) - len(stripped)
        if stripped.startswith(_BULLETS):
            bullet_body, consumed = _collect_bullet_block(lines, i, indent)
            result.append((indent, bullet_body))
            i += consumed
            continue
        for token in _split_top_level_semicolons(stripped):
            token = token.strip()
            if token:
                result.append((indent, token))
        i += 1
    return result


def _collect_bullet_block(lines: list[str], start: int, bullet_indent: int) -> tuple[str, int]:
    """Grab a ``· ...`` bullet plus every more-indented continuation line."""
    first = lines[start]
    collected = [first]
    j = start + 1
    while j < len(lines):
        candidate = lines[j]
        stripped = candidate.lstrip()
        if not stripped:
            collected.append(candidate)
            j += 1
            continue
        indent = len(candidate) - len(stripped)
        if indent <= bullet_indent and not stripped.startswith(_BULLETS):
            break
        if indent <= bullet_indent and stripped.startswith(_BULLETS):
            break
        collected.append(candidate)
        j += 1
    return "\n".join(collected), j - start


def _split_top_level_semicolons(line: str) -> list[str]:
    depth = 0
    in_string = False
    tokens: list[str] = []
    current: list[str] = []
    i = 0
    while i < len(line):
        ch = line[i]
        if in_string:
            current.append(ch)
            if ch == "\\" and i + 1 < len(line):
                current.append(line[i + 1])
                i += 2
                continue
            if ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            current.append(ch)
            i += 1
            continue
        if ch in "([{⟨":
            depth += 1
        elif ch in ")]}⟩":
            depth -= 1
        if ch == ";" and depth == 0:
            tokens.append("".join(current))
            current = []
            i += 1
            continue
        current.append(ch)
        i += 1
    tail = "".join(current).strip()
    if tail:
        tokens.append(tail)
    return tokens


def _parse_tactic_block(block: str, *, depth: int) -> list[TacticStep]:
    """Convert a tactic block string into a list of :class:`TacticStep`."""
    steps: list[TacticStep] = []
    pairs = _split_tactic_lines(block)
    if not pairs:
        return steps
    base_indent = min(indent for indent, _ in pairs)
    i = 0
    while i < len(pairs):
        indent, text = pairs[i]
        if text.lstrip().startswith(_BULLETS):
            bullet_text = text.lstrip()
            # Strip the leading bullet and any whitespace.
            body = re.sub(r"^[·•]\s*", "", bullet_text)
            sub_steps = _parse_tactic_block(body, depth=depth + 1)
            narrative = "Focus on this subgoal." if sub_steps else "Focus on this subgoal (empty branch)."
            steps.append(
                TacticStep(
                    tactic="·",
                    narrative=narrative,
                    depth=depth,
                    sub_steps=sub_steps,
                )
            )
            i += 1
            continue
        sub_steps: list[TacticStep] = []
        # Detect an inline ``have h : P := by ...`` with continuation.
        have_match = re.match(
            r"^(have|suffices|show|let)\b\s*(?P<name>[\w\u03b1-\u03c9\u0391-\u03a9']*)?\s*(?::\s*(?P<type>.+?))?\s*:=\s*by\b(?P<tail>.*)$",
            text,
        )
        if have_match and have_match.group("tail").strip():
            # The tail is the first tactic of an inline by-block. Gather any
            # more-indented continuation lines.
            body_lines = [have_match.group("tail").strip()]
            j = i + 1
            while j < len(pairs) and pairs[j][0] > indent:
                body_lines.append(pairs[j][1])
                j += 1
            sub_steps = _parse_tactic_block("\n".join(body_lines), depth=depth + 1)
            text_for_narrative = re.sub(r"\s*:=\s*by\s.*$", " := by …", text)
            narrative = _narrate_tactic(text_for_narrative)
            steps.append(
                TacticStep(
                    tactic=text,
                    narrative=narrative,
                    depth=depth,
                    sub_steps=sub_steps,
                )
            )
            i = j
            continue
        narrative = _narrate_tactic(text)
        # Gather ``| pat => tac`` continuation lines from the same indent
        # level — they are match alternatives of the preceding tactic
        # (``induction ... with``, ``cases ... with``, ``match ... with``).
        # Each alternative bundles any more-indented body lines into its
        # own sub-step block.
        alternatives: list[tuple[str, list[str]]] = []
        j = i + 1
        while j < len(pairs):
            alt_indent, alt_text = pairs[j]
            if alt_indent != indent or not alt_text.lstrip().startswith("|"):
                break
            body_lines: list[str] = []
            j += 1
            while j < len(pairs):
                body_indent, body_text = pairs[j]
                if body_indent <= indent:
                    break
                if body_text.lstrip().startswith(("|", "·", "•")) and body_indent == indent:
                    break
                body_lines.append(" " * body_indent + body_text)
                j += 1
            alternatives.append((alt_text, body_lines))
        if alternatives:
            alt_sub_steps: list[TacticStep] = []
            for alt_header, body_lines in alternatives:
                if body_lines:
                    inner_steps = _parse_tactic_block(
                        textwrap.dedent("\n".join(body_lines)),
                        depth=depth + 2,
                    )
                else:
                    inner_steps = []
                alt_sub_steps.append(
                    TacticStep(
                        tactic=alt_header,
                        narrative=_narrate_match_alternative(alt_header),
                        depth=depth + 1,
                        sub_steps=inner_steps,
                    )
                )
            steps.append(
                TacticStep(
                    tactic=text,
                    narrative=narrative,
                    depth=depth,
                    sub_steps=alt_sub_steps,
                )
            )
            i = j
            continue
        _ = base_indent  # reserved for future relative-depth decisions
        steps.append(TacticStep(tactic=text, narrative=narrative, depth=depth))
        i += 1
    return steps


def _narrate_match_alternative(line: str) -> str:
    """Gloss a ``| pat => tac`` match alternative into prose."""
    stripped = line.lstrip().lstrip("|").strip()
    if "=>" in stripped:
        pattern, _, body = stripped.partition("=>")
        tactic_narr = _narrate_tactic(body.strip()) if body.strip() else "(no tactic)"
        return f"Case `{_one_line(pattern.strip())}`: {tactic_narr}"
    return f"Case `{_one_line(stripped)}`."


# ─── Narrative translation ──────────────────────────────────────────────────


def _narrate_tactic(text: str) -> str:
    """Translate one tactic invocation into an Isar-style prose sentence.

    The mapping is heuristic and lossy on purpose: the goal is to help a
    reviewer skim a proof, not to reconstruct a formal Isar document.
    Every tactic we don't recognize falls through to a quoted form so the
    narrative never silently swallows source.
    """
    stripped = text.strip().rstrip(",")
    if not stripped:
        return ""
    low = stripped.lower()
    head_match = re.match(r"^([A-Za-z_]+\??)\b(.*)$", stripped)
    head = head_match.group(1) if head_match else stripped
    rest = head_match.group(2).strip() if head_match else ""

    if head == "intro":
        return f"Introduce `{rest or '_'}`."
    if head == "intros":
        return f"Introduce {rest or 'the hypotheses'}."
    if head == "rintro":
        return f"Destructuring-introduce {rest or 'the hypotheses'}."
    if head == "exact":
        return f"Conclude by `{_one_line(rest)}`."
    if head in {"exact?", "apply?"}:
        return f"Search for a finishing term via `{head}`."
    if head == "apply":
        return f"Apply `{_one_line(rest)}`, reducing to its premises."
    if head == "refine":
        return f"Refine with `{_one_line(rest)}`, leaving `_` goals for the remaining parts."
    if head in {"rw", "rewrite", "erw"}:
        return f"Rewrite using `{_one_line(rest)}`."
    if head == "simp" or head == "simp_all":
        if rest:
            return f"Simplify using `{_one_line(rest)}`."
        return "Simplify with `simp`."
    if head == "norm_num":
        return "Normalize the numerical goal."
    if head == "ring":
        return "Close the goal by ring arithmetic."
    if head == "linarith":
        return "Close the goal by linear arithmetic."
    if head == "nlinarith":
        return "Close the goal by nonlinear arithmetic."
    if head == "omega":
        return "Close the goal with `omega` (integer/natural linear arithmetic)."
    if head == "decide":
        return "Decide the goal by `decide`."
    if head == "aesop":
        return "Dispatch the goal with `aesop`."
    if head == "trivial":
        return "Trivial."
    if head == "assumption":
        return "By assumption."
    if head == "rfl":
        return "By reflexivity."
    if head == "contradiction":
        return "Derive a contradiction from the hypotheses."
    if head in {"cases", "rcases"}:
        return f"Analyze the cases of `{_one_line(rest)}`."
    if head == "induction":
        return f"Proceed by induction on `{_one_line(rest)}`."
    if head == "split" or head == "constructor":
        return "Split the goal into its constructor pieces."
    if head == "obtain":
        return f"Obtain `{_one_line(rest)}`."
    if head == "have":
        name_match = re.match(r"(?P<name>\w+)?\s*:\s*(?P<type>.+?)\s*:=\s*(?P<rhs>.+)$", rest)
        if name_match:
            name = name_match.group("name") or "this"
            type_ = _one_line(name_match.group("type"))
            rhs = _one_line(name_match.group("rhs"))
            if rhs.startswith("by"):
                return f"Establish `{name} : {type_}` (proved below)."
            return f"Establish `{name} : {type_}` from `{rhs}`."
        return f"Establish `{_one_line(rest)}`."
    if head == "show":
        return f"It suffices to show `{_one_line(rest)}`."
    if head == "suffices":
        return f"It suffices to have `{_one_line(rest)}`."
    if head == "let":
        return f"Let `{_one_line(rest)}`."
    if head == "change":
        return f"Change the goal to `{_one_line(rest)}`."
    if head == "sorry":
        return "**Gap: `sorry`** — this subgoal is unproved."
    if head == "admit":
        return "**Gap: `admit`** — this subgoal is accepted without proof."
    if head == "specialize":
        return f"Specialize `{_one_line(rest)}`."
    if head == "push_neg":
        return "Push negations inward."
    if head == "by_contra" or head == "by_contradiction":
        return f"Argue by contradiction: assume `{_one_line(rest) or '¬ goal'}` and derive a contradiction."
    if head == "use":
        return f"Provide witness `{_one_line(rest)}`."
    if head == "ext":
        return f"Apply extensionality{(' to ' + _one_line(rest)) if rest else ''}."
    if head == "funext":
        return f"Apply function extensionality{(' at ' + _one_line(rest)) if rest else ''}."
    if head == "subst":
        return f"Substitute `{_one_line(rest)}`."
    if head == "trans" or head == "transitivity":
        return f"By transitivity through `{_one_line(rest)}`."
    if head == "symm":
        return "Swap sides by symmetry."
    if low.startswith("·") or low.startswith("•"):
        return "Focus on this subgoal."
    return f"Apply tactic `{_one_line(stripped)}`."


# ─── Rendering ──────────────────────────────────────────────────────────────


def _render_markdown(block: TheoremBlock) -> str:
    lines: list[str] = []
    title = block.name or "(anonymous)"
    lines.append(f"### `{block.kind} {title}`")
    lines.append("")
    lines.append("**Statement.**")
    lines.append("")
    lines.append("```lean")
    lines.append(block.signature)
    lines.append("```")
    lines.append("")
    if block.warnings:
        lines.append("> ⚠ " + "; ".join(block.warnings))
        lines.append("")
    lines.append("**Narrative proof.**")
    lines.append("")
    if not block.steps:
        lines.append("_(no proof body to narrate)_")
        lines.append("")
    else:
        _emit_markdown_steps(block.steps, lines, ordinal_stack=[])
    lines.append("")
    lines.append("**Lean tactic script.**")
    lines.append("")
    lines.append("```lean")
    lines.append(block.raw_proof.rstrip())
    lines.append("```")
    return "\n".join(lines)


def _emit_markdown_steps(
    steps: list[TacticStep],
    lines: list[str],
    *,
    ordinal_stack: list[int],
) -> None:
    for index, step in enumerate(steps, start=1):
        indent = "  " * step.depth
        ordinal = ".".join(str(n) for n in [*ordinal_stack, index])
        lines.append(f"{indent}{ordinal}. {step.narrative}")
        if step.tactic and step.narrative != step.tactic:
            lines.append(f"{indent}   `{_one_line(step.tactic, limit=200)}`")
        if step.sub_steps:
            _emit_markdown_steps(step.sub_steps, lines, ordinal_stack=[*ordinal_stack, index])


def _render_latex(block: TheoremBlock) -> str:
    lines: list[str] = []
    title = block.name or "anonymous"
    safe_title = _latex_escape(title)
    lines.append(f"\\subsection*{{{block.kind.capitalize()} \\texttt{{{safe_title}}}}}")
    lines.append("")
    lines.append("\\paragraph{Statement.}")
    lines.append("\\begin{verbatim}")
    lines.append(block.signature)
    lines.append("\\end{verbatim}")
    if block.warnings:
        escaped = [_narrative_to_latex(warning) for warning in block.warnings]
        lines.append("\\textbf{Warnings:} " + "; ".join(escaped) + ".")
    lines.append("")
    lines.append("\\paragraph{Narrative proof.}")
    if not block.steps:
        lines.append("\\emph{(no proof body to narrate)}")
    else:
        lines.append("\\begin{enumerate}")
        _emit_latex_steps(block.steps, lines)
        lines.append("\\end{enumerate}")
    lines.append("")
    lines.append("\\paragraph{Lean tactic script.}")
    lines.append("\\begin{verbatim}")
    lines.append(block.raw_proof.rstrip())
    lines.append("\\end{verbatim}")
    return "\n".join(lines)


def _emit_latex_steps(steps: list[TacticStep], lines: list[str]) -> None:
    for step in steps:
        narrative = _narrative_to_latex(step.narrative)
        tactic = _latex_escape(_one_line(step.tactic, limit=200)) if step.tactic else ""
        if tactic and step.narrative != step.tactic:
            lines.append(f"  \\item {narrative} \\quad \\texttt{{{tactic}}}")
        else:
            lines.append(f"  \\item {narrative}")
        if step.sub_steps:
            lines.append("  \\begin{enumerate}")
            _emit_latex_steps(step.sub_steps, lines)
            lines.append("  \\end{enumerate}")


def _narrative_to_latex(text: str) -> str:
    """Translate the shared narrative (Markdown-ish) into LaTeX markup.

    The narrative is authored with ``**bold**`` and ``` `code` ``` so the
    Markdown renderer can pass it through unchanged. For LaTeX we swap
    those primitives for ``\\textbf{...}`` and ``\\texttt{...}`` and then
    escape the remaining special characters.
    """
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        if text.startswith("**", i):
            end = text.find("**", i + 2)
            if end != -1:
                out.append("\\textbf{")
                out.append(_latex_escape(text[i + 2 : end]))
                out.append("}")
                i = end + 2
                continue
        if text[i] == "`":
            end = text.find("`", i + 1)
            if end != -1:
                out.append("\\texttt{")
                out.append(_latex_escape(text[i + 1 : end]))
                out.append("}")
                i = end + 1
                continue
        out.append(_latex_escape(text[i]))
        i += 1
    return "".join(out)


_LATEX_ESCAPES = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def _latex_escape(text: str) -> str:
    return "".join(_LATEX_ESCAPES.get(ch, ch) for ch in text)


# ─── Public entry point ──────────────────────────────────────────────────────


def render_proof(
    source: str,
    *,
    source_path: str = "<string>",
    theorem: str | None = None,
    format: ProofRenderFormat = "markdown",
) -> RenderProofResult:
    """Parse ``source`` and produce rendered narrative(s) for its theorems.

    Args:
        source: Raw Lean 4 source text.
        source_path: Display label for the file (echoed back in the result).
        theorem: Optional name filter. If provided and not found, the result
            will list available names in ``warnings`` rather than erroring —
            callers decide how strict to be.
        format: ``markdown``, ``latex``, or ``json`` (the last emits empty
            narrative strings; the caller is expected to consume the
            structured ``theorems`` list directly).
    """
    blocks = extract_theorems(source)
    selected: list[TheoremBlock]
    skipped: list[str] = []
    warnings: list[str] = []
    if theorem:
        matching = [block for block in blocks if block.name == theorem]
        if not matching:
            available = ", ".join(sorted({b.name for b in blocks if b.name})) or "(none)"
            warnings.append(f"theorem {theorem!r} not found; available: {available}")
        selected = matching
        skipped = [block.name for block in blocks if block.name != theorem and block.name]
    else:
        selected = blocks
    if not blocks:
        warnings.append("no theorem/lemma/example declarations found")
    rendered: list[RenderedProof] = []
    for block in selected:
        if format == "markdown":
            narrative = _render_markdown(block)
        elif format == "latex":
            narrative = _render_latex(block)
        else:
            narrative = ""
        rendered.append(RenderedProof(theorem=block, narrative=narrative))
    return RenderProofResult(
        source_path=source_path,
        format=format,
        theorems=rendered,
        skipped=skipped,
        warnings=warnings,
    )
