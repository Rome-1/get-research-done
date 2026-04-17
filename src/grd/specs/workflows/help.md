<purpose>
Display the complete GRD command reference. Output ONLY the reference content. Do NOT add project-specific analysis, git status, next-step suggestions, or any commentary beyond the reference.
</purpose>

<process>

<step name="contextual_help">
## Contextual Help (State-Aware Variant)

When a state-aware help view is requested, show guidance based on project state:

1. Check project state via grd CLI
2. Show ONLY the 5-8 commands relevant NOW:

**No project exists:**
```
Getting started:
  /grd:new-project         — Start a new research project
  /grd:new-project --minimal — Quick start with minimal setup
  /grd:map-research        — Map an existing research project
```

**Project exists, no plans yet:**
```
Phase {N}: {name}
  /grd:discuss-phase {N}   — Gather context before planning
  /grd:plan-phase {N}      — Create execution plan
  /grd:progress --full     — See full project status
```

**Plans exist, not executed:**
```
Ready to execute:
  /grd:execute-phase {N}   — Execute phase {N} plans
  /grd:show-phase {N}      — Review phase details first
```

**Phase complete:**
```
Phase {N} complete:
  /grd:discuss-phase {N+1}  — Gather context before planning the next phase
  /grd:plan-phase {N+1}    — Create execution plan
  /grd:complete-milestone   — If all phases done
```

**Manuscript exists, no referee report yet:**
```
Publication workflow:
  /grd:peer-review         — Run manuscript peer review inside the current project
  /grd:arxiv-submission    — Package only after review passes
```

**Referee report exists:**
```
Revision workflow:
  /grd:respond-to-referees — Draft responses and revise the manuscript
  /grd:peer-review         — Re-run peer review after revision
```

For full command reference: `/grd:help --all`
</step>

<step name="concepts">
## GRD Concepts

GRD organizes physics research into a clear hierarchy:

```
Project ─── the overall research goal
  └─ Milestone ─── a major research objective (e.g., "v1.0: derive and validate")
       └─ Phase ─── one investigation step (e.g., "Phase 3: Monte Carlo validation")
            └─ Plan ─── a concrete execution plan (e.g., "Plan 01: implement Metropolis")
                 └─ Task ─── an atomic work unit (e.g., "Task 2: run thermalization")
```

**Typical workflow:**
1. `/grd:new-project` — Define research question, survey literature, create roadmap
2. `/grd:discuss-phase N` — Clarify the phase before planning
3. `/grd:plan-phase N` — Create detailed plans for phase N
4. `/grd:execute-phase N` — Run all plans (derivations, simulations, analysis)
5. `/grd:verify-work` — Verify physics correctness
6. Repeat 2-5 for each phase
7. `/grd:write-paper` — Generate publication from results
8. `/grd:peer-review` — Run manuscript review before submission inside the current project
9. `/grd:respond-to-referees` — Address reviewer comments if needed
10. `/grd:arxiv-submission` — Package the approved manuscript

**Example:** Studying the 3D Ising critical exponent:
- Phase 1: Set up Wolff cluster MC algorithm
- Phase 2: Run simulations at multiple temperatures and system sizes
- Phase 3: Finite-size scaling analysis to extract nu
- Phase 4: Compare with known results, write paper
</step>

</process>

<reference>
# GRD Command Reference

**GRD** (Get Research Done) creates hierarchical research plans optimized for solo agentic physics research with AI research agents.

## Startup Checklist

Use the shared onboarding surfaces in the README or installer output for the longer beginner-first startup order and prerequisites.

1. `grd:help` - See the command reference first.
2. `grd:start` - Let GRD choose the safest first step for the current folder.
3. `grd:tour` - Get a read-only walkthrough before you choose.
4. `grd:new-project` or `grd:map-research` - Begin the actual work path once you know the folder state.
5. `grd:resume-work` - Continue later from the selected project's canonical state.
6. `grd:settings` - Change autonomy, permissions, or runtime preferences after your first successful start or later.
7. `grd:set-tier-models` - Directly pin concrete `tier-1`, `tier-2`, and `tier-3` model ids for the active runtime.

## Invocation Surfaces

This reference lists canonical in-runtime slash-command names in `/grd:*` form.

- If you are new to terminals or runtime setup, start with the Beginner Onboarding Hub linked from the README and installer output.
- That shared onboarding surface keeps the OS guides, runtime guides, and startup checklist in one place.
- Use these names inside the installed agent/runtime command surface.
- The local `grd` CLI may expose different `grd ...` subcommands and grouping. Use `grd --help` to inspect the executable CLI surface directly.
- If you need to validate whether a slash-command can run in the current workspace, use `grd validate command-context grd:<name>`.

## Quick Start

1. `/grd:new-project` - Initialize research project (includes literature survey, objectives, roadmap)
2. `/grd:discuss-phase 1` - Clarify the first phase before planning
3. `/grd:plan-phase 1` - Create detailed plan for first phase
4. `/grd:execute-phase 1` - Execute the phase

Use the path that matches your current situation:

**New work**
1. `grd:start` - Guided first-run router that chooses the safest first step for this folder
2. `grd:tour` - Get a read-only overview before choosing
3. `grd:new-project` - Create a full GRD project
4. `grd:new-project --minimal` - Create a project through the shortest setup path

**Existing work**
1. `grd:map-research` - Map an existing folder before turning it into a GRD project
2. `grd:new-project` - Turn that mapped context into a full GRD project

**Returning work**
1. `grd resume` - Reopen the current-workspace recovery snapshot from your normal terminal
2. `grd resume --recent` - Find a different workspace first from your normal terminal
3. `grd:resume-work` - Continue inside the reopened project's canonical state
4. `grd:progress` - See the broader project snapshot
5. `grd:suggest-next` - Get the fastest next action
6. `grd observe execution` - Watch progress / waiting state, conservative `possibly stalled` wording, and the next read-only checks from your normal terminal
7. `grd cost` - Review recorded machine-local usage / cost from your normal terminal

