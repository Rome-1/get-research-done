---
name: grd:lean-demo
description: "Rome-persona single-entry physicist demo — runs the MATHEMATICIAN-WORKFLOWS §7 transcript end-to-end against the simple-mechanics template."
argument-hint: "[--dry-run] [--template simple-mechanics]"
context_mode: project-aware
allowed-tools:
  - shell
---

<objective>
Cold re-onboarding entry point. After three weeks away, run exactly one
command and watch a screen-shareable transcript of the full §7 "physics
phase → Lean-checked lemma" demo in under 5 minutes.

This skill wraps `grd lean demo`. It is the single entry point promised in
MATHEMATICIAN-WORKFLOWS §7 for the Rome persona — no flags to remember
beyond `--dry-run` and `--template`, no subcommands to sequence manually.
</objective>

<context>
The demo walks the §7 transcript stage-by-stage:

1. `grd init new-project --template simple-mechanics` — **REAL** (ge-bqdt)
2. `/grd:lean-bootstrap --for physicist` — **SKIPPED** (installer; ge-5o8)
3. `/grd:progress` (pre-verify) — **MOCK** fixture
4. `/grd:verify-claim --phase 1 --claim derived-energy-conservation` — **SKIPPED** (live LLM; ge-ln7 + ge-cla + ge-j8k)
5. `/grd:progress` (post-verify) — **MOCK** fixture (ge-8g5)

Every stage carries an honest status label:

  - `REAL`    — ran live; narration reflects real output
  - `MOCK`    — dependency shipped, output is the §7 expected-state fixture
  - `SKIPPED` — long-running / LLM-backed; command printed, not executed

This is by design (ge-e2c1 contract (c)): "--dry-run that clearly labels
which stages are still mocked when dependencies haven't shipped (don't
lie)". The demo is honest about what it ran vs narrated.
</context>

<process>

## Step 1: Run the demo

```bash
grd lean demo
```

The default template is `simple-mechanics` (1D harmonic oscillator, energy
conservation). The only live side effect is stamping the template into
`.grd/demo/simple-mechanics/` under the current working directory. The
bootstrap installer and live verify-claim are always SKIPPED so the
transcript stays under the 5-minute budget.

Pass `--dry-run` to skip the template stamp as well — useful for
screen-shares where you don't want to leave any filesystem state behind:

```bash
grd lean demo --dry-run
```

## Step 2: Read the stage labels

Scan each stage for its label:

- `[REAL]`    — you just watched real output
- `[MOCK]`    — fixture from §7; expected-state, not live-state
- `[YELLOW-dim]SKIPPED[/]` — command printed under `→`; run it to see live output

The `→` line on every SKIPPED stage shows the exact command to run
manually. For the full live experience:

```bash
# The long-running installer (run once; subsequent demos re-use the toolchain):
grd lean bootstrap --for physicist --yes

# The live LLM + Lean verify-claim (takes minutes, costs API tokens):
grd lean verify-claim --phase 1 --claim derived-energy-conservation
```

## Step 3: Inspect the stamped project

When run without `--dry-run`, the demo leaves a real `simple-mechanics`
project at `.grd/demo/simple-mechanics/`. Open `PROJECT.md`,
`CONVENTIONS.md`, `ROADMAP.md`, and `state.json` to see the canonical
physicist project shape. This is the same template `grd init new-project
--template simple-mechanics` stamps in a fresh project directory.

</process>

<success_criteria>
- [ ] Demo transcript is printed end-to-end in under 5 minutes wall-clock.
- [ ] Every stage carries a visible `[REAL]`, `[MOCK]`, or `[SKIPPED]` label.
- [ ] Under `--dry-run`, nothing is written to disk.
- [ ] Without `--dry-run`, exactly one real side effect: the stamped template.
- [ ] Each `SKIPPED` stage shows the exact command to run live.
</success_criteria>
