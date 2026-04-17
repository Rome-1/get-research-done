---
name: grd:new-milestone
description: Start a new research milestone cycle — update PROJECT.md and route to requirements
argument-hint: "[milestone name, e.g., 'v1.1 Finite-Temperature Extension']"
context_mode: project-required
allowed-tools:
  - file_read
  - file_write
  - shell
  - task
  - ask_user
---


<objective>
Start a new research milestone: questioning -> literature research (optional) -> requirements -> staged roadmap handoff.

Continuation equivalent of new-project. Research project exists, PROJECT.md has history. Gathers "what's next", updates PROJECT.md, then runs requirements → roadmap cycle while honoring `planning.commit_docs` for milestone artifact commits.

**Creates/Updates:**

- `.grd/PROJECT.md` — updated with new milestone goals
- `.grd/research/` — domain and literature research (optional, NEW research objectives only)
- `.grd/REQUIREMENTS.md` — scoped requirements for this milestone
- `.grd/ROADMAP.md` — phase structure (continues numbering)
- `.grd/STATE.md` — reset for new milestone

**After:** `/grd:plan-phase [N]` to start execution.
</objective>

<execution_context>
@{GRD_INSTALL_DIR}/workflows/new-milestone.md
@{GRD_INSTALL_DIR}/references/research/questioning.md
@{GRD_INSTALL_DIR}/references/ui/ui-brand.md
@{GRD_INSTALL_DIR}/templates/project.md
@{GRD_INSTALL_DIR}/templates/requirements.md
</execution_context>

<context>
Milestone name: $ARGUMENTS (optional - will prompt if not provided)

**Load project context:**
@.grd/PROJECT.md
@.grd/STATE.md
@.grd/MILESTONES.md
@.grd/config.json

**Load milestone context (if exists, from /grd:discuss-phase):**
@.grd/MILESTONE-CONTEXT.md
</context>

<process>
**Follow the new-milestone workflow** from `@{GRD_INSTALL_DIR}/workflows/new-milestone.md`.

**Argument parsing:**

- `$ARGUMENTS` → milestone name (optional, will prompt if not provided)
- Parse milestone name from arguments if present

**Flags:** None currently defined.

The workflow handles the full milestone initialization flow:

1. Load existing project context (PROJECT.md, MILESTONES.md, STATE.md)
2. Gather milestone goals (from MILESTONE-CONTEXT.md or user questioning)
3. Determine milestone version (auto-increment from MILESTONES.md)
4. Update PROJECT.md and STATE.md
5. Optional literature survey (4 parallel researcher agents)
6. Define research requirements (category scoping, REQ-IDs)
7. Create research roadmap (grd-roadmapper agent)
8. Commit all artifacts
9. Present next steps (`/grd:discuss-phase [N]` or `/grd:plan-phase [N]`)

All gates (validation, questioning, research, requirements, roadmap approval, commits) are preserved in the workflow.
</process>

<success_criteria>

- [ ] PROJECT.md updated with Current Milestone section
- [ ] STATE.md reset for new milestone
- [ ] MILESTONE-CONTEXT.md consumed and deleted (if existed)
- [ ] Literature survey completed (if selected) — 4 parallel agents, milestone-aware
- [ ] Research requirements gathered and scoped per category
- [ ] REQUIREMENTS.md created with REQ-IDs
- [ ] grd-roadmapper spawned with phase numbering context
- [ ] Roadmap files written immediately (not draft)
- [ ] User feedback incorporated (if any)
- [ ] ROADMAP.md phases continue from previous milestone
- [ ] All commits made when `planning.commit_docs` is true
- [ ] User knows next step: `/grd:discuss-phase [N]`

**Atomic commits:** Each phase commits its artifacts immediately.
</success_criteria>