**Post-startup settings**
1. `grd:settings` - Change autonomy, permissions, and broader runtime preferences after your first successful start or later
2. `grd:set-tier-models` - Pin concrete `tier-1`, `tier-2`, and `tier-3` model ids only

When a side investigation appears later, use `grd:tangent` first. It is the chooser for stay / quick / defer / branch. Use `grd:branch-hypothesis` only when that tangent needs its own git-backed branch.

## Command Index

This is the compact grouped list of runtime commands. For normal-terminal install, readiness, and diagnostics commands, use `grd --help`.

### Starter commands

- `grd:help` - Show the quick start or command index
- `grd:start` - Guided first-run router for the safest first path in the current folder
- `grd:tour` - Show a read-only overview of the main commands
- `grd:new-project` - Create a full GRD project
- `grd:new-project --minimal` - Create a GRD project through the shortest setup path
- `grd:map-research` - Map an existing research folder before planning
- `grd:resume-work` - Resume the selected project's canonical state inside the runtime
- `grd:progress` - Review project status and likely next steps
- `grd:suggest-next` - Ask only for the next best action
- `grd:explain [concept]` - Explain a concept, method, result, or paper
- `grd:quick` - Run one small bounded task without the full phase workflow

### Planning and execution

- `grd:discuss-phase <number>` - Capture phase context before planning
- `grd:research-phase <number>` - Run a focused phase literature survey
- `grd:list-phase-assumptions <number>` - Preview the planned phase approach
- `grd:discover [phase or topic]` - Survey methods, literature, and tools before planning
- `grd:show-phase <number>` - Inspect one phase's artifacts and status
- `grd:plan-phase <number>` - Build a detailed execution plan for a phase
- `grd:execute-phase <phase-number>` - Run all plans in a phase
- `grd:autonomous [--from N]` - Run all remaining phases autonomously (discuss→plan→execute→verify each)
- `grd:derive-equation` - Run a rigorous derivation workflow

### Roadmap and milestones

- `grd:add-phase <description>` - Append a new phase to the roadmap
- `grd:insert-phase <after> <description>` - Insert urgent work between phases
- `grd:remove-phase <number>` - Remove a future phase and renumber later ones
- `grd:revise-phase <number> "<reason>"` - Supersede a completed phase with a replacement
- `grd:merge-phases <source> <target>` - Fold one phase's results into another
- `grd:new-milestone <name>` - Start the next milestone
- `grd:complete-milestone <version>` - Archive a completed milestone

### Validation and analysis

- `grd:verify-work [phase]` - Run physics verification checks
- `grd:debug [issue description]` - Start a persistent debug session
- `grd:dimensional-analysis` - Check dimensional consistency
- `grd:limiting-cases` - Check known limits
- `grd:numerical-convergence` - Run convergence checks for numerical work
- `grd:compare-experiment` - Compare results against external data
- `grd:compare-results` - Compare internal results or baselines
- `grd:validate-conventions [phase]` - Check notation and convention consistency
- `grd:regression-check [phase]` - Scan for regressions in recorded verification state
- `grd:health` - Run project health checks
- `grd:parameter-sweep [phase]` - Run a structured parameter sweep
- `grd:sensitivity-analysis` - Rank which inputs matter most
- `grd:error-propagation` - Track uncertainties through a calculation chain

### Knowledge authoring

- `grd:digest-knowledge [topic|arXiv id|source file|knowledge path]` - Create or update a draft knowledge doc from a topic, arXiv paper, source file, or explicit `GRD/knowledge/` path
- `grd:review-knowledge [knowledge path|knowledge id]` - Review a knowledge doc, write the review artifact, and promote fresh approved drafts to stable

### Writing and publication

- `grd:literature-review [topic]` - Create a structured literature review
- `grd:write-paper [title or topic] [--from-phases 1,2,3]` - Draft a paper from project results
- `grd:peer-review [paper directory or manuscript path]` - Run the staged review workflow
- `grd:respond-to-referees` - Draft referee responses and revise the paper
- `grd:arxiv-submission` - Package a built manuscript for arXiv
- `grd:slides [topic, audience, or source path]` - Create presentation slides

### Tangents, memory, and exports

- `grd:tangent [description]` - Chooser for stay / quick / defer / branch when a side investigation appears
- `grd:branch-hypothesis <description>` - Explicit git-backed alternative path for a side investigation
- `grd:compare-branches` - Compare results across hypothesis branches
- `grd:pause-work` - Save a continuation handoff before stepping away
- `grd:add-todo [description]` - Capture a task or idea
- `grd:check-todos [area]` - Review pending todos and pick one
- `grd:decisions [phase or keyword]` - Search the decision log
- `grd:graph` - Visualize phase dependencies
- `grd:export [--format html|latex|zip|all]` - Export project artifacts
- `grd:export-logs [--format jsonl|json|markdown] [--session <id>] [--last N] [--no-traces] [--output-dir <path>]` - Export observability logs
- `grd:error-patterns [category]` - Review common project-specific errors
- `grd:record-insight [description]` - Save a project-specific lesson
- `grd:audit-milestone [version]` - Audit milestone completion against goals
- `grd:plan-milestone-gaps` - Turn audit gaps into new phases

### Configuration and maintenance

- `grd:settings` - Guided autonomy, permissions, and runtime configuration after your first successful start or later
- `grd:set-tier-models` - Directly pin concrete tier model ids
- `grd:set-profile <profile>` - Switch the abstract model profile
- `grd:compact-state` - Archive old `STATE.md` entries
- `grd:sync-state` - Repair diverged `STATE.md` and `state.json`
- `grd:undo` - Roll back the last GRD operation with a safety checkpoint
- `grd:update` - Update GRD to the latest version
- `grd:reapply-patches` - Reapply local modifications after updating

