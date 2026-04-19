---
name: grd:lean-bootstrap-physicist
description: "Guided Lean 4 on-ramp for physicists: express a paper claim in Lean, explore PhysLean examples."
argument-hint: ""
context_mode: project-aware
allowed-tools:
  - file_read
  - shell
  - ask_user
---

<objective>
Walk a physicist through their first 10-20 minutes with Lean 4 + PhysLean inside GRD.

This is greenfield territory -- as of 2025 there are zero independent public PhysLean
users (nitro research). The canonical on-ramp is a LinkedIn DM to the library author.
GRD provides the first structured physicist entry point.

Assumes the toolchain is already installed (``grd lean bootstrap --for physicist``
ran first, which auto-enables the Mathlib cache).
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

If `blocked on:` appears, run ``/grd:lean-bootstrap --for physicist`` first and
come back.

## Step 2: Physics meets proof -- why formalize?

Briefly explain *why* a physicist would use Lean:

- **Catch sign errors and factor-of-two mistakes** before they propagate through
  a 40-page calculation.
- **Machine-check dimensional analysis** -- the type system prevents adding meters
  to seconds.
- **Reproducible derivations** -- a Lean proof is a permanent record that the
  derivation is correct, not just peer-reviewed.

The goal is not to formalize all of physics -- it's to formalize the *claims that
matter most* in a paper or thesis.

## Step 3: Your first physics type-check

Start with a simple claim that doesn't need PhysLean:

```bash
grd lean check 'theorem energy_nonneg (m v : Float) (hm : m >= 0) (hv : v >= 0) : m * v * v / 2 >= 0 := by sorry'
```

This will *fail* (``sorry`` is a placeholder). Explain:
- The statement expresses "kinetic energy is non-negative".
- ``sorry`` is a hole -- Lean accepts the structure but flags it as unproved.
- We'll fill it in properly below.

Now try with a real proof:

```bash
grd lean check 'theorem pos_mul_nonneg (a b : Nat) : 0 <= a * b := Nat.zero_le _'
```

## Step 4: PhysLean -- what's available

PhysLean (formerly SciLean / PhysLib) provides:
- **Units and dimensional analysis** as Lean types
- **Tensor calculus** and index notation
- **Standard Model** particle physics definitions
- **Lie algebra** representations

The library is at ``https://github.com/PhysLean/PhysLean`` (~540 GitHub stars).

To use PhysLean in a GRD project, add it to ``lakefile.lean``:

```lean
require physlean from git
  "https://github.com/PhysLean/PhysLean" @ "main"
```

Then: ``lake update && lake exe cache get`` (the Mathlib cache speeds this up).

## Step 5: Example traces from PhysLean

Walk through 3-5 real examples from the PhysLean repository:

### Example 1: Basic type structure

```lean
-- PhysLean uses type-safe units. A mass has type `Mass`, not just `Float`.
-- This prevents adding incompatible quantities at compile time.
-- The key insight: Lean's type system IS your dimensional analysis.
```

### Example 2: A simple Lorentz invariant

```bash
grd lean check --import Mathlib.Tactic '
  -- A Minkowski inner product is invariant under Lorentz boosts.
  -- In PhysLean this would use `LorentzGroup` and `minkowskiMetric`.
  -- Without PhysLean, we can still express the algebraic structure:
  theorem lorentz_invariance_sketch : True := trivial
'
```

### Example 3: Conservation law pattern

```bash
grd lean check '
  -- Pattern: express a conservation law as an equation between before/after states.
  theorem momentum_conservation (p1_before p2_before p1_after p2_after : Float)
    (h : p1_before + p2_before = p1_after + p2_after)
    : p1_after + p2_after = p1_before + p2_before := h.symm
'
```

### Example 4: Expressing a paper claim

Show the autoformalization pipeline:

```bash
grd lean verify-claim --no-llm 'The total energy of an isolated system is conserved'
```

Explain: ``--no-llm`` does a dry run without an API key. In production, this
pipeline extracts the claim, retrieves relevant Mathlib/PhysLean names, generates
candidate Lean statements, and compile-tests them.

### Example 5: Dimensional analysis as types

```bash
grd lean check '
  -- Lean can enforce dimensional consistency through its type system.
  -- Define units as distinct types; conversions require explicit functions.
  structure Meters where val : Float
  structure Seconds where val : Float
  structure MetersPerSecond where val : Float

  def velocity (d : Meters) (t : Seconds) : MetersPerSecond :=
    { val := d.val / t.val }

  -- This prevents: velocity + distance (type error!)
'
```

## Step 6: The physicist's workflow in GRD

1. **Express a claim** from your paper or derivation.
2. **Run ``grd lean verify-claim``** to auto-formalize it.
3. If the pipeline succeeds, the Lean statement is added to the Blueprint.
4. If it escalates, you get a bead with the specific ambiguity to resolve.
5. **Build up a Blueprint** (``grd lean init-blueprint``) for the full proof
   structure of a paper section.

## Step 7: Next steps

Ask what the user wants to formalize:

1. **A specific equation or theorem** from their current work.
2. **A derivation chain** (e.g., starting from Maxwell's equations).
3. **A dimensional analysis check** on existing calculations.

Offer to run ``grd lean verify-claim`` on their first candidate.

</process>

<success_criteria>
- [ ] User's environment is verified.
- [ ] User understands why formalization helps physicists (error-catching, not purity).
- [ ] User has type-checked at least one physics-flavored theorem.
- [ ] User has seen the PhysLean example traces.
- [ ] User has run a dry-run verify-claim.
- [ ] User knows the end-to-end physicist workflow in GRD.
</success_criteria>
