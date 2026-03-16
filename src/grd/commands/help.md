---
name: grd:help
description: Show available GRD commands and usage guide
argument-hint: "[--all]"
context_mode: global
---

<!-- Tool names and @ includes are platform-specific. The installer translates paths for your runtime. -->
<!-- Allowed-tools are runtime-specific. Other platforms may use different tool interfaces. -->

<objective>
Display the complete GRD command reference.

Output ONLY the reference content below. Do NOT add:

- Project-specific analysis
- Git status or file context
- Next-step suggestions
- Any commentary beyond the reference
  </objective>

<execution_context>
@{GRD_INSTALL_DIR}/workflows/help.md
</execution_context>

<process>

## Step 1: Parse Arguments

Check if the user passed `--all` as an argument.

- If `$ARGUMENTS` contains `--all`: display the **Full Command Reference** (step 3).
- If `$ARGUMENTS` is empty or does not contain `--all`: display the **Quick Start** (step 2) only.

## Step 2: Quick Start (Default Output)

Output this and STOP (do not display the full reference):

# GRD Command Reference

**GRD** (Get Research Done) — agentic physics research with AI research agents.

## Quick Start

1. `/grd:new-project` — Initialize research project
2. `/grd:plan-phase <N>` — Plan a research phase
3. `/grd:execute-phase <N>` — Execute phase plans
4. `/grd:verify-work [phase]` — Verify research results
5. `/grd:progress` — Check status and get next action
6. `/grd:complete-milestone` — Archive completed milestone
7. `/grd:help --all` — Full command reference

**Workflow:** new-project → plan-phase → execute-phase → verify-work → repeat → complete-milestone
**Publication:** write-paper → peer-review → respond-to-referees → arxiv-submission

Run `/grd:help --all` for all 61 commands.

--- END of default output. STOP here. ---

## Step 3: Full Command Reference (--all)

Output the complete GRD command reference from the loaded help workflow.
Display the reference content directly — no additions or modifications.

# GRD Command Reference

**GRD** (Get Research Done) creates hierarchical research plans optimized for solo agentic physics research with AI research agents.

## Quick Start

1. `/grd:new-project` - Initialize research project (includes literature survey, objectives, roadmap)
2. `/grd:plan-phase 1` - Create detailed plan for first phase
3. `/grd:execute-phase 1` - Execute the phase

## Core Workflow

```
/grd:new-project -> /grd:plan-phase -> /grd:execute-phase -> repeat
```

### Project Initialization

**`/grd:new-project`**
Initialize new research project through unified flow.

One command takes you from research idea to ready-for-investigation:

- Deep questioning to understand the physics problem
- Optional literature survey (spawns 4 parallel scout agents)
- Research objectives definition with scoping
- Roadmap creation with phase breakdown and success criteria

Creates all `.grd/` artifacts:

- `PROJECT.md` — research question, theoretical framework, key parameters
- `config.json` — workflow settings (`autonomy`, `research_mode`, agent toggles)
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
- Produces a complete, self-contained derivation document with boxed final result

Usage: `/grd:derive-equation`

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

Usage: `/grd:progress`
Usage: `/grd:progress --full` (detailed view with all phase artifacts)
Usage: `/grd:progress --brief` (compact one-line status)
Usage: `/grd:progress --reconcile` (fix diverged STATE.md and state.json)

**`/grd:suggest-next`**
Suggest the most impactful next action based on current project state.

- Scans phases, plans, verification status, blockers, and todos
- Produces a prioritized action list
- Fastest way to answer "what should I do next?" without reading through progress reports

Usage: `/grd:suggest-next`

### Session Management

**`/grd:resume-work`**
Resume research from previous session with full context restoration.

- Reads STATE.md for project context
- Shows current position and recent progress
- Offers next actions based on project state

Usage: `/grd:resume-work`

**`/grd:pause-work`**
Create context handoff when pausing work mid-phase.

- Creates .continue-here file with current state
- Updates STATE.md session continuity section
- Captures in-progress work context

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

Usage: `/grd:dimensional-analysis`

**`/grd:limiting-cases`**
Verify results reduce correctly in known limiting cases.

- Tests classical, non-relativistic, weak-coupling, thermodynamic limits
- Compares against textbook expressions in each limit
- Flags limits that are not recovered

Usage: `/grd:limiting-cases`

**`/grd:numerical-convergence`**
Run systematic convergence tests on numerical computations.

- Tests convergence with grid refinement, time step, basis size
- Estimates convergence order via Richardson extrapolation
- Constructs error budgets for computed quantities

Usage: `/grd:numerical-convergence`

**`/grd:compare-experiment`**
Compare theoretical/numerical results against experimental data.

- Loads published experimental values and error bars
- Computes chi-squared or other goodness-of-fit measures
- Identifies systematic deviations and their possible origins

Usage: `/grd:compare-experiment`

**`/grd:validate-conventions [phase]`**
Validate convention consistency across all phases.

- Checks metric signature, Fourier convention, natural units, gauge choice
- Detects convention drift where a symbol is redefined in a later phase
- Cross-checks locked conventions against all phase artifacts
- Scope to a single phase or run across all phases

Usage: `/grd:validate-conventions`
Usage: `/grd:validate-conventions 3`

**`/grd:regression-check [phase]`**
Re-verify all previously verified claims and checks to catch regressions after changes.