## Detailed Command Reference

Use `grd:help --command <name>` when you want the detailed notes for one runtime command at a time.

### Core Workflow

```
/grd:new-project -> /grd:discuss-phase -> /grd:plan-phase -> /grd:execute-phase -> repeat
```

### Project Initialization

**`/grd:new-project`**
Initialize new research project through unified flow.

- Detects whether the current folder is an existing GRD project, existing non-GRD research, or a new folder
- Recommends the right entry point instead of forcing the user to guess
- Routes into `grd:resume-work`, `grd:suggest-next`, `grd:progress`, `grd:tour`, `grd:map-research`, `grd:new-project`, `grd:new-project --minimal`, `grd:help --all`, or `grd:explain`
- Does not create project artifacts itself; it is an onboarding router

Usage: `grd:start`

**`grd:tour`**
Show a guided beginner tour of the core GRD commands without taking action.

- Explains the main commands and when to use them
- Stays read-only and does not create files or route into another workflow
- Good optional first stop if you want a quick orientation before choosing a path

Usage: `grd:tour`

**`grd:new-project`**
Initialize a new research project through questioning, optional survey, scoping, and roadmap generation.

One command takes you from idea to ready-for-investigation:

- Deep questioning to understand the physics problem
- Optional literature survey (spawns 4 parallel scout agents)
- Research objectives definition with scoping
- Roadmap creation with phase breakdown and success criteria

Creates all `.grd/` artifacts:

- `PROJECT.md` — research question, theoretical framework, key parameters
- `config.json` — workflow settings (`autonomy`, `research_mode`, `execution.review_cadence`, `planning.commit_docs`, agent toggles)
- `research/` — literature survey (if selected)
- `REQUIREMENTS.md` — scoped research requirements with REQ-IDs
- `ROADMAP.md` — phases mapped to requirements
- `STATE.md` — project memory

**Flags:**

- `--minimal` — Skip deep questioning and literature survey. Creates project from a single description. Asks one question ("Describe your research project and phases"), then generates all `.grd/` artifacts with sensible defaults. Same file set as full mode, so all downstream commands work identically.
- `--minimal @file.md` — Create project directly from a markdown file describing your research and phases. Parses research question, phase list, and key parameters from the file. No interactive questions asked.
- `--auto` — Automatic mode with full depth. Expects research proposal via @ reference. Runs literature survey, requirements, and roadmap without interaction.

Usage: `/grd:new-project`
Usage: `/grd:new-project --minimal`
Usage: `/grd:new-project --minimal @plan.md`

**`/grd:map-research`**
Map an existing research project — theoretical framework, computations, conventions, and open questions.

- Spawns 4 parallel research-mapper agents to analyze project artifacts
- Creates `.grd/research-map/` with 7 structured documents
- Covers formalism, references, computational architecture, structure, conventions, validation, concerns
- Use before `/grd:new-project` on existing research projects

Usage: `/grd:map-research`

### Phase Planning

**`/grd:discuss-phase <number>`**
Help articulate your vision for a research phase before planning.

- Captures how you imagine this phase proceeding
- Creates CONTEXT.md with your approach, essentials, and boundaries
- Use when you have specific ideas about methods or approximations

Usage: `/grd:discuss-phase 2`

**`/grd:research-phase <number>`**
Comprehensive literature survey for a specific phase.

- Discovers known results, standard methods, available data
- Creates {phase}-RESEARCH.md with domain expert knowledge
- Use for phases involving unfamiliar techniques or contested results
- Goes beyond "which method" to deep domain knowledge

Usage: `/grd:research-phase 3`

**`/grd:list-phase-assumptions <number>`**
See what the agent plans to do before it starts.

- Shows the agent's intended approach for a phase
- Lets you course-correct if the approach is wrong
- No files created - conversational output only

Usage: `/grd:list-phase-assumptions 3`

**`/grd:discover [phase or topic] [--depth quick|medium|deep]`**
Run discovery phase to investigate methods, literature, and approaches before planning.

- Surveys known results, standard methods, and computational tools
- Depth levels: quick (summary), medium (detailed), deep (comprehensive)
- Creates discovery artifacts consumed by planner or standalone analysis
- Use when entering an unfamiliar subfield or technique

Usage: `/grd:discover 3`
Usage: `/grd:discover "finite-temperature RG flow" --depth deep`
Usage: `/grd:discover 3 --depth deep`

**`/grd:show-phase <number>`**
Inspect a single phase's artifacts, status, and results.

- Shows phase goal, plans, summaries, and verification status
- Displays frontmatter metadata (wave, dependencies, status)
- Quick way to review what a phase produced

Usage: `/grd:show-phase 3`

**`/grd:plan-phase <number>`**
Create detailed execution plan for a specific phase.

- Generates `.grd/phases/XX-phase-name/XX-YY-PLAN.md`
- Breaks phase into concrete, actionable steps
- Includes verification criteria (limiting cases, consistency checks)
- Multiple plans per phase supported (XX-01, XX-02, etc.)

**Flags:**

- `--research` — Force literature research even if RESEARCH.md already exists
- `--skip-research` — Skip literature research entirely
- `--gaps` — Gap closure mode: plan from VERIFICATION.md issues instead of fresh research
- `--skip-verify` — Skip plan checker verification after planning
- `--light` — Produce simplified strategic outline (contract, constraints, high-level approach only)
- `--inline-discuss` — Run discuss-phase inline before planning (skip if already done)

Usage: `/grd:plan-phase 1`
Usage: `/grd:plan-phase 3 --research`
Usage: `/grd:plan-phase 5 --light --skip-verify`
Result: Creates `.grd/phases/01-framework-setup/01-01-PLAN.md`

### Execution

**`/grd:execute-phase <phase-number>`**
Execute all plans in a phase.

