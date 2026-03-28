---
template_version: 1
purpose: Formal specification of all valid state transitions in GRD
---

# GRD State Machine Specification

Reference document specifying all valid entity lifecycles, state ownership, and transition triggers across the GRD system.

---

## Entity Lifecycles

### Project

```
Created → Active → Paused → Active → Complete → Archived
```

- **Owner file**: `.grd/PROJECT.md` (status), `.grd/STATE.md` (position)
- **Created → Active**: `/grd:new-project` completes (ROADMAP.md exists, STATE.md initialized)
- **Active → Paused**: `/grd:pause-work` (explicit user action, writes `.continue-here` file)
- **Paused → Active**: `/grd:resume-work` (restores context from `.continue-here`)
- **Active → Complete**: All phases reach `complete` status
- **Complete → Archived**: `/grd:complete-milestone` (archives ROADMAP.md, REQUIREMENTS.md to `milestones/`, updates MILESTONES.md)

### Phase

```
Not started → Discussed → Researched → Planned → Executing → Phase complete → Verified → Complete
                                                      ↓
                                                   Blocked → (resolve) → Executing
```

Disk status values (from `roadmap_analyze`): `no_directory`, `empty`, `discussed`, `researched`, `planned`, `partial`, `complete`

- **Owner files**: ROADMAP.md (phase section, checkbox), STATE.md (Current Phase, Status)
- **Not started → Discussed**: `/grd:discuss-phase` completes (`{NN}-CONTEXT.md` created in phase directory)
- **Discussed → Researched**: `/grd:research-phase` completes (`{NN}-RESEARCH.md` created)
- **Not started → Researched**: `/grd:plan-phase` with research enabled (skips discuss, creates RESEARCH.md directly)
- **Researched → Planned**: `/grd:plan-phase` completes (`{NN}-{plan}-PLAN.md` files created with wave frontmatter)
- **Planned → Executing**: `/grd:execute-phase` starts (STATE.md Status set to "Ready to execute", Current Plan set to 1)
- **Executing → Phase complete**: `grd state advance` when `currentPlan >= totalPlans` (Status set to "Phase complete — ready for verification")
- **Phase complete → Verified**: `/grd:verify-work` completes (`{NN}-VERIFICATION.md` and/or `{NN}-VALIDATION.md` created)
- **Verified → Complete**: `grd phase complete {N}` (ROADMAP checkbox marked `[x]`, STATE.md advances to next phase)
- **Executing → Blocked**: Dependency not met or failure encountered (blocker added via `grd state add-blocker`)
- **Blocked → Executing**: Blocker resolved via `grd state resolve-blocker`

### Phase Failure States

| State | Triggered By | Recovery |
|-------|-------------|----------|
| Planning failed | /grd:plan-phase unable to produce valid plan after 3 attempts | Re-run /grd:research-phase, then retry planning |
| Execution failed | Executor returns unrecoverable failure | See RECOVERY-{plan}.md, option to rollback or resume |
| Verification failed | Verifier finds gaps, user chooses not to override | Run /grd:plan-phase --gaps to create fix plans |

### Verification Synthesis

Two verification tracks exist:
1. **Automated (verify-phase.md):** Computational checks via grd-verifier subagent → VERIFICATION.md
2. **Interactive (verify-work.md):** Conversational walkthrough with researcher → detailed check results

**When both are required:** Novel results, publication-bound phases, milestone-final phases
**When automated suffices:** Standard computations with clear benchmarks, intermediate phases
**When interactive suffices:** Qualitative analysis, literature review phases

**Combined pass criteria:** A phase is VERIFIED when:
- Automated verification score ≥ 80% AND no BLOCKER-level gaps, OR
- Interactive verification explicitly approves with documented reasoning

### Plan

```
Pending → In progress → Complete
               ↓
            Failed → (replan) → Pending
```

- **Owner file**: Plan frontmatter (`status` field), SUMMARY.md existence
- **Pending → In progress**: `grd state advance` sets Current Plan to this plan's number; executor begins work
- **In progress → Complete**: Executor creates matching `{NN}-{plan}-SUMMARY.md` with frontmatter (one-liner, key-files, methods, patterns, decisions, dependency-graph)
- **In progress → Failed**: Executor encounters unrecoverable error; plan marked failed
- **Failed → Pending**: `/grd:revise-phase` creates replacement plan

