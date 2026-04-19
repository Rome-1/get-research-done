---
name: grd:lean-bootstrap-mathematician
description: "Guided Lean 4 on-ramp for mathematicians: state a lemma, prove it with Mathlib tactics, explore the tactic zoo."
argument-hint: ""
context_mode: project-aware
allowed-tools:
  - file_read
  - shell
  - ask_user
---

<objective>
Walk a mathematician through their first 10-20 minutes with Lean 4 + Mathlib inside GRD.

Assumes the toolchain is already installed (``grd lean bootstrap --for mathematician``
ran first). This walkthrough follows the *Mathematics in Lean* progression:
state a simple lemma, close it with a tactic, then build up to real Mathlib usage.
</objective>

<context>
Lean environment:

```bash
grd --json lean env
```
</context>

<process>

## Step 1: Verify the environment

```bash
grd lean env
```

If `blocked on:` appears, run ``/grd:lean-bootstrap --for mathematician`` first and
come back. Otherwise, confirm elan, toolchain, and pantograph are ready.

## Step 2: Hello, Lean -- your first type-check

Create a file and check it:

```bash
grd lean check 'theorem hello : 1 + 1 = 2 := by norm_num'
```

Explain what happened:
- ``theorem hello`` declares a named theorem.
- ``: 1 + 1 = 2`` is the *statement* (a proposition / type).
- ``:= by norm_num`` is the *proof term* — ``by`` enters tactic mode, ``norm_num``
  closes arithmetic goals.
- Exit code 0 means Lean accepted the proof.

## Step 3: Try the tactic ladder

Show the built-in tactic search:

```bash
grd lean prove '1 + 1 = 2'
```

Explain the output — GRD tried ``rfl``, ``decide``, ``norm_num`` etc. in order and
returned the first one that worked. This is useful for quick exploration; real proofs
use more targeted tactics.

## Step 4: State a real lemma

Guide the user to state something slightly harder:

```lean
theorem add_comm_example (m n : Nat) : m + n = n + m := by omega
```

Type-check it:

```bash
grd lean check 'theorem add_comm_example (m n : Nat) : m + n = n + m := by omega'
```

Explain:
- ``(m n : Nat)`` introduces universally quantified variables.
- ``omega`` is a decision procedure for linear arithmetic over ``Nat`` / ``Int``.
- If the user wants the Mathlib proof: ``exact Nat.add_comm m n``.

## Step 5: Use a Mathlib import

Now try something that requires Mathlib. This shows the power of the cache:

```bash
grd lean check --import Mathlib.Tactic 'example (p q : Prop) (hp : p) (hq : q) : p /\ q := by exact And.intro hp hq'
```

Or with ``aesop``:

```bash
grd lean check --import Mathlib.Tactic 'example (p q : Prop) (hp : p) (hq : q) : p /\ q := by aesop'
```

Explain:
- ``--import Mathlib.Tactic`` loads the standard Mathlib tactic library.
- ``aesop`` is a general-purpose automation tactic that chains multiple strategies.
- With the Mathlib cache (``lake exe cache get``), first imports are fast.

## Step 6: The tactic zoo -- quick reference

Present the most useful tactics for daily mathematics:

| Tactic | Closes goals like... | Example |
|--------|---------------------|---------|
| ``rfl`` | ``a = a`` (definitional equality) | ``example : 0 + n = n := by rfl`` |
| ``norm_num`` | Numeric equalities/inequalities | ``example : 2 + 3 = 5 := by norm_num`` |
| ``omega`` | Linear arithmetic (Nat/Int) | ``example (n : Nat) : n < n + 1 := by omega`` |
| ``ring`` | Ring identities | ``example (x : Int) : (x+1)^2 = x^2 + 2*x + 1 := by ring`` |
| ``simp`` | Simplification with lemma database | ``example (l : List Nat) : l ++ [] = l := by simp`` |
| ``exact`` | Supply a term directly | ``exact Nat.add_comm m n`` |
| ``apply`` | Reduce goal using a lemma | ``apply Nat.succ_lt_succ`` |
| ``aesop`` | General-purpose automation | Works on many goals, sometimes slow |
| ``linarith`` | Linear arithmetic with hypotheses | Uses hypotheses in context |
| ``decide`` | Decidable propositions | ``example : 7 < 10 := by decide`` |

## Step 7: Next steps

Suggest the user's next moves:

1. **State a lemma from their research** — use ``grd lean check`` to iterate.
2. **Search Mathlib** — ``exact?``, ``apply?``, ``rw?`` in VS Code or via
   ``grd lean check --import Mathlib.Tactic 'example ...'``.
3. **Formalize a claim** — ``grd lean verify-claim 'for every prime p, p > 1'``
   runs the autoformalization pipeline.
4. **Set up a Blueprint** — ``grd lean init-blueprint <phase>`` creates a
   dependency graph for a phase's proof obligations.

Ask the user what they'd like to try first.

</process>

<success_criteria>
- [ ] User's environment is verified (elan + toolchain + pantograph ready).
- [ ] User has type-checked at least one theorem (``grd lean check``).
- [ ] User has seen the tactic ladder (``grd lean prove``).
- [ ] User has used at least one Mathlib import.
- [ ] Tactic reference table is presented.
- [ ] User knows their next steps (verify-claim, init-blueprint, or freeform proving).
</success_criteria>