- Groups plans by wave (from frontmatter), executes waves sequentially
- Plans within each wave run in parallel via task tool
- Verifies phase goal after all plans complete (limiting cases, dimensional analysis, benchmarks)
- Updates REQUIREMENTS.md, ROADMAP.md, STATE.md

Usage: `/grd:execute-phase 5`

### Derivation

**`/grd:derive-equation`**
Perform a rigorous physics derivation with systematic verification at each step.

- States assumptions explicitly, establishes notation and conventions
- Performs step-by-step derivation with dimensional analysis at each stage
- Verifies intermediate results against known limits and symmetry properties
- Justifies and bounds all approximations with error estimates
- For theorem-bearing work, spawns `grd-check-proof` and blocks completion until the proof audit passes
- Produces a complete, self-contained derivation document with boxed final result

Usage: `/grd:derive-equation "derive the one-loop beta function"`

### Quick Mode

**`/grd:quick`**
Execute small, ad-hoc calculations with GRD guarantees but skip optional agents.

Quick mode uses the same system with a shorter path:

- Spawns planner + executor (skips literature scout, checker, validator)
- Quick tasks live in `.grd/quick/` separate from planned phases
- Updates STATE.md tracking (not ROADMAP.md)

Use when you know exactly what to calculate and the task is small enough to not need literature survey or validation.

Usage: `/grd:quick`
Result: Creates `.grd/quick/NNN-slug/PLAN.md`, `.grd/quick/NNN-slug/SUMMARY.md`

### Roadmap Management

**`/grd:add-phase <description>`**
Add new phase to end of current milestone.

- Appends to ROADMAP.md
- Uses next sequential number
- Updates phase directory structure

Usage: `/grd:add-phase "Compute finite-temperature corrections"`

**`/grd:insert-phase <after> <description>`**
Insert urgent work as decimal phase between existing phases.

- Creates intermediate phase (e.g., 7.1 between 7 and 8)
- Useful for discovered work that must happen mid-investigation
- Maintains phase ordering

Usage: `/grd:insert-phase 7 "Fix sign error in vertex function"`
Result: Creates Phase 7.1

**`/grd:remove-phase <number>`**
Remove a future phase and renumber subsequent phases.

- Deletes phase directory and all references
- Renumbers all subsequent phases to close the gap
- Only works on future (unstarted) phases
- Git commit preserves historical record

Usage: `/grd:remove-phase 17`
Result: Phase 17 deleted, phases 18-20 become 17-19

**`/grd:revise-phase <number> "<reason>"`**
Supersede a completed phase and create a replacement for iterative revision.

- Marks original phase as superseded (preserved as historical record)
- Creates replacement phase with decimal numbering (e.g., 3.1)
- Pre-populates replacement with context: what worked, what didn't, what to change
- Updates downstream dependency references
- Flags downstream phases that may also need revision
- Only works on completed phases (use /grd:remove-phase for future phases)

Usage: `/grd:revise-phase 3 "Sign error in vertex correction"`
Result: Phase 3 superseded, Phase 3.1 created with inherited context

**`/grd:merge-phases <source> <target>`**
Merge results from one phase into another.

- Copies artifacts (summaries, plans, data files) from source to target
- Merges intermediate results and decisions with phase attribution
- Updates roadmap to reflect the merge
- Useful for folding decimal phases back into parents or converging parallel branches

Usage: `/grd:merge-phases 2.1 2`

### Milestone Management

**`/grd:new-milestone <name>`**
Start a new research milestone through unified flow.

- Deep questioning to understand the next research direction
- Optional literature survey (spawns 4 parallel scout agents)
- Objectives definition with scoping
- Roadmap creation with phase breakdown
- Uses `planning.commit_docs` from init to decide whether milestone artifacts are committed immediately

Mirrors `/grd:new-project` flow for continuation projects (existing PROJECT.md).

Usage: `/grd:new-milestone "v2.0 Higher-order corrections"`

**`/grd:complete-milestone <version>`**
Archive completed milestone and prepare for next direction.

- Creates MILESTONES.md entry with results summary
- Archives full details to milestones/ directory
- Creates git tag for the release
- Prepares workspace for next research direction

Usage: `/grd:complete-milestone 1.1.0`

### Progress Tracking

**`/grd:progress`**
Check research status and intelligently route to next action.

- Shows visual progress bar and completion percentage
- Summarizes recent work from SUMMARY files
- Displays current position and what's next
- Lists key results and open issues
- Offers to execute next plan or create it if missing
- Detects 100% milestone completion
- Use `--brief` when returning and you only need orientation
- Use `--reconcile` only on the runtime `grd:progress` surface when state appears out of sync with disk artifacts
- The local CLI `grd progress` is a separate read-only renderer and uses `json|bar|table` instead of these runtime flags

Usage: `/grd:progress`
Usage: `/grd:progress --full` (detailed view with all phase artifacts)
Usage: `/grd:progress --brief` (compact one-line status)
Usage: `/grd:progress --reconcile` (fix diverged STATE.md and state.json)

### Session Management

**`/grd:resume-work`**
Resume research from previous session with full context restoration.

@{GRD_INSTALL_DIR}/references/orchestration/resume-vocabulary.md

Usage: `/grd:resume-work`

**`/grd:pause-work`**
Create context handoff when pausing work mid-phase.

**`grd:pause-work`**
Create a continuation handoff artifact when pausing work mid-phase.

- Creates the canonical `.continue-here.md` continuation handoff artifact with current state
- Updates the mirrored STATE.md session continuity entry
- Captures in-progress work context
- Run this before leaving mid-phase so `grd:resume-work` has an explicit recorded handoff artifact to restore from canonical continuation state

Usage: `/grd:pause-work`

### Todo Management

**`/grd:add-todo [description]`**
Capture idea or task as todo from current conversation.

