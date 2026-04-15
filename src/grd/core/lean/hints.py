"""Error-explanation layer for Lean diagnostics.

Maps raw Lean 4 diagnostic messages to one-line human-cause + suggested-action
hints. Populated automatically by ``parse_diagnostics`` so every surface
(check / prove / verify-claim / daemon) inherits explanations for free.

Design contract for a hint:

* One line, ≤180 chars. Read well as a bullet under the raw message.
* Cause *first*, then the concrete next action.
* No Lean jargon without a gloss — the cold-mathematician audience is the
  reason this layer exists.
* Avoid prescribing a specific fix when Lean's own message already says what
  to do (e.g. "Try 'import X'") — those messages are already actionable.

Seeded with the top-5 error classes from the nitro UX study (ge-m0m, Q9):
``synthInstance``, ``type mismatch``, ``heartbeats``, ``deep recursion``,
universe levels. Supplemented with ~25 further patterns covering honorable
mentions and common day-one failures so the layer covers ~80% of user-visible
failures (per UX-STUDY.md §P0-1).

``hint_for_message`` is pure and case-insensitive on the matching side.
Patterns are ordered: the first matching rule wins, so narrower patterns
must come before broader ones. Add new entries at the top of their category.
"""

from __future__ import annotations

import re
from typing import Final

__all__ = ["hint_for_message", "HINT_RULES"]