- Extracts verified results from VERIFICATION.md files
- Re-runs dimensional analysis, limiting cases, and numerical checks
- Reports any results that no longer hold
- Scope to a single phase or run across all phases

Usage: `/grd:regression-check`
Usage: `/grd:regression-check 3`

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
Usage: `/grd:sensitivity-analysis --method numerical`

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
- Produces stage artifacts under `.grd/review/` plus `.grd/REFEREE-REPORT.md` and `.grd/REFEREE-REPORT.tex` (or revision-round follow-up pairs)
- Routes the result to `/grd:respond-to-referees` or `/grd:arxiv-submission`
- Requires an initialized `.grd/PROJECT.md` workspace; manuscript paths do not bypass project preflight

Usage: `/grd:peer-review`
Usage: `/grd:peer-review paper/`

**`/grd:respond-to-referees`**
Structure point-by-point response to referee reports and revise the manuscript.

- Parses referee comments into structured items with severity levels
- Creates `.grd/AUTHOR-RESPONSE.md` for structured issue tracking plus `.grd/paper/REFEREE_RESPONSE.md` for the journal-facing response letter
- Consumes `.grd/review/REVIEW-LEDGER*.json` and `.grd/review/REFEREE-DECISION*.json` when present to preserve blocking-issue context
- Spawns paper-writer agents for targeted section revisions
- Tracks new calculations required by referees as revision tasks
- Produces response letter from `templates/paper/referee-response.md`
- Bounded revision loop (max 3 iterations with re-review)

Usage: `/grd:respond-to-referees`

**`/grd:arxiv-submission`**
Prepare a completed paper for arXiv submission with validation and packaging.

- LaTeX validation and compilation check
- Bibliography flattening (inline .bbl or resolve .bib)
- Figure format and resolution checking
- `\input` resolution into single .tex file (optional)
- Metadata verification (title, authors, abstract)
- Ancillary file packaging
- Generates submission-ready `.tar.gz`
- Produces checklist of remaining manual steps

Usage: `/grd:arxiv-submission`

**`/grd:literature-review [topic]`**
Structured literature review for a physics research topic.

- Citation network analysis and open question identification
- Spawns grd-literature-reviewer agent
- Creates structured review with key papers, methods, and gaps
- Spawns grd-bibliographer to verify citations

Usage: `/grd:literature-review "Sachdev-Ye-Kitaev model thermodynamics"`

### Hypothesis Branches

**`/grd:branch-hypothesis <description>`**
Create a hypothesis branch for parallel investigation of an alternative approach.

- Creates git branch with isolated `.grd/` state
- Allows exploring alternative methods without disrupting main line
- Use when two valid approaches exist and you want to compare

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
Configure workflow toggles, model profile, and runtime-specific tier model overrides interactively.

- Toggle plan researcher, plan checker, and execution verifier agents
- Configure inter-wave verification gates (auto/always/never)
- Toggle parallel execution of wave plans
- Select model profile (deep-theory/numerical/exploratory/review/paper-writing)
- Optionally pin concrete runtime model strings for `tier-1`, `tier-2`, and `tier-3`
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

**`/grd:health`**
Run comprehensive project health checks, including storage-path policy auditing.

- Validates state.json, STATE.md sync, convention locks, config.json, orphaned phases, ROADMAP.md consistency, missing plans, stale artifacts, and git status
- Use `--fix` to auto-repair detected issues

Usage: `/grd:health`
Usage: `/grd:health --fix`

**`/grd:help`**
Show this command reference.

## Files & Structure

```
.grd/
|-- PROJECT.md            # Research question, framework, parameters
|-- REQUIREMENTS.md       # Scoped research requirements with REQ-IDs
|-- ROADMAP.md            # Current phase breakdown
|-- STATE.md              # Project memory & context
|-- MILESTONES.md         # Milestone history
|-- config.json           # Workflow mode & gates
|-- research/             # Literature survey results
|   |-- PRIOR-WORK.md     # Established results in the field
|   |-- METHODS.md        # Standard methods and tools
|   |-- COMPUTATIONAL.md  # Computational approaches and tools
|   |-- PITFALLS.md       # Known pitfalls and open problems
|   +-- SUMMARY.md        # Synthesized survey
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

Set during `/grd:new-project`:

**Interactive Mode**

- Confirms each major decision
- Pauses at checkpoints for approval
- More guidance throughout

**YOLO Mode**

- Auto-approves most decisions
- Executes plans without confirmation
- Only stops for critical checkpoints (e.g., sign convention choices)

Change anytime by editing `.grd/config.json`

## Planning Configuration

Configure how planning artifacts are managed in `.grd/config.json`:

**`planning.commit_docs`** (default: `true`)

- `true`: Planning artifacts committed to git (standard workflow)
- `false`: Planning artifacts kept local-only, not committed

When `commit_docs: false`:

- Add `.grd/` to your `.gitignore`
- Useful for collaborative projects, shared repos, or keeping planning private
- All planning files still work normally, just not tracked in git

Example config:

```json
{
  "planning": {
    "commit_docs": false
  }
}
```

## Common Workflows

**Starting a new research project:**

```
/grd:new-project        # Unified flow: questioning -> survey -> objectives -> roadmap
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

**Resuming work after a break:**

```
/grd:progress  # See where you left off and continue
```

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
  </process>