- Extracts context from conversation (or uses provided description)
- Creates structured todo file in `.grd/todos/pending/`
- Infers area from context for grouping
- Checks for duplicates before creating
- Updates STATE.md todo count

Usage: `/grd:add-todo` (infers from conversation)
Usage: `/grd:add-todo Check if vertex correction satisfies Ward identity`

**`/grd:check-todos [area]`**
List pending todos and select one to work on.

- Lists all pending todos with title, area, age
- Optional area filter (e.g., `/grd:check-todos numerical`)
- Loads full context for selected todo
- Routes to appropriate action (work now, add to phase, think more)
- Moves todo to done/ when work begins

Usage: `/grd:check-todos`
Usage: `/grd:check-todos analytical`

### Validation

**`/grd:verify-work [phase]`**
Validate research results through systematic checks.

- Extracts testable results from SUMMARY.md files
- Checks limiting cases, dimensional analysis, conservation laws
- Compares against known benchmarks
- Automatically diagnoses failures and creates fix plans
- Ready for re-execution if issues found

Usage: `/grd:verify-work 3`

### Debugging

**`/grd:debug [issue description]`**
Systematic debugging of physics calculations with persistent state across context resets.

- Spawns grd-debugger agent with scientific method approach
- Maintains debug session state in `.grd/debug/`
- Survives context window resets — resumes from last checkpoint
- Archives resolved issues to `.grd/debug/resolved/`

Usage: `/grd:debug Sign error in self-energy diagram`

### Physics Validation

**`/grd:dimensional-analysis`**
Check dimensional consistency of equations and expressions.

- Verifies all terms have consistent units
- Checks final results have correct dimensions
- Flags dimensionless ratios and magic numbers

Usage: `/grd:dimensional-analysis 3`
Usage: `/grd:dimensional-analysis results/01-SUMMARY.md`

**`/grd:limiting-cases`**
Verify results reduce correctly in known limiting cases.

- Tests classical, non-relativistic, weak-coupling, thermodynamic limits
- Compares against textbook expressions in each limit
- Flags limits that are not recovered

Usage: `/grd:limiting-cases 3`
Usage: `/grd:limiting-cases results/01-SUMMARY.md`

**`/grd:numerical-convergence`**
Run systematic convergence tests on numerical computations.

- Tests convergence with grid refinement, time step, basis size
- Estimates convergence order via Richardson extrapolation
- Constructs error budgets for computed quantities

Usage: `/grd:numerical-convergence 3`
Usage: `/grd:numerical-convergence results/mesh-study.csv`

**`/grd:compare-experiment`**
Compare theoretical/numerical results against experimental data.

- Loads published experimental values and error bars
- Computes chi-squared or other goodness-of-fit measures
- Identifies systematic deviations and their possible origins

Usage: `/grd:compare-experiment predictions.csv experiment.csv`

**`/grd:compare-results [phase, artifact, or comparison target]`**
Compare internal results, baselines, or methods and emit a decisive verdict.

- Compares phase outputs, artifacts, or named comparison targets
- Surfaces agreement, tension, or failure in a single verdict-oriented view
- Useful when you need to compare internal baselines without reaching for external data

Usage: `/grd:compare-results 3`
Usage: `/grd:compare-results results/01-SUMMARY.md`

**`/grd:validate-conventions [phase]`**
Validate convention consistency across all phases.

- Checks metric signature, Fourier convention, natural units, gauge choice
- Detects convention drift where a symbol is redefined in a later phase
- Cross-checks locked conventions against all phase artifacts
- Scope to a single phase using the optional phase argument, or run across all completed phases

Usage: `/grd:validate-conventions`
Usage: `/grd:validate-conventions 3`

**`/grd:regression-check [phase]`**
Scan-only audit for regressions in already-recorded verification state.

- Detects convention conflicts where the same symbol is redefined with different values across completed SUMMARY artifacts
- Scans `SUMMARY.md` and `VERIFICATION.md` frontmatter rather than re-running numerical or physics verification
- Flags non-passing, invalid, or non-canonical `VERIFICATION.md` statuses in completed phases
- Uses canonical statuses `passed`, `gaps_found`, `expert_needed`, and `human_needed`
- Reports the affected phases and files for follow-up verification or repair
- Scope to a single phase using the optional phase argument, or run across all completed phases

Usage: `/grd:regression-check`
Usage: `/grd:regression-check 3`

**`/grd:health`**
Run project health checks and optionally auto-fix issues.

- Checks state, frontmatter, storage-path policy, and other project health surfaces
- Reports warnings and fixable issues before they become workflow blockers
- Supports `--fix` for automatic repair of common problems

Usage: `/grd:health`
Usage: `/grd:health --fix`

### Quantitative Analysis

**`/grd:parameter-sweep [phase]`**
Systematic parameter sweep with parallel execution and result aggregation.

- Varies one or more parameters across a specified range
- Uses wave-based parallelism for independent parameter values
- Collects results and produces summary tables
- Supports adaptive refinement near interesting features

Usage: `/grd:parameter-sweep 3 --param coupling --range 0:1:20`
Usage: `/grd:parameter-sweep 3 --adaptive`

**`/grd:sensitivity-analysis`**
Determine which input parameters most strongly affect output quantities.

- Computes partial derivatives and condition numbers
- Ranks parameters by sensitivity
- Identifies which measurements or calculations would most improve results
- Supports analytical and numerical methods

Usage: `/grd:sensitivity-analysis --target cross_section --params g,m,Lambda`
Usage: `/grd:sensitivity-analysis --target cross_section --params g,m,Lambda --method numerical`

**`/grd:error-propagation`**
Track how uncertainties propagate through multi-step calculations.

- Traces input uncertainties through intermediate results to final quantities
- Identifies dominant error sources
- Produces error budgets
- Scope to specific phases or full derivation chain

Usage: `/grd:error-propagation --target final_mass`
Usage: `/grd:error-propagation --phase-range 1:5`