# Each rule is (compiled_pattern, hint). Patterns match anywhere in the
# (possibly multi-line) diagnostic message. Order matters: narrower patterns
# come first inside each category, and the first match wins.
_HINT_RULES_RAW: Final[list[tuple[str, str]]] = [
    # ── Top-5 from nitro Q9 ──────────────────────────────────────────────
    # 1. failed to synthesize instance — typeclass resolution failure.
    #    Covers Decidable/DecidableEq/Repr and arbitrary class names.
    (
        r"failed to synthesize\s+instance\s+Decidable\b",
        "Lean can't decide this proposition automatically. Add `[DecidableEq α]` "
        "or `[Decidable p]` to your hypotheses, or prove the instance manually.",
    ),
    (
        r"failed to synthesize\s+instance\s+DecidableEq\b",
        "No `DecidableEq` for this type. Add `[DecidableEq α]` to the theorem's "
        "type class arguments, or use `deriving DecidableEq` on the inductive type.",
    ),
    (
        r"failed to synthesize",
        "Typeclass search couldn't find an instance. Check imports (Mathlib "
        "instances live behind `import Mathlib`), supply a `[Class α]` binder, "
        "or run `set_option trace.Meta.synthInstance true` to see what was tried.",
    ),
    # 2. type mismatch — lean4#333 class, types often look identical.
    (
        r"type mismatch.*?has type.*?but\s+is\s+expected\s+to\s+have\s+type",
        "Types differ even if they print identically (lean4#333) — usually "
        "coercions, universes, or implicit args. Try `set_option pp.all true` "
        "to see the real shapes, or add an explicit `show <type>` ascription.",
    ),
    (
        r"type mismatch",
        "Lean got a different type than it expected here. Read the `has type` "
        "vs `expected` lines carefully; if they look identical, enable "
        "`set_option pp.all true` to surface hidden universe/instance diffs.",
    ),
    # 3. Heartbeat timeouts.
    (
        r"\(deterministic\)\s+timeout.*?heartbeats",
        "Lean ran out of compute budget for this elaboration step. Bump with "
        "`set_option maxHeartbeats 400000` at the top of the file, or split the "
        "tactic into smaller steps. Run `grd lean prove` for automatic retry.",
    ),
    (
        r"maximum number of heartbeats",
        "Lean ran out of compute budget (heartbeats ≈ reductions). Raise via "
        "`set_option maxHeartbeats 400000`, or use `count_heartbeats in <tac>` "
        "to find the step actually spending the budget.",
    ),
    # 4. Deep recursion.
    (
        r"deep recursion detected",
        "Stack overflow inside Lean's elaborator — almost always a typeclass "
        "loop. Check for instances that synthesize themselves (e.g. `inst : A` "
        "built from `A`) and remove or guard the cycle.",
    ),
    # 5. Universe errors.
    (
        r"invalid universe level",
        "Lean's universe solver can't unify these levels. Make a universe "
        "variable explicit with `universe u` + `{α : Type u}`, or annotate "
        "the definition with `.{u}`.",
    ),
    (
        r"universe level\s+\d+\s+not\s*(?:<=|≤)\s*\d+",
        "Universe mismatch — a `Type u` is being used where a smaller universe "
        "was expected. Make universes explicit (`universe u`, `Type u`) or add "
        "`.{u}` to the definition's universe list.",
    ),
    (
        r"stuck at solving universe constraint",
        "Lean's universe unifier is stuck. Declare a `universe u` and annotate "
        "the polymorphic definitions with `.{u}` so the constraint is explicit.",
    ),
    # ── Missing-imports / project-setup family ───────────────────────────
    (
        r"unknown identifier\s+['`]?(ℕ|ℤ|ℚ|ℝ|ℂ)['`]?",
        "This Unicode numeric type lives in Mathlib. Add `import Mathlib` (or "
        "the specific `Mathlib.Data.Real.Basic` etc.) at the top of the file.",
    ),
    (
        r"unknown identifier",
        "Lean doesn't know this name. Likely a missing `import`, a typo, or "
        "a scoped notation — try `import Mathlib` for Mathlib names or check "
        "capitalization and namespacing.",
    ),
    (
        r"unknown (?:constant|declaration|theorem|lemma)",
        "Name exists nowhere Lean can see. Check for renames in Mathlib "
        "(search Loogle), a missing `import`, or `open` the right namespace.",
    ),
    (
        r"unknown (?:tactic|identifier)\s+['`]?(?:polyrith|nlinarith|linarith|positivity|field_simp|ring|norm_num)",
        "This Mathlib tactic isn't available. Add `import Mathlib.Tactic` (or "
        "`import Mathlib` for the full suite) to the top of the file.",
    ),
    (
        r"unknown package ['`]?Mathlib",
        "Lean ran outside a Lake project or without a Mathlib dependency. Run "
        "`grd lean bootstrap` to set up a project, or `cd` into a directory "
        "with a `lakefile.lean`/`lakefile.toml` that requires Mathlib.",
    ),
    (
        r"unknown module",
        "Lean can't find this module. Check the module name spelling and that "
        "the providing package is in your `lakefile` `require`s; run `lake "
        "update` and `lake build` after edits.",
    ),
    (
        r"Invalid Lake configuration",
        "Lake failed to load the manifest — often a network error fetching a "
        "dependency (lean4#6827), not your config. Re-run with network access, "
        "or check `lake-manifest.json` for a stale revision.",
    ),
    (
        r"lake\s*:\s*command not found|lean\s*:\s*command not found",
        "Lean toolchain isn't on `PATH`. Run `/grd:lean-bootstrap` to install "
        "elan + Lean, or source your shell init (`~/.profile`, `~/.zshrc`) "
        "after a manual elan install.",
    ),
    # ── Typeclass inference loops / depth ────────────────────────────────
    (
        r"maximum class-instance resolution depth has been reached",
        "Typeclass search hit its depth limit — frequently a Unicode/ASCII "
        "name collision or a missing instance. Run `set_option "
        "synthInstance.maxHeartbeats 40000` or trace to find the culprit class.",
    ),
    (
        r"maximum recursion depth has been reached",
        "Lean's elaborator exceeded its own recursion limit. Almost always a "
        "looping macro or `simp` lemma — bisect your recent `@[simp]` additions "
        "or disable notation extensions to isolate the cycle.",
    ),
    # ── Goal state / tactic failure ──────────────────────────────────────
    (
        r"unsolved goals",
        "You closed the tactic block but Lean still has goals left. Check the "
        "remaining goals in the error and add tactics to discharge each; a "
        "stray `done` after `sorry` is not equivalent to a proof.",
    ),
    (
        r"tactic '.*?' failed.*?did not make progress",
        "This tactic fired but nothing changed — usually a lemma that doesn't "
        "apply or a `simp` set that's already normal. Inspect the goal state "
        "(`--show-goal` in `grd lean prove`) and pick a tactic that matches.",
    ),
    (
        r"tactic 'rfl' failed",
        "`rfl` only closes definitionally-equal goals. Use `decide` for "
        "decidable props, `norm_num` for arithmetic, or rewrite with the "
        "relevant lemmas before attempting `rfl`.",
    ),
    (
        r"tactic 'apply' failed.*?unification",
        "`apply` couldn't unify the lemma's conclusion with your goal. Check "
        "argument order and implicit args; try `refine <lemma> ?_ ?_` to see "
        "which subgoals remain, or `exact?` for a search.",
    ),
    (
        r"linarith failed to find a contradiction|linarith\s+failed",
        "`linarith` proves linear arithmetic only. For nonlinear goals try "
        "`nlinarith` or `polyrith`; for equalities use `ring` / `field_simp`; "
        "for goals involving casts, `push_cast` first.",
    ),
    (
        r"ring\s+(?:tactic\s+)?failed",
        "`ring` only closes commutative-(semi)ring equalities. If your goal "
        "has casts (`Nat → Int`), run `push_cast` first; if it has divisions, "
        "use `field_simp` then `ring`.",
    ),
    (
        r"simp made no progress",
        "`simp` found nothing to rewrite. The goal may already be normal, or "
        "your lemma set doesn't apply — try `simp?` to see the used lemmas, "
        "or `simp only [...]` with explicit rewrites.",
    ),
    (
        r"decide tactic failed|failed to reduce to 'true'",
        "`decide` only closes propositions Lean can compute to a literal "
        "`true`. Ensure every component has a `Decidable` instance; for large "
        "domains use `native_decide` (untrusted) or prove manually.",
    ),
    (
        r"expected token|unexpected token",
        "Syntax error — often a stray `|`, `⟨⟩` mismatch, or Lean 3 leftover "
        "(e.g. `begin ... end`). Lean 4 uses `by ... ` for tactic blocks "
        "and `⟨..., ...⟩` for anonymous constructors.",
    ),
    (
        r"missing exponent digits in scientific literal",
        "Despite the message, this usually means a *theorem name* starts with "
        "a digit (lean4#9450). Rename the declaration to start with a letter.",
    ),
    (
        r"function expected at",
        "Lean thinks you applied a non-function to an argument — often a "
        "missing space between identifier and `(`, or a coercion that never "
        "fires. Check parentheses and try an explicit `(x : Type)` ascription.",
    ),
    (
        r"(?:invalid|ill-formed) field notation",
        "Dot notation (`x.foo`) needs the type to define `foo`. Use the full "
        "namespace path (`Namespace.foo x`) or check the type has the field.",
    ),
    # ── Lean 3 leftovers / syntax drift ──────────────────────────────────
    (
        r"\b(?:begin|end)\b.*?tactic|invalid 'begin' block",
        "Lean 4 dropped `begin ... end`. Replace with `by` for tactic mode: `theorem t : P := by tac1; tac2`.",
    ),
    # ── Warnings worth hinting ───────────────────────────────────────────
    (
        r"declaration uses 'sorry'",
        "This declaration is not actually proved — it has a `sorry`. Replace "
        "each `sorry` with a real proof before treating the theorem as true.",
    ),
    (
        r"unused variable",
        "Lean warns when a binder is unused; prefix the name with `_` (`_h : P`) to silence or remove the binder.",
    ),
]


_RULES_COMPILED: Final[tuple[tuple[re.Pattern[str], str], ...]] = tuple(
    (re.compile(pat, re.IGNORECASE | re.DOTALL), hint) for pat, hint in _HINT_RULES_RAW
)


HINT_RULES: Final[tuple[tuple[str, str], ...]] = tuple(_HINT_RULES_RAW)
"""Public view of the (pattern, hint) table for docs/tests/audits."""


def hint_for_message(message: str) -> str | None:
    """Return a one-line explanation + action hint, or ``None`` if unknown.

    Matches the first rule in ``HINT_RULES`` whose pattern is found anywhere
    in ``message`` (case-insensitive, ``.`` matches newline so multi-line Lean
    diagnostics work). Returning ``None`` for unrecognized messages is the
    intentional contract — callers treat that as "show the raw diagnostic,
    don't invent guidance."
    """
    if not message:
        return None
    for pattern, hint in _RULES_COMPILED:
        if pattern.search(message):
            return hint
    return None
