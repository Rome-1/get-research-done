---
name: grd:debug
description: Systematic debugging of physics calculations with persistent state across context resets
argument-hint: "[issue description]"
context_mode: project-required
allowed-tools:
  - file_read
  - shell
  - task
  - ask_user
---
<objective>
Debug physics calculations using systematic isolation with subagent investigation.

**Orchestrator role:** Gather symptoms, spawn grd-debugger agent, handle checkpoints, spawn continuations.

**Why subagent:** Investigation burns context fast. Fresh context keeps the orchestrator lean.

Physics debugging differs fundamentally from software debugging. In software, a bug is deterministic: same input gives same wrong output. In physics calculations, errors can be subtle — a sign error that only matters in one regime, a factor of 2 from a symmetry argument, a gauge artifact that looks like a physical effect, a numerical instability that masquerades as a phase transition. The debugger must think like a physicist, not a programmer.
</objective>

<execution_context>
@{GRD_INSTALL_DIR}/workflows/debug.md
</execution_context>

<context>
User's issue: $ARGUMENTS

Check for active sessions:

```bash
ls .grd/debug/*.md 2>/dev/null | grep -v resolved | head -5
```

</context>

<process>

## 0. Initialize Context

```bash
INIT=$(grd init progress --include state,roadmap,config)
```

Extract `commit_docs` from init JSON. Resolve debugger model:

```bash
DEBUGGER_MODEL=$(grd resolve-model grd-debugger)
```

## 1. Check Active Sessions

If active sessions exist AND no $ARGUMENTS:

- List sessions with status, current hypothesis, next action
- User picks number to resume OR describes new issue

If $ARGUMENTS provided OR user describes new issue:

- Continue to symptom gathering

## 2. Gather Symptoms (if new issue)

Use ask_user for each. Physics-specific symptom gathering:

1. **Expected result** — What should the calculation give? (analytical prediction, known limit, published value, physical intuition)
2. **Actual result** — What do you get instead? (wrong magnitude, wrong sign, wrong functional form, divergence, nonsensical value)
3. **Discrepancy character** — How does the error behave?
   - Constant factor off (suggests combinatorial or normalization error)
   - Wrong sign (suggests convention mismatch or parity error)
   - Wrong power law (suggests missed contribution or wrong scaling argument)
   - Divergence where finite result expected (suggests regularization issue or missed cancellation)
   - Numerical instability (suggests ill-conditioned formulation or inadequate precision)
   - Gauge-dependent result for gauge-invariant observable (suggests gauge artifact)
4. **Where it breaks** — In what regime or parameter range does the problem appear?
   - Always wrong, or only for certain parameter values?
   - Does it get worse as some parameter increases?
   - Does the problem appear at a specific step in the derivation?
5. **What you have tried** — Any checks already performed?
   - Dimensional analysis?
   - Limiting cases?
   - Comparison with alternative derivation?
   - Numerical spot-checks?

After all gathered, confirm ready to investigate.

## 3. Spawn grd-debugger Agent

Fill prompt and spawn:

```markdown
<objective>
Investigate physics issue: {slug}

**Summary:** {trigger}
</objective>

<symptoms>
expected: {expected}
actual: {actual}
discrepancy_character: {discrepancy_character}
where_it_breaks: {where_it_breaks}
already_tried: {already_tried}
</symptoms>

<mode>
symptoms_prefilled: true
goal: find_root_cause_only
</mode>

<debug_file>
Create: .grd/debug/{slug}.md
</debug_file>
```

```
task(
  prompt="First, read {GRD_AGENTS_DIR}/grd-debugger.md for your role and instructions.\n\n" + filled_prompt,
  subagent_type="grd-debugger",
  model="{debugger_model}",
  readonly=false,
  description="Debug {slug}"
)
```

## 4. Handle Agent Return

Handle the debugger return once through the workflow-owned typed child-return contract. Do not branch on heading text here.

- Display root cause and evidence summary
- Classify the error type (sign error, missing factor, wrong convention, numerical issue, conceptual error)
- Offer options:
  - "Fix now" — spawn fix subagent
  - "Plan fix" — suggest /grd:plan-phase --gaps
  - "Manual fix" — done (provide the identified error location and correction)

## 5. Spawn Fresh Continuation agent (After Checkpoint)

When user responds to checkpoint, spawn fresh agent:

```markdown
<objective>
Continue debugging {slug}. Evidence is in the debug file.
</objective>

<prior_state>
Debug file path: .grd/debug/{slug}.md
Read that file before continuing so you inherit the prior investigation state instead of relying on an inline `@...` attachment.
</prior_state>

<checkpoint_response>
**Type:** {checkpoint_type}
**Response:** {user_response}
</checkpoint_response>

<mode>
goal: find_root_cause_only
</mode>
```

```
task(
  prompt="First, read {GRD_AGENTS_DIR}/grd-debugger.md for your role and instructions.\n\n" + continuation_prompt,
  subagent_type="grd-debugger",
  model="{debugger_model}",
  readonly=false,
  description="Continue debug {slug}"
)
```

</process>

<success_criteria>

- [ ] Active sessions checked
- [ ] Symptoms gathered with physics-specific characterization (if new)
- [ ] grd-debugger spawned with context and investigation strategy
- [ ] Checkpoints handled correctly
- [ ] Root cause confirmed and classified before fixing
- [ ] Error type identified (algebraic, numerical, conceptual, conventional)
      </success_criteria>