### Research Publishing

**`/grd:write-paper [title or topic] [--from-phases 1,2,3]`**
Structure and write a physics paper from research results.

- Loads research digest from milestone completion (if available)
- Runs paper-readiness audit (conventions, verification, figures, citations)
- Spawns grd-paper-writer agents for each section (Results first, Abstract last)
- Generates LaTeX with proper equations, figures, and citations
- Spawns grd-bibliographer to verify all references
- Runs the staged peer-review panel with grd-referee as final adjudicator
- Supports revision mode for referee responses (bounded 3-iteration loop)

Usage: `/grd:write-paper "Critical exponents via RG"`
Usage: `/grd:write-paper --from-phases 1,3,5` (subset of phases)

**`/grd:peer-review [paper directory or manuscript path]`**
Run skeptical peer review on an existing manuscript within the current GRD project.

- Runs strict review preflight checks against project state, manuscript, artifacts, and reproducibility support
- Loads manuscript files, phase summaries, verification reports, bibliography audit, and artifact manifest
- Spawns a six-agent review panel: reader, literature, math, physics, significance, and final grd-referee adjudicator
- Produces stage artifacts under `.grd/review/` plus `.grd/REFEREE-REPORT{round_suffix}.md` and `.grd/REFEREE-REPORT{round_suffix}.tex`
- Routes the result to `/grd:respond-to-referees` or `/grd:arxiv-submission`
- Requires an initialized `.grd/PROJECT.md` workspace; manuscript paths do not bypass project preflight

Usage: `/grd:peer-review`
Usage: `/grd:peer-review paper/`

**`/grd:respond-to-referees`**
Structure point-by-point response to referee reports and revise the manuscript.
- Parses referee comments into structured items with severity levels
- Drafts both `.grd/AUTHOR-RESPONSE{round_suffix}.md` and `.grd/paper/REFEREE_RESPONSE{round_suffix}.md` with REF-xxx issue tracking (fixed/rebutted/acknowledged)
- Consumes `.grd/review/REVIEW-LEDGER*.json` and `.grd/review/REFEREE-DECISION*.json` when present to preserve blocking-issue context
- Spawns paper-writer agents for targeted section revisions
- Tracks new calculations required by referees as revision tasks
- Produces response letter from `templates/paper/referee-response.md`
- Bounded revision loop (max 3 iterations with re-review)

Usage: `/grd:respond-to-referees`

**`/grd:arxiv-submission`**
Prepare a completed paper for arXiv submission with validation and packaging.

- Requires a successful `grd paper-build` before packaging
- Optional local compiler smoke check if available
- Bibliography flattening (inline .bbl or resolve .bib)
- Figure format and resolution checking
- `\input` resolution into single .tex file (optional)
- Metadata verification (title, authors, abstract)
- Ancillary file packaging
- Generates submission-ready `.tar.gz`
- Produces checklist of remaining manual steps

Usage: `/grd:arxiv-submission`

**`/grd:explain [concept]`**
Explain a concept, method, notation, result, or paper in project context or from a standalone question.

- Spawns a `grd-explainer` agent and grounds the explanation in the active phase, manuscript, or local workflow when available
- Produces a structured explanation under `.grd/explanations/`
- Audits cited papers with `grd-bibliographer` and includes a reading path with openable links

Usage: `/grd:explain "Ward identity"`

**`/grd:suggest-next`**
Suggest the most impactful next action based on current project state.

- Scans phases, plans, verification status, blockers, and todos
- Produces a prioritized action list
- Local CLI fallback: `grd --raw suggest`
- Fastest way to answer "what should I do next?" without reading through progress reports
- Fastest post-resume command when you only need the next action

Usage: `/grd:suggest-next`

**`/grd:literature-review [topic]`**
Structured literature review for a physics research topic.

- Citation network analysis and open question identification
- Spawns `grd-literature-reviewer` for the structured review
- Spawns grd-bibliographer agent for citation verification
- Creates structured review with key papers, methods, and gaps

Usage: `/grd:literature-review "Sachdev-Ye-Kitaev model thermodynamics"`

**`grd:digest-knowledge [topic|arXiv id|source file|knowledge path]`**
Create or update a knowledge document draft from a topic, paper, source file, or explicit knowledge path.

**`/grd:branch-hypothesis <description>`**
Create a hypothesis branch for parallel investigation of an alternative approach.

- Creates git branch with isolated `.grd/` state
- Allows exploring alternative methods without disrupting main line
- Use when the tangent should become an explicit git-backed alternative path you intend to compare

Usage: `/grd:branch-hypothesis "Try perturbative RG instead of exact RG"`

**`/grd:compare-branches`**
Compare results across hypothesis branches side-by-side.

- Reads SUMMARY.md and VERIFICATION.md from each branch
- Shows which approach produced better results
- Helps decide which branch to merge back

Usage: `/grd:compare-branches`

### Decision Tracking

**`/grd:decisions [phase or keyword]`**
Display and search the cumulative decision log.

- Shows all recorded decisions across phases
- Filter by phase number or keyword
- Tracks sign conventions, approximation choices, gauge choices
- Reads from `.grd/DECISIONS.md`

Usage: `/grd:decisions`
Usage: `/grd:decisions 3`
Usage: `/grd:decisions "gauge"`

### Visualization & Export

**`/grd:graph`**
Visualize dependency graph across phases and identify gaps.

- Builds Mermaid diagram from phase frontmatter (provides/requires/affects)
- Identifies gaps where a phase requires something no other phase provides
- Computes critical path through the research project

Usage: `/grd:graph`

> **Note:** Wave dependency validation runs automatically when executing phases. To validate manually, use `grd phase validate-waves <phase>` — checks depends_on targets, file overlap within waves, wave consistency, and circular dependencies.

**`/grd:export [--format html|latex|zip|all]`**
Export research results to HTML, LaTeX, or ZIP package.

