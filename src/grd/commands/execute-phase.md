---
name: grd:execute-phase
description: Execute all plans in a phase with wave-based parallelization
argument-hint: "<phase-number> [--gaps-only]"
context_mode: project-required
requires:
  files: [".grd/ROADMAP.md"]
  state: "phase_planned"
allowed-tools:
  - file_read
  - file_write
  - file_edit
  - find_files
  - search_files
  - shell
  - task
  - ask_user
---

<!-- Tool names and @ includes are runtime-specific; the installer rewrites paths for your runtime. -->

<objective>
Execute all phase plans with wave-based parallelization.

The orchestrator discovers plans, groups them into waves, spawns subagents, and collects results while each subagent owns its own plan.

Plans may cover derivations, calculations, numerical implementations, data analysis, figure generation, or LaTeX writing.

Context budget: ~15% orchestrator, fresh context per subagent.
</objective>

<execution_context>
@{GRD_INSTALL_DIR}/workflows/execute-phase.md
@{GRD_INSTALL_DIR}/references/ui/ui-brand.md
</execution_context>

<context>
Phase: $ARGUMENTS

**Flags:**

- `--gaps-only` -- Execute only gap-closure plans (`gap_closure: true`). Use after `verify-work` creates fix plans.

@.grd/ROADMAP.md
@.grd/STATE.md
</context>

<inline_guidance>

## Error Recovery

- **Subagent failure:** Re-read the `PLAN.md` task, clarify it, and retry; if it still fails, mark the task blocked and continue.
- **Derivation dead end:** Stop, record what failed, and try a different representation, regularization, or cross-check.
- **Numerics don't converge:** Check units, boundary conditions, resolution, and algorithm fit before changing approach.
- **Sign or factor errors:** Trace backward through each step rather than adjusting by hand.

## Physics-Specific Execution Tips

- **Dimensional consistency:** Verify dimensions before moving to the next task.
- **Approximation validity:** Check that the parameter regime still matches the plan.
- **Convention mismatches:** Verify sign conventions, unit systems, and index placement when combining results.
- **Intermediate results:** Write key expressions to `SUMMARY.md` as they are obtained.

## Inter-wave Verification Gates

Between waves, the orchestrator can run lightweight verification on the completed wave's `SUMMARY.md` outputs. This is controlled by `execution.review_cadence` and the phase classification rules in the full workflow:

- `"dense"` — always run the gates
- `"adaptive"` (default) — run the gates when the wave created or challenged decisive downstream evidence
- `"sparse"` — skip routine gates unless the wave raised a failed sanity check, anchor gap, or dependency warning

Cost: ~2-5k tokens per gate. Catches sign errors and convention drift before they propagate.

## Partial Completion and Resumption

- If execution is interrupted (context limit, user stop, crash), the completed task SUMMARY.md files are already written.
- On resumption, the orchestrator detects which plans already have SUMMARY.md files and skips them.
- To force re-execution of a completed plan, delete or rename its SUMMARY.md before re-running `/grd:execute-phase`.
- The orchestrator applies returned shared-state updates after each successfully completed plan, so by the time a wave completes `STATE.md` already reflects that plan-level progress.

</inline_guidance>

<process>
**CRITICAL: First, read the full workflow file using the file_read tool:**
Read the file at {GRD_INSTALL_DIR}/workflows/execute-phase.md — this contains the complete step-by-step instructions. Do NOT improvise. Follow the workflow file exactly.

Execute the workflow end-to-end and preserve all gates (wave execution, checkpoint handling, verification, state updates, routing).
</process>
