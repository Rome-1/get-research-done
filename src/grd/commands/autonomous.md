---
name: grd:autonomous
description: Run all remaining phases autonomously — discuss→plan→execute→verify per phase
argument-hint: "[--from N]"
context_mode: project-required
requires:
  files: ["GRD/ROADMAP.md", "GRD/STATE.md"]
allowed-tools:
  - file_read
  - file_write
  - file_edit
  - shell
  - find_files
  - search_files
  - ask_user
  - task
---

<objective>
Execute all remaining milestone phases autonomously. For each phase: discuss → plan → execute → verify. Pauses only for user decisions (gray area acceptance, blockers, verification routing).

Uses ROADMAP.md phase discovery and Skill() flat invocations for each phase command. After all phases complete: milestone audit → complete.

**Creates/Updates:**
- `GRD/STATE.md` — updated after each phase
- `GRD/ROADMAP.md` — progress updated after each phase
- Phase artifacts — CONTEXT.md, PLANs, SUMMARYs, VERIFICATION.md per phase

**After:** Milestone is complete and archived.
</objective>

<execution_context>
@{GRD_INSTALL_DIR}/workflows/autonomous.md
</execution_context>

<context>
Optional flag: `--from N` — start from phase N instead of the first incomplete phase.

Project context, phase list, and state are resolved inside the workflow using init commands (`grd --raw init milestone-op`, `grd --raw roadmap analyze`). No upfront context loading needed.
</context>

<process>
**CRITICAL: First, read the full workflow file using the file_read tool:**
Read {GRD_INSTALL_DIR}/workflows/autonomous.md first and follow it exactly.

Execute the autonomous workflow end-to-end.
Preserve all workflow gates (phase discovery, per-phase execution, convention checks, blocker handling, progress display, verification routing).
</process>