- HTML: standalone page with MathJax rendering
- LaTeX: document with proper equations and bibliography
- ZIP: complete archive of all planning artifacts

Usage: `/grd:export --format html`
Usage: `/grd:export --format all`

**`/grd:slides [topic, audience, or source path]`**
Create presentation slides from a GRD project or the current folder.

- Audits papers, figures, notes, code, and data to build a talk brief
- Asks targeted questions about audience, duration, format/toolchain, templates, technical depth, and whether to refresh or extend existing slide assets
- Defaults toward Beamer for equation-heavy talks and uses markdown or native decks when that fits better
- Produces an outline plus deck source files in `slides/`

Usage: `/grd:slides "Group meeting update on finite-temperature RG"`
Usage: `/grd:slides -- "20 minute seminar for condensed matter theorists"`

**`/grd:error-patterns [category]`**
View accumulated physics error patterns for this project.

- Shows common mistakes discovered during debugging and verification
- Optional category filter (sign, dimension, approximation, etc.)
- Helps avoid repeating known pitfalls

Usage: `/grd:error-patterns`
Usage: `/grd:error-patterns sign`

**`/grd:record-insight [description]`**
Record a project-specific learning or pattern to the insights ledger.

- Records error patterns, convention pitfalls, verification lessons
- Checks for duplicates before adding
- Categorizes into appropriate section (Debugging Patterns, Verification Lessons, etc.)
- Updates `.grd/INSIGHTS.md`

Usage: `/grd:record-insight`
Usage: `/grd:record-insight Sign error in Wick contractions with mostly-minus metric`

### Milestone Auditing

**`/grd:audit-milestone [version]`**
Audit milestone completion against original objectives.

- Reads all phase VERIFICATION.md files
- Checks objectives coverage
- Spawns cross-check agent for consistency between phases
- Creates MILESTONE-AUDIT.md with gaps and open questions

Usage: `/grd:audit-milestone`

**`/grd:plan-milestone-gaps`**
Create phases to close gaps identified by audit.

- Reads MILESTONE-AUDIT.md and groups gaps into phases
- Prioritizes by objective priority
- Adds gap closure phases to ROADMAP.md
- Ready for `/grd:plan-phase` on new phases

Usage: `/grd:plan-milestone-gaps`

### Configuration

**`/grd:settings`**
Configure workflow toggles, model profile, `execution.review_cadence`, and runtime-specific tier model overrides interactively.

- Choose how often GRD should pause for you (`Balanced (Recommended)` is the best default for most unattended runs)
- Review unattended execution budgets and other bounded continuation limits before leaving runs alone
- Start with a qualitative model-cost posture: `Max quality`, `Balanced`, or `Budget-aware`
- Sync runtime-owned permissions after autonomy changes when the active runtime supports it
- If settings reports a relaunch is required, the new autonomy level is not unattended-ready yet
- Toggle plan researcher, plan checker, and execution verifier agents
- Configure inter-wave verification gates (`execution.review_cadence`: `dense`, `adaptive`, or `sparse`)
- Toggle parallel execution of wave plans
- Select model profile (deep-theory/numerical/exploratory/review/paper-writing); `review` with runtime defaults is the safest first choice
- Let that posture drive whether you keep runtime defaults or pin concrete runtime model strings for `tier-1`, `tier-2`, and `tier-3`
- Configure whether planning artifacts are committed (`planning.commit_docs`)
- Configure git branching strategy (`git.branching_strategy`: `none`, `per-phase`, or `per-milestone`)
- Updates `.grd/config.json`

Usage: `/grd:settings`

**`/grd:set-profile <profile>`**
Quick switch model profile for GRD agents. Use `/grd:settings` to pin concrete runtime model IDs per tier.

- `deep-theory` — tier-1 (highest capability) for all reasoning-intensive agents (formal derivations, proofs)
- `numerical` — tier-1 for planning/verification, tier-2 for execution (simulations, numerics)
- `exploratory` — tier-1 for planner/researchers, tier-2 for execution (hypothesis generation)
- `review` (default) — tier-1 for verifier/checker/debugger, tier-2 for execution (validation focus)
- `paper-writing` — tier-1 for planner/executor/synthesizer, tier-2 for verification

Usage: `/grd:set-profile deep-theory`

### Utility Commands

**`/grd:compact-state`**
Archive historical entries from STATE.md to keep it lean.

- Moves old decisions, metrics, and resolved blockers to STATE-ARCHIVE.md
- Keeps STATE.md under the target line budget (~150 lines)
- Triggered automatically when STATE.md exceeds 1500 lines

Usage: `/grd:compact-state`
Usage: `/grd:compact-state --force` (skip line-count check)

**`/grd:sync-state`**
Reconcile diverged STATE.md and state.json after manual edits or corruption.

- Detects mismatches between human-readable STATE.md and structured state.json
- Resolves by choosing the more recent or more complete source
- Fixes broken convention locks, missing phase counters, or stale progress bars
- Use after manual edits to STATE.md or after a crash during state updates

Usage: `/grd:sync-state`

**`/grd:undo`**
Rollback last GRD operation with safety checkpoint.

- Creates a safety tag before reverting so the undo itself is reversible
- Reverts only GRD-related commits (not arbitrary git history)
- Rejects merge commits — manual resolution required

Usage: `/grd:undo`

**`/grd:update`**
Update GRD to latest version with changelog display.

- Pulls latest GRD files from the repository
- Shows changelog of what changed since your version
- Preserves local modifications (use `/grd:reapply-patches` after if needed)

Usage: `/grd:update`

**`/grd:reapply-patches`**
Reapply local modifications after a GRD update.

- Detects and replays customizations you made to GRD files
- Use after `/grd:update` if you have local workflow or template modifications

Usage: `/grd:reapply-patches`

**`/grd:help`**
Show this command reference.

## Files & Structure

