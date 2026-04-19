---
name: grd:lean-bootstrap-ml-researcher
description: "Guided Lean 4 on-ramp for ML researchers: LeanDojo setup, miniF2F eval, LLM-driven proving."
argument-hint: ""
context_mode: project-aware
allowed-tools:
  - file_read
  - shell
  - ask_user
---

<objective>
Walk an ML researcher through their first 10-20 minutes with Lean 4 + LeanDojo inside GRD.

The ML-researcher persona cares about Lean as a *verification backend* for
LLM-generated proofs, not as a daily proving tool. Their workflow is:
benchmark on miniF2F, evaluate proof-generation models, and integrate formal
verification into ML pipelines.

Assumes the toolchain is already installed (``grd lean bootstrap --for ml-researcher``
ran first, which auto-enables the LeanDojo premise index).
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

If `blocked on:` appears, run ``/grd:lean-bootstrap --for ml-researcher`` first.

Confirm that Lean, Pantograph, and (ideally) LeanDojo are available.

## Step 2: The ML researcher's Lean stack

Explain the ecosystem:

| Tool | Role | Status |
|------|------|--------|
| **Lean 4** | Kernel -- verifies proofs are correct | Installed via elan |
| **Pantograph** | REPL -- lets programs interact with Lean programmatically | Installed via pip |
| **LeanDojo** | Premise retrieval + extraction -- feeds ML models | Opt-in (``--with-leandojo``) |
| **Kimina / BFS-Prover** | Proof-generation models -- generate tactic sequences | External; GRD integrates as a backend |
| **LLMLean** | VS Code extension for LLM-assisted proving | Optional IDE integration |
| **miniF2F** | Benchmark -- 488 competition math problems | Standard eval target |

GRD's role: orchestrate verification so ML researchers don't have to manage
Lean infrastructure manually.

## Step 3: Your first proof verification

Show that GRD can verify a proof:

```bash
grd lean check 'theorem two_plus_two : 2 + 2 = 4 := by decide'
```

Now show the tactic ladder -- GRD's built-in proof search:

```bash
grd lean prove '2 + 2 = 4'
```

Explain: this is a simple enumeration over 8 tactics. The interesting
ML problem is generating *arbitrary* tactic sequences, not just trying
a fixed list.

## Step 4: How LLM-driven proving works

Explain the pipeline:

```
Informal claim
    |
    v
[LLM: generate N candidate Lean statements]
    |
    v
[Lean: type-check each candidate]  <-- grd lean check
    |
    v
[Repair loop: fix compile errors]  <-- APOLLO-style
    |
    v
[Back-translate + faithfulness check]
    |
    v
Accept or escalate
```

GRD implements this as ``grd lean verify-claim``:

```bash
grd lean verify-claim --no-llm 'for every prime p, p > 1'
```

(``--no-llm`` runs the full pipeline with stub responses -- useful for testing
plumbing without an API key.)

With an API key:

```bash
ANTHROPIC_API_KEY=sk-... grd lean verify-claim 'for every prime p, p > 1'
```

## Step 5: Pantograph -- programmatic Lean interaction

Pantograph exposes Lean's proof state as a JSON API. GRD manages the
Pantograph daemon automatically:

```bash
# Start the REPL daemon (auto-starts on first use)
grd lean serve-repl

# Ping it
grd lean ping
```

The daemon holds Lean's environment in memory, so repeated checks are fast
(~100ms vs ~5s cold start). This matters for ML training loops where you're
running thousands of proof attempts.

## Step 6: Evaluating on miniF2F

miniF2F is the standard benchmark for neural theorem proving:
- 488 problems from math competitions (AMC, AIME, IMO)
- Split into validation (244) and test (244) sets
- State of the art: BFS-Prover-V2 hits ~95% on test (2025)

To evaluate a proof-generation model against miniF2F:

1. Clone miniF2F and build it:
   ```bash
   git clone https://github.com/openai/miniF2F lean4
   cd lean4 && lake build
   ```

2. For each problem, extract the goal and feed it to your model.

3. Verify the model's output:
   ```bash
   grd lean check --file path/to/generated_proof.lean
   ```

4. Or use ``grd lean prove`` for the baseline tactic search:
   ```bash
   grd lean prove 'theorem imo_2019_p1 ...'
   ```

GRD's ``verify-claim`` pipeline is designed for *informal* claims. For
miniF2F, where you already have formal statements, use ``grd lean check``
directly.

## Step 7: LeanDojo premise retrieval

When LeanDojo is installed (``grd lean bootstrap --with-leandojo --yes``),
GRD can retrieve relevant premises from Mathlib:

- **Premise retrieval**: given a goal state, find lemmas likely to be useful.
- **Extraction**: parse Lean source into a graph of definitions and theorems.
- **ReProver**: LeanDojo's built-in retrieval-augmented prover (50%+ on miniF2F).

The premise index is used by ``grd lean verify-claim`` to ground LLM-generated
statements against real Mathlib identifiers, catching hallucinated names.

## Step 8: Integrating with your ML pipeline

Three integration patterns:

### Pattern A: Batch verification
```bash
# Verify a batch of claims from a JSONL file
cat claims.jsonl | while read -r line; do
  claim=$(echo "$line" | jq -r '.claim')
  grd --json lean verify-claim "$claim" >> results.jsonl 2>/dev/null
done
```

### Pattern B: Daemon-backed fast checking
```bash
# Start daemon once, run many checks
grd lean serve-repl
for proof in proofs/*.lean; do
  grd --json lean check --file "$proof"
done
```

### Pattern C: Event-streamed progress
```bash
# Stream progress events for monitoring
grd lean verify-claim --events jsonl 'claim here' > events.jsonl
```

## Step 9: Next steps

1. **Set up an API key** and run a real ``verify-claim`` on a claim from
   your research.
2. **Benchmark** your proof-generation model using ``grd lean check`` in
   a loop.
3. **Explore LeanDojo** for premise retrieval if installed.
4. **Check Kimina** (``https://github.com/MoonshotAI/Kimina``) for
   state-of-the-art batch proving -- GRD will integrate it as a backend
   in Phase 4.

Ask the user what they'd like to try first.

</process>

<success_criteria>
- [ ] User's environment is verified (Lean + Pantograph ready).
- [ ] User understands the LLM-driven proving pipeline.
- [ ] User has run ``grd lean check`` and ``grd lean prove``.
- [ ] User has seen the verify-claim pipeline (at least ``--no-llm`` dry run).
- [ ] ML ecosystem (LeanDojo, Kimina, miniF2F) is explained with concrete next steps.
- [ ] Integration patterns (batch, daemon, event-stream) are demonstrated.
</success_criteria>