### task (within plan)

```
Pending → Active → [Checkpoint] → Active → Complete
                        ↓
                     Blocked
```

- **Owner**: Plan body (## Task N sections), executor agent state
- **Pending → Active**: Executor starts working on the task
- **Active → Checkpoint**: Plan has `interactive: true` in frontmatter; executor pauses for user review
- **Checkpoint → Active**: User approves checkpoint; executor resumes
- **Active → Complete**: Task deliverables produced
- **Active → Blocked**: External dependency or user input needed

### Milestone

```
Active → Audited → Complete → Archived
```

- **Owner files**: ROADMAP.md, MILESTONES.md, `milestones/` archive directory
- **Active → Audited**: `/grd:audit-milestone` produces `{version}-MILESTONE-AUDIT.md`
- **Audited → Complete**: `/grd:complete-milestone {version}` (all phases verified)
- **Complete → Archived**: Same command archives ROADMAP.md and REQUIREMENTS.md to `milestones/{version}-*`, creates/appends MILESTONES.md entry

---

## State Ownership Table

| State Field | Owner File | Updated By |
|-------------|-----------|------------|
| Current Phase | STATE.md (`**Current Phase:**`) | `grd state update`, `grd phase complete` |
| Current Phase Name | STATE.md (`**Current Phase Name:**`) | `grd state update`, `grd phase complete` |
| Total Phases | STATE.md (`**Total Phases:**`) | `grd phase add/remove` |
| Current Plan | STATE.md (`**Current Plan:**`) | `grd state advance` |
| Total Plans in Phase | STATE.md (`**Total Plans in Phase:**`) | Workflow orchestrator |
| Status | STATE.md (`**Status:**`) | `grd state update`, `grd state advance`, `grd phase complete` |
| Progress | STATE.md (`**Progress:**`) | `grd state update-progress` (counts SUMMARY.md files across all phases) |
| Last Activity | STATE.md (`**Last Activity:**`) | Most state-modifying commands |
| Paused At | STATE.md (`**Paused At:**`) | `/grd:pause-work` (set), `/grd:resume-work` (clear) |
| Convention Lock | state.json (`convention_lock`) | `grd convention set/list/check` |
| Intermediate Results | state.json (`intermediate_results`) + STATE.md | `grd result add` |
| Decisions | STATE.md (Decisions section) + DECISIONS.md | `grd state add-decision` |
| Blockers | STATE.md (Blockers section) | `grd state add-blocker/resolve-blocker` |
| Approximations | state.json (`approximations`) | `grd approximation add/list/check` |
| Propagated Uncertainties | state.json (`propagated_uncertainties`) | `grd uncertainty add/list` |
| Session Continuity | STATE.md (Session section) | `grd state record-session` |
| Performance Metrics | STATE.md (Performance Metrics table) | `grd state record-metric` |
| Phase Completion | ROADMAP.md (checkbox `[x]`) | `grd phase complete` |
| Milestone Completion | MILESTONES.md | `grd milestone complete` |

---

## Transition Triggers

| Transition | Command / Workflow | Files Modified |
|-----------|---------|---------------|
| Project: Created → Active | `/grd:new-project` | PROJECT.md, ROADMAP.md, STATE.md, state.json, config.json created |
| Project: Active → Paused | `/grd:pause-work` | STATE.md (Paused At set), `.continue-here` created |
| Project: Paused → Active | `/grd:resume-work` | STATE.md (Paused At cleared), `.continue-here` consumed |
| Phase: Not started → Discussed | `/grd:discuss-phase` | `{NN}-CONTEXT.md` created |
| Phase: → Researched | `/grd:research-phase` or `/grd:plan-phase` | `{NN}-RESEARCH.md` created |
| Phase: Researched → Planned | `/grd:plan-phase` | `{NN}-{plan}-PLAN.md` files created, STATE.md updated |
| Phase: Planned → Executing | `/grd:execute-phase` | STATE.md (Status, Current Plan updated) |
| Plan: advance within phase | `grd state advance` | STATE.md (Current Plan incremented, Status updated) |
| Plan: complete | Executor creates SUMMARY.md | `{NN}-{plan}-SUMMARY.md` created |
| Phase: → Phase complete | `grd state advance` (last plan) | STATE.md (Status = "Phase complete — ready for verification") |
| Phase: → Verified | `/grd:verify-work` | `{NN}-VERIFICATION.md` and/or `{NN}-VALIDATION.md` created |
| Phase: Verified → Complete | `grd phase complete {N}` | ROADMAP.md (checkbox), STATE.md (next phase), progress updated |
| Milestone: → Audited | `/grd:audit-milestone` | `{version}-MILESTONE-AUDIT.md` created |
| Milestone: → Archived | `/grd:complete-milestone` | MILESTONES.md updated, files archived to `milestones/` |
| Decision recorded | `grd state add-decision` | STATE.md (Decisions section), state.json synced |
| Blocker added | `grd state add-blocker` | STATE.md (Blockers section), state.json synced |
| Blocker resolved | `grd state resolve-blocker` | STATE.md (Blockers section), state.json synced |
| Metric recorded | `grd state record-metric` | STATE.md (Performance Metrics table), state.json synced |
| Progress recalculated | `grd state update-progress` | STATE.md (Progress bar), state.json synced |
| Session recorded | `grd state record-session` | STATE.md (Session section), state.json synced |
| State compacted | `grd state compact` | STATE.md (trimmed), STATE-ARCHIVE.md (appended) |

---

## Status Vocabulary Mapping

Three status systems coexist. The **disk status** (from `roadmap_analyze`) is the canonical internal representation. ROADMAP.md and STATE.md use display labels.

| Disk Status (canonical) | ROADMAP.md Display | STATE.md Status | Description |
|------------------------|--------------------|-----------------|-------------|
| `no_directory` | Not started | — | Phase directory does not exist |
| `empty` | Not started | — | Phase directory exists but is empty |
| `discussed` | Not started | Ready to plan | Context file exists (`{NN}-CONTEXT.md`) |
| `researched` | Not started | Ready to plan | Research file exists (`{NN}-RESEARCH.md`) |
| `planned` | Not started | Ready to execute | Plan files exist (`{NN}-{plan}-PLAN.md`) |
| `partial` | In progress | Executing | Some summaries exist (execution in progress) |
| `complete` | Complete | Phase complete — ready for verification | All plan summaries exist |
| — | Blocked | Blocked | Blocker added (not a disk status) |
| — | Deferred | — | Phase pushed to later (not a disk status) |

**Notes:**
- Disk statuses are detected by scanning phase directory contents (see `roadmap_analyze`)
- ROADMAP.md statuses are display labels in the Progress table
- STATE.md Status reflects the current phase's workflow position
- "Blocked" and "Deferred" are workflow states, not detected from disk

---

## Dual-Write Consistency

STATE.md and state.json are kept in sync via `sync_state_json()`:

- **STATE.md** is the human-readable source, rendered by `generate_state_markdown()`
- **state.json** is the machine-readable sidecar, with additional fields not in markdown (convention_lock, approximations, propagated_uncertainties, intermediate_results as structured objects)
- Every write to STATE.md triggers `sync_state_json()` which parses markdown and merges into existing JSON
- Every write to state.json via `save_state_json()` also regenerates STATE.md
- `state_validate` cross-checks position fields between both files
- `state.json.bak` provides crash recovery if state.json becomes corrupt

---

## Invariants

1. **Phase numbering is sequential** for integer phases (gaps detected by `validate_consistency`)
2. **Decimal phases** (e.g., 06.1, 06.2) are inserted between integer phases and renumbered on removal
3. **Every SUMMARY.md must have a matching PLAN.md** (orphan summaries flagged by consistency check)
4. **Plan wave ordering**: a plan cannot depend on a plan in the same or later wave
5. **No circular dependencies** between plans (validated by topological sort in `validate_waves`)
6. **Convention lock is append-only** in spirit: conventions should not be silently changed
7. **Decisions are append-only** in STATE.md; full log lives in DECISIONS.md
8. **Progress percentage** = (total SUMMARY.md files) / (total PLAN.md files) across all phases