The literature survey lives under `GRD/literature/`, and reviewed knowledge docs live under `GRD/knowledge/` with review artifacts in `GRD/knowledge/reviews/`.

```
.grd/
|-- PROJECT.md            # Research question, framework, parameters
|-- REQUIREMENTS.md       # Scoped research requirements with REQ-IDs
|-- ROADMAP.md            # Current phase breakdown
|-- STATE.md              # Project memory & context
|-- MILESTONES.md         # Milestone history
|-- config.json           # Workflow mode & gates
|-- literature/           # Literature survey results and citation artifacts
|   |-- PRIOR-WORK.md     # Established results in the field
|   |-- METHODS.md        # Standard methods and tools
|   |-- COMPUTATIONAL.md  # Computational approaches and tools
|   |-- PITFALLS.md       # Known pitfalls and open problems
|   +-- SUMMARY.md        # Synthesized survey
|-- knowledge/            # Knowledge docs and typed review artifacts
|   |-- K-*.md            # Draft, in_review, stable, or superseded knowledge docs
|   +-- reviews/          # Deterministic review artifacts
|-- research-map/         # Theory map (existing research projects)
|   |-- FORMALISM.md      # Mathematical framework and key equations
|   |-- REFERENCES.md     # Key papers and their relationships
|   |-- ARCHITECTURE.md   # Computation flow and methodology
|   |-- STRUCTURE.md      # Project layout, key files
|   |-- CONVENTIONS.md    # Notation standards, unit systems
|   |-- VALIDATION.md     # Known results for benchmarking
|   +-- CONCERNS.md       # Open questions, known issues
|-- todos/                # Captured ideas and research tasks
|   |-- pending/          # Todos waiting to be worked on
|   +-- done/             # Completed todos
|-- debug/                # Active debug sessions
|   +-- resolved/         # Archived resolved issues
|-- quick/                # Ad-hoc task plans and summaries
|-- milestones/           # Archived milestone data
+-- phases/
    |-- 01-analytical-setup/
    |   |-- 01-01-PLAN.md
    |   |-- 01-01-SUMMARY.md
    |   +-- 01-VERIFICATION.md
    +-- 02-numerical-validation/
        |-- 02-01-PLAN.md
        +-- 02-01-SUMMARY.md
```

## Workflow Modes

Set during `/grd:new-project` or changed later with `/grd:settings`:

**Supervised**

- Confirms each major step
- Uses the most checkpoints
- Best for high-stakes work or learning the workflow
- Best when you plan to stay nearby and approve each physics-bearing move

**Balanced (Recommended)**

- Handles routine work automatically
- Pauses on physics decisions, ambiguities, blockers, or scope changes
- Best default for most projects
- Best first choice for unattended runs because it still pauses on important physics, scope, and blocker decisions

**YOLO**

- Fastest and least interactive
- Auto-approves checkpoints and keeps going unless a hard stop fires
- Best when you want maximum speed and minimal interruptions
- Use only after `grd:settings` reports runtime permissions are synchronized and no relaunch is still required

Change anytime with `grd:settings`. If it says a relaunch is required, the new autonomy level is not unattended-ready yet.

## Planning Configuration

Configure how planning artifacts are managed in `.grd/config.json`:

**`planning.commit_docs`** (default: `true`)

- `true`: Planning artifacts committed to git (standard workflow)
- `false`: Planning artifacts kept local-only, not committed

When `planning.commit_docs: false`:

- Add `.grd/` to your `.gitignore`
- Useful for collaborative projects, shared repos, or keeping planning private
- All planning files still work normally, just not tracked in git

Example config:

```json
{
  "execution": {
    "review_cadence": "adaptive"
  },
  "planning": {
    "commit_docs": false
  }
}
```

## Common Workflows

**Starting a new research project:**

```
/grd:new-project        # Unified flow: questioning -> survey -> discuss -> objectives -> roadmap
/clear
/grd:discuss-phase 1    # Gather context and clarify approach
/clear
/grd:plan-phase 1       # Create plans for first phase
/clear
/grd:execute-phase 1    # Execute all plans in phase
```

**Fast project bootstrap (skip deep questioning):**

```
/grd:new-project --minimal              # One question, then auto-generate everything
/grd:new-project --minimal @plan.md     # Generate from existing research plan file
```

**Leaving and returning after a break:**

```
/grd:progress  # See where you left off and continue
```

**Normal terminal, read-only recovery snapshot:**

```
grd resume
```

**Normal terminal, read-only machine-local usage / cost summary:**

```
grd cost
```

Read-only machine-local usage / cost summary from recorded local telemetry, optional USD budget guardrails, and the current profile tier mix; advisory only, not live budget enforcement or provider billing truth. If telemetry is missing, the USD view stays partial or estimated rather than exact.

**Adding urgent mid-milestone work:**

```
/grd:insert-phase 5 "Fix sign error in renormalization group equation"
/grd:plan-phase 5.1
/grd:execute-phase 5.1
```

**Completing a milestone:**

```
/grd:complete-milestone 1.1.0
/clear
/grd:new-milestone  # Start next milestone (questioning -> survey -> objectives -> roadmap)
```

**Capturing ideas during work:**

```
/grd:add-todo                                      # Capture from conversation context
/grd:add-todo Check finite-size scaling exponent    # Capture with explicit description
/grd:check-todos                                    # Review and work on todos
/grd:check-todos numerical                          # Filter by area
```

## Getting Help

- Read `.grd/PROJECT.md` for research question and framework
- Read `.grd/STATE.md` for current context and key results
- Check `.grd/ROADMAP.md` for phase status
- Run `/grd:progress` to check where you are
  </reference>

<success_criteria>
- [ ] Available commands listed with descriptions
- [ ] Common workflows shown with examples
- [ ] Quick reference table presented
- [ ] Next action guidance provided based on current project state
</success_criteria>
