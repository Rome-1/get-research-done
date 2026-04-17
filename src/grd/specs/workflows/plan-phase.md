<purpose>
Create executable phase prompts (PLAN.md files) for a research phase with integrated literature review and verification. Default flow: Research (if needed) -> Plan -> Verify -> Done. Orchestrates grd-phase-researcher, grd-planner, and grd-plan-checker agents with a revision loop (max 3 iterations).
</purpose>

<required_reading>
Read all files referenced by the invoking prompt's execution_context before starting.

Read these files using the file_read tool:
- {GRD_INSTALL_DIR}/references/ui/ui-brand.md
- {GRD_INSTALL_DIR}/templates/planner-subagent-prompt.md -- Template for spawning grd-planner agents (placeholders, continuation format, failure protocol)
- {GRD_INSTALL_DIR}/templates/phase-prompt.md -- PLAN.md output format (frontmatter, task XML, contract-native wiring)
</required_reading>

<process>

## 1. Initialize

Bootstrap with only the phase metadata and contract gate:

```bash
INIT=$(grd init plan-phase "$PHASE" --include state,roadmap,requirements,context,research,verification,validation)
if [ $? -ne 0 ]; then
  echo "ERROR: grd initialization failed: $INIT"
  exit 1
fi
```

Parse JSON for: `researcher_model`, `planner_model`, `checker_model`, `research_enabled`, `plan_checker_enabled`, `commit_docs`, `autonomy`, `research_mode`, `phase_found`, `phase_dir`, `phase_number`, `phase_name`, `phase_slug`, `padded_phase`, `has_research`, `has_context`, `has_plans`, `plan_count`, `planning_exists`, `roadmap_exists`, `project_contract`, `project_contract_gate`, `project_contract_validation`, `project_contract_load_info`, `platform`.

**Mode-aware behavior:**
- `autonomy=supervised`: Present the written draft plans for user review before treating them as approved or moving on to execution. Do not weaken the contract gate just because the draft is human-reviewed.
- `autonomy=balanced` (default): Write the plan and pause only if the plan-checker raises issues or the planning choices need user judgment.
- `autonomy=yolo`: Write the plan and proceed without pausing.
- `research_mode=explore`: Always run research step even if research exists. Expand research and comparison coverage, but do not auto-create git-backed branches or branch-like plans just because alternatives appear.
- `research_mode=exploit`: Reuse existing research only when it already covers the exact method family, anchors, and decisive evidence path for this phase. Otherwise run targeted research. suppress optional tangents entirely unless the user explicitly requests them. Do not volunteer `grd:branch-hypothesis` as the default response in exploit mode.
- `research_mode=balanced` (default): Use the standard research depth for the phase and keep the default contract-checking and comparison coverage unless the phase needs broader or narrower review.
- `research_mode=adaptive`: Start broad until prior decisive evidence or an explicit approach lock justifies narrowing. Do not infer “safe to narrow” from phase number alone.
- Tangent policy: when multiple viable approaches or optional side questions appear, do NOT silently branch or widen the plan. Use the canonical tangent decision model below instead of assuming extra plans or branches. `git.branching_strategy` does not override this rule.
- All modes still require contract completeness, decisive outputs, required anchors, forbidden-proxy handling, and disconfirming paths before execution starts.

**Bind the current INIT snapshot into shell variables, then re-run this binding after every staged reload before routing on any later step:**

```bash
bind_plan_phase_init() {
  local init="$1"

  researcher_model=$(echo "$init" | grd json get .researcher_model --default "")
  planner_model=$(echo "$init" | grd json get .planner_model --default "")
  checker_model=$(echo "$init" | grd json get .checker_model --default "")
  research_enabled=$(echo "$init" | grd json get .research_enabled --default false)
  plan_checker_enabled=$(echo "$init" | grd json get .plan_checker_enabled --default false)
  commit_docs=$(echo "$init" | grd json get .commit_docs --default false)
  autonomy=$(echo "$init" | grd json get .autonomy --default balanced)
  research_mode=$(echo "$init" | grd json get .research_mode --default balanced)
  phase_found=$(echo "$init" | grd json get .phase_found --default false)
  phase_dir=$(echo "$init" | grd json get .phase_dir --default "")
  phase_number=$(echo "$init" | grd json get .phase_number --default "")
  phase_name=$(echo "$init" | grd json get .phase_name --default "")
  phase_slug=$(echo "$init" | grd json get .phase_slug --default "")
  padded_phase=$(echo "$init" | grd json get .padded_phase --default "")
  has_research=$(echo "$init" | grd json get .has_research --default false)
  has_context=$(echo "$init" | grd json get .has_context --default false)
  has_plans=$(echo "$init" | grd json get .has_plans --default false)
  plan_count=$(echo "$init" | grd json get .plan_count --default 0)
  planning_exists=$(echo "$init" | grd json get .planning_exists --default false)
  roadmap_exists=$(echo "$init" | grd json get .roadmap_exists --default false)
  project_contract=$(echo "$init" | grd json get .project_contract --default "")
  project_contract_gate=$(echo "$init" | grd json get .project_contract_gate --default "")
  project_contract_load_info=$(echo "$init" | grd json get .project_contract_load_info --default "")
  project_contract_validation=$(echo "$init" | grd json get .project_contract_validation --default "")
  contract_intake=$(echo "$init" | grd json get .contract_intake --default "")
  effective_reference_intake=$(echo "$init" | grd json get .effective_reference_intake --default "")
  selected_protocol_bundle_ids=$(echo "$init" | grd json get .selected_protocol_bundle_ids --default "")
  protocol_bundle_count=$(echo "$init" | grd json get .protocol_bundle_count --default 0)
  protocol_bundle_context=$(echo "$init" | grd json get .protocol_bundle_context --default "")
  protocol_bundle_verifier_extensions=$(echo "$init" | grd json get .protocol_bundle_verifier_extensions --default "")
  active_reference_context=$(echo "$init" | grd json get .active_reference_context --default "")
  reference_artifact_files=$(echo "$init" | grd json get .reference_artifact_files --default "")
  reference_artifacts_content=$(echo "$init" | grd json get .reference_artifacts_content --default "")
  literature_review_files=$(echo "$init" | grd json get .literature_review_files --default "")
  literature_review_count=$(echo "$init" | grd json get .literature_review_count --default 0)
  research_map_reference_files=$(echo "$init" | grd json get .research_map_reference_files --default "")
  research_map_reference_count=$(echo "$init" | grd json get .research_map_reference_count --default 0)
  derived_manuscript_proof_review_status=$(echo "$init" | grd json get .derived_manuscript_proof_review_status --default "")
  state_content=$(echo "$init" | grd json get .state_content --default "")
  roadmap_content=$(echo "$init" | grd json get .roadmap_content --default "")
  requirements_content=$(echo "$init" | grd json get .requirements_content --default "")
  context_content=$(echo "$init" | grd json get .context_content --default "")
  research_content=$(echo "$init" | grd json get .research_content --default "")
  experiment_design_content=$(echo "$init" | grd json get .experiment_design_content --default "")
  verification_content=$(echo "$init" | grd json get .verification_content --default "")
  validation_content=$(echo "$init" | grd json get .validation_content --default "")

  RESEARCHER_MODEL="$researcher_model"
  PLANNER_MODEL="$planner_model"
  CHECKER_MODEL="$checker_model"
  RESEARCH_ENABLED="$research_enabled"
  PLAN_CHECKER_ENABLED="$plan_checker_enabled"
  COMMIT_DOCS="$commit_docs"
  AUTONOMY="$autonomy"
  RESEARCH_MODE="$research_mode"
  PHASE_FOUND="$phase_found"
  PHASE_DIR="$phase_dir"
  PHASE_NUMBER="$phase_number"
  PHASE_NAME="$phase_name"
  PHASE_SLUG="$phase_slug"
  PADDED_PHASE="$padded_phase"
  HAS_RESEARCH="$has_research"
  HAS_CONTEXT="$has_context"
  HAS_PLANS="$has_plans"
  PLAN_COUNT="$plan_count"
  PLANNING_EXISTS="$planning_exists"
  ROADMAP_EXISTS="$roadmap_exists"
  PROJECT_CONTRACT="$project_contract"
  PROJECT_CONTRACT_GATE="$project_contract_gate"
  PROJECT_CONTRACT_LOAD_INFO="$project_contract_load_info"
  PROJECT_CONTRACT_VALIDATION="$project_contract_validation"
  CONTRACT_INTAKE="$contract_intake"
  EFFECTIVE_REFERENCE_INTAKE="$effective_reference_intake"
  SELECTED_PROTOCOL_BUNDLE_IDS="$selected_protocol_bundle_ids"
  PROTOCOL_BUNDLE_COUNT="$protocol_bundle_count"
  PROTOCOL_BUNDLE_CONTEXT="$protocol_bundle_context"
  PROTOCOL_BUNDLE_VERIFIER_EXTENSIONS="$protocol_bundle_verifier_extensions"
  ACTIVE_REFERENCE_CONTEXT="$active_reference_context"
  REFERENCE_ARTIFACT_FILES="$reference_artifact_files"
  REFERENCE_ARTIFACTS_CONTENT="$reference_artifacts_content"
  LITERATURE_REVIEW_FILES="$literature_review_files"
  LITERATURE_REVIEW_COUNT="$literature_review_count"
  RESEARCH_MAP_REFERENCE_FILES="$research_map_reference_files"
  RESEARCH_MAP_REFERENCE_COUNT="$research_map_reference_count"
  DERIVED_MANUSCRIPT_PROOF_REVIEW_STATUS="$derived_manuscript_proof_review_status"
  STATE_CONTENT="$state_content"
  ROADMAP_CONTENT="$roadmap_content"
  REQUIREMENTS_CONTENT="$requirements_content"
  CONTEXT_CONTENT="$context_content"
  RESEARCH_CONTENT="$research_content"
  EXPERIMENT_DESIGN_CONTENT="$experiment_design_content"
  VERIFICATION_CONTENT="$verification_content"
  VALIDATION_CONTENT="$validation_content"
}

REQUESTED_PHASE="${PHASE}"
PHASE=$(echo "$INIT" | grd json get .phase_number --default "${REQUESTED_PHASE}")
PHASE_DIR=$(echo "$INIT" | grd json get .phase_dir --default "")
AUTONOMY=$(echo "$INIT" | grd json get .autonomy --default balanced)
RESEARCH_MODE=$(echo "$INIT" | grd json get .research_mode --default balanced)
```

**If `planning_exists` is false:** Error -- run `/grd:new-project` first.

**If `project_contract_load_info.status` starts with `blocked`:** STOP and checkpoint with the user. Show the specific `project_contract_load_info.errors` / `warnings`; do not silently continue from `ROADMAP.md` or `REQUIREMENTS.md` alone when the stored contract could not even be loaded cleanly.

**If `project_contract` is empty or null:** STOP and checkpoint with the user. Planning requires an approved scoping contract in `.grd/state.json`; do not infer phase scope from `ROADMAP.md` or `REQUIREMENTS.md` alone.

**Treat `project_contract` as authoritative only when `project_contract_gate.authoritative` is true.** If the gate is false, keep the contract visible as context and diagnostics, not as approved planning scope.

**If `project_contract_validation.valid` is false:** STOP and checkpoint with the user. Quote the `project_contract_validation.errors` explicitly and repair the contract before planning; a visible-but-blocked contract is not an approved planning contract.

## 1.5 Proof-Obligation Planning Gate

The planner template owns the detailed theorem and proof-redteam policy. The workflow only needs to keep proof-bearing work fail-closed: `--skip-verify` does NOT waive checker review, checker-disabled config does not waive proof review, and any proof-bearing plan set still needs checker review or an equivalent main-context audit before planning is considered complete. Proof-bearing work includes theorem-style claims, `claim`, lemma, corollary, proposition, proof, prove, existence, and uniqueness tasks.

## 2. Parse and Normalize Arguments

Extract from $ARGUMENTS: phase number (integer or decimal like `2.1`), flags (`--research`, `--skip-research`, `--gaps`, `--skip-verify`, `--light`, `--inline-discuss`).

### `--inline-discuss` Flag (Combined Discuss + Plan)

When `--inline-discuss` is present, combine discuss-phase and plan-phase into a single session. This eliminates the 3-session friction (discuss → plan → execute) for straightforward phases.

**Before step 5 (Handle Research), insert a quick gray-area probe:**

1. Read the phase goal and description from ROADMAP.md
2. Present 2-3 critical decision points to the researcher — focus on the gray areas most likely to affect planning:
   - "What formalism/method do you envision for this phase?" (if multiple valid approaches exist)
   - "Are there any constraints or conventions from prior phases that should carry through?" (if phase has dependencies)
   - "What precision level is acceptable?" (for numerical/computational phases)
3. If those questions reveal multiple viable approaches or optional side questions, use the canonical tangent decision model below instead of assuming extra plans or branches.
4. Record any explicit tangent decision in the lightweight CONTEXT.md so downstream agents see whether the user chose to stay on the main line, branch, quick-check, or defer.
5. Record responses as a lightweight CONTEXT.md in the phase directory (same format as discuss-phase output, but with only the critical decisions — skip the full Socratic dialogue)
6. Proceed to step 5 with the context populated

This is NOT the full discuss-phase flow — just the 2-3 most impactful questions. If the phase is complex enough to need full discussion, the researcher should run `/grd:discuss-phase` separately.

**If no phase number:** Detect next unplanned phase from roadmap.

**If `phase_found` is false:** Validate phase exists in ROADMAP.md. If valid, resolve directory metadata from the roadmap before continuing:

```bash
PHASE_INFO=$(grd roadmap get-phase "${PHASE}")
if [ "$(echo "$PHASE_INFO" | grd json get .found --default false)" != "true" ]; then
  echo "Error: Phase ${PHASE} not found in ROADMAP.md."
  exit 1
fi

PHASE_NAME=$(echo "$PHASE_INFO" | grd json get .phase_name --default "")
PHASE_SLUG=$(grd slug "$PHASE_NAME")
PADDED_PHASE=$(printf '%s' "${PHASE}" | python3 -c "import sys; parts=sys.stdin.read().strip().split('.'); head=str(int(parts[0])).zfill(2); tail=[str(int(part)) for part in parts[1:] if part]; print('.'.join([head, *tail]))")
PHASE="${PADDED_PHASE}"
PHASE_DIR=".grd/phases/${PADDED_PHASE}-${PHASE_SLUG}"
mkdir -p "${PHASE_DIR}"
```

Use these resolved values for all later references to `PHASE_DIR`, `PHASE_SLUG`, and `PADDED_PHASE`.

**Existing artifacts from init:** `has_research`, `has_plans`, `plan_count`.

## 3. Validate Phase

```bash
PHASE_INFO=$(grd roadmap get-phase "${PHASE}")
```

**If `found` is false:** Error with available phases. **If `found` is true:** Extract `phase_number`, `phase_name`, `goal` from JSON.

## 4. Load CONTEXT.md and Hypothesis Context

Use `context_content` from init JSON (already loaded via `--include context`).

**CRITICAL:** Use `context_content` from INIT -- pass to researcher, planner, checker, and revision agents.

If `context_content` is not null, display: `Using phase context from: ${PHASE_DIR}/*-CONTEXT.md`

### Hypothesis-Aware Planning

Check if STATE.md contains an active hypothesis:

```bash
HYPOTHESIS_INFO=$(grd --raw state active-hypothesis)
if [ "$(echo "$HYPOTHESIS_INFO" | grd json get .found --default false)" = "true" ]; then
  HYPOTHESIS_SLUG=$(echo "$HYPOTHESIS_INFO" | grd json get .branch_slug --default "")
  HYPOTHESIS_FILE="GRD/hypotheses/${HYPOTHESIS_SLUG}/HYPOTHESIS.md"
  HYPOTHESIS_CONTENT=$(cat "$HYPOTHESIS_FILE" 2>/dev/null)
fi
```

**If an active hypothesis exists:**

1. Extract the hypothesis branch slug from the helper output
2. Read the HYPOTHESIS.md file:

```bash
HYPOTHESIS_SLUG=$(echo "$HYPOTHESIS_SECTION" | grep "Branch:" | sed 's/.*hypothesis\///')
HYPOTHESIS_FILE=".grd/hypotheses/${HYPOTHESIS_SLUG}/HYPOTHESIS.md"
HYPOTHESIS_CONTENT=$(cat "$HYPOTHESIS_FILE" 2>/dev/null)
```

3. Display: `Active hypothesis detected: hypothesis/${HYPOTHESIS_SLUG}`
4. The hypothesis description, motivation, expected outcome, and success criteria become a **primary constraint** for all downstream agents (researcher, planner, checker). Inject the hypothesis context into every agent prompt:

```markdown
<hypothesis_constraint>
This phase is being planned on a HYPOTHESIS BRANCH. The plan must serve
the hypothesis investigation, not the default approach.

{HYPOTHESIS_CONTENT}

**Planning constraint:** Every plan task must either:
- Directly test or advance the hypothesis, OR
- Provide infrastructure required by hypothesis-specific tasks

Do NOT plan tasks that follow the parent branch approach. The parent branch
already explores that path.
</hypothesis_constraint>
```

5. Append this `<hypothesis_constraint>` block to the prompts for: grd-phase-researcher (step 5), grd-planner (step 8), grd-plan-checker (step 10), and revision agents (step 12).

## 4.5. Convention Verification

**Verify conventions before planning** — plans that depend on conventions from prior phases must use the correct ones:

```bash
CONV_CHECK=$(grd --raw convention check 2>/dev/null)
if [ $? -ne 0 ]; then
  echo "WARNING: Convention verification failed — resolve before planning"
  echo "$CONV_CHECK"
fi
```

If the check fails, warn the user before spawning the researcher or planner. Convention mismatches in the plan will propagate into every task during execution.

## 4.6. Tangent Control During Planning

Required 4-way tangent decision model:

- Branch as alternative hypothesis -> route through `grd:tangent` or `grd:branch-hypothesis`
- Run a bounded side investigation now -> route through `grd:quick`
- Capture and defer -> route through `grd:add-todo`
- Stay on the main line -> create plans only for the selected primary approach

The planner template owns the detailed tangent decision model. The workflow only needs to surface an explicit checkpoint when the planner reports multiple viable approaches; do NOT silently branch, widen scope, or create detached side plans here.

## 4.7 Refresh Research Handoff Context

Load the staged handoff slice needed to assemble the researcher prompt. Do not use the lighter routing slice here:

```bash
INIT=$(grd --raw init plan-phase "$PHASE" --stage planner_authoring)
# Legacy routing slice: grd --raw init plan-phase "$PHASE" --stage research_routing
if [ $? -ne 0 ]; then
  echo "ERROR: staged plan-phase init failed: $INIT"
  exit 1
fi
bind_plan_phase_init "$INIT"
```

## 5. Handle Research

**Skip if:** `--gaps` flag, `--skip-research` flag, or `research_enabled` is false (from init) without `--research` override.

**Read research mode from init JSON:**

```bash
RESEARCH_MODE=$(echo "$INIT" | grd json get .research_mode --default balanced)
```

### Research Mode Decision Matrix

| Mode | RESEARCH.md exists | RESEARCH.md missing | `--research` flag |
|------|-------------------|--------------------|--------------------|
| **explore** | Re-research always (expand scope, compare alternatives, refresh anchors) | Research (comprehensive — multiple methods, broad survey) | Research (comprehensive) |
| **balanced** (default) | Skip by default, but re-research if inputs look stale or missing for the current contract slice | Research (standard) | Research (standard) |
| **exploit** | Skip only if the existing research already covers the exact method family, anchor set, and decisive evidence path; otherwise run targeted method research | Research (minimal — method-specific only, no broad survey, no optional tangent surfacing unless explicitly requested) | Research (minimal) |
| **adaptive** | Reuse existing research only after prior decisive evidence or explicit approach-lock markers show the method is stable; otherwise refresh research in a balanced or explore-style pass while surfacing unresolved alternatives as tangent candidates rather than silent branches | Research (broad enough to choose and lock an approach) | Research (standard) |

**If `has_research` is true (from init) AND no `--research` flag:**

Route by research mode:

```bash
if [ "$RESEARCH_MODE" = "explore" ]; then
  # Explore: always re-research for broader coverage
  echo "Research mode: explore — re-researching for comprehensive coverage"
  # Proceed to spawn researcher below
elif [ "$RESEARCH_MODE" = "exploit" ]; then
  # Exploit: reuse only if existing research already covers the exact method family
  # and contract-critical anchor/comparison path for this phase
  if echo "$INIT" | grd json get .research_content --default "" | grep -qi "method\\|benchmark\\|anchor"; then
    echo "Research mode: exploit — existing targeted research appears sufficient"
    # Skip to step 6
  else
    echo "Research mode: exploit — no RESEARCH.md found, refreshing targeted method context"
    # Proceed to spawn researcher below
  fi
elif [ "$RESEARCH_MODE" = "adaptive" ]; then
  # Adaptive: narrow only after prior decisive evidence or an explicit approach lock
  VALIDATED=$(ls .grd/phases/*/*SUMMARY.md 2>/dev/null | xargs grep -El "approach_validated: true|comparison_verdicts:|contract_results:" 2>/dev/null | head -1)
  if [ -n "$VALIDATED" ]; then
    echo "Research mode: adaptive — prior decisive evidence found, using existing research as the starting point"
    # Skip to step 6
  else
    echo "Research mode: adaptive — approach not yet locked, refreshing research before planning"
    # Proceed to spawn researcher below
  fi
else
  # Balanced (default): check staleness before skipping
  RESEARCH_MOD=$(stat -f %m "${PHASE_DIR}"/*-RESEARCH.md 2>/dev/null || stat -c %Y "${PHASE_DIR}"/*-RESEARCH.md 2>/dev/null || echo 0)
  STATE_MOD=$(stat -f %m .grd/STATE.md 2>/dev/null || stat -c %Y .grd/STATE.md 2>/dev/null || echo 0)
  DIFF_DAYS=$(( (STATE_MOD - RESEARCH_MOD) / 86400 ))

  if [ "$DIFF_DAYS" -gt 1 ]; then
    echo "Research may be stale (created ${RESEARCH_MOD}, state updated ${STATE_MOD}). Re-research with --research?"
    # If user chooses to re-research, proceed to spawn researcher below. Otherwise, use existing and skip to step 6.
  fi
fi
```

**If RESEARCH.md missing OR `--research` flag OR explore mode with existing research:**

Display banner:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 GRD > RESEARCHING PHASE {X}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

* Spawning researcher...
```

### Spawn grd-phase-researcher
> **Runtime delegation:** Spawn a subagent for the task below. Adapt the `task()` call to your runtime's agent spawning mechanism. If `model` resolves to `null` or an empty string, omit it so the runtime uses its default model. Always pass `readonly=false` for file-producing agents. If subagent spawning is unavailable, execute these steps sequentially in the main context.

```bash
PHASE_DESC=$(grd roadmap get-phase "${PHASE}" | grd json get .section --default "")
# Use requirements_content from INIT (already loaded via --include requirements)
REQUIREMENTS=$(echo "$INIT" | grd json get .requirements_content --default "" | grep -A100 "## Requirements" | head -50)
STATE_SNAP=$(grd state snapshot)
# Extract decisions from grd state snapshot JSON: echo "$STATE_SNAP" | grd json list .decisions
```

Research prompt:

```markdown
<objective>
Research Phase {phase_number}: {phase_name} well enough to plan it rigorously.
</objective>

<phase_context>
IMPORTANT: If CONTEXT.md exists below, it contains user decisions from /grd:discuss-phase.

- **Decisions** = Locked -- research THESE deeply, no alternatives
- **Agent's Discretion** = Freedom areas -- research options, recommend
- **Deferred Ideas** = Out of scope -- ignore

{context_content}
</phase_context>

<additional_context>
Phase description: {phase_description}
Requirements: {requirements}
Prior decisions: {decisions}
Project contract: {project_contract}
Active references: {active_reference_context}
Reference artifacts: {reference_artifacts_content}
</additional_context>

<research_mode>{RESEARCH_MODE}</research_mode>

<hypothesis_constraint>
If this phase belongs to a hypothesis branch, include the hypothesis constraint block below verbatim. Otherwise omit this section.
{hypothesis_constraint}
</hypothesis_constraint>

<output>
Write to: {phase_dir}/{phase_number}-RESEARCH.md
</output>

<spawn_contract>
write_scope:
  mode: scoped_write
  allowed_paths:
    - {phase_dir}/{phase_number}-RESEARCH.md
expected_artifacts:
  - {phase_dir}/{phase_number}-RESEARCH.md
shared_state_policy: return_only
</spawn_contract>
```

```
RESEARCH_RETURN=$(
task(
  prompt="First, read {GRD_AGENTS_DIR}/grd-phase-researcher.md for your role and instructions.\n\n" + research_prompt,
  subagent_type="grd-phase-researcher",
  model="{researcher_model}",
  readonly=false,
  description="Research Phase {phase_number}"
)
)
```

**If the researcher agent fails to spawn or returns an error:** Report the failure. Offer: 1) Retry with the same context, 2) Execute the research in the main context (slower but reliable), 3) Skip research and proceed directly to planning (planner will work with less context). Do not silently continue without research output.

### Handle Researcher Return

Human-readable headings such as `## RESEARCH COMPLETE` and `## RESEARCH BLOCKED` are presentation only. Route on `grd_return.status` and the artifact gate below.

- **`grd_return.status: completed`:** Verify the returned files and the on-disk artifact before accepting completion, then display confirmation and continue to step 6.
- **`grd_return.status: checkpoint`:** Present the checkpoint, collect the response, and spawn a fresh continuation handoff. Do not wait inside the child run.
- **`grd_return.status: blocked` or `failed`:** Display blocker, offer: 1) Provide context, 2) Skip research, 3) Abort

**Verify RESEARCH.md was written (guard against silent researcher failure):**

```bash
EXPECTED_RESEARCH_FILE="${PHASE_DIR}/${PHASE_NUMBER}-RESEARCH.md"
RESEARCH_FILES=$(echo "$RESEARCH_RETURN" | grd json list .grd_return.files_written --default "")
if ! printf '%s\n' "$RESEARCH_FILES" | grep -Fxq "$EXPECTED_RESEARCH_FILE"; then
  echo "ERROR: researcher returned completed without naming ${EXPECTED_RESEARCH_FILE}"
  exit 1
fi
if [ ! -r "$EXPECTED_RESEARCH_FILE" ]; then
  echo "ERROR: researcher returned completed but ${EXPECTED_RESEARCH_FILE} is missing or unreadable"
  exit 1
fi
```

## 5.1 Handle Researcher Checkpoint

If the researcher returns `grd_return.status: checkpoint`, present the checkpoint to the user and spawn a fresh continuation handoff:

```markdown
<objective>
Continue research as a fresh continuation handoff for Phase {phase_number}: {phase_name}
</objective>

<prior_state>
Research file path: {phase_dir}/{phase_number}-RESEARCH.md
Read that file before continuing so you inherit the prior research state instead of relying on inline prompt state.
</prior_state>

<checkpoint_response>
**Type:** {checkpoint_type}
**Response:** {user_response}
</checkpoint_response>

<hypothesis_constraint>
If this phase belongs to a hypothesis branch, include the hypothesis constraint block below verbatim. Otherwise omit this section.
{hypothesis_constraint}
</hypothesis_constraint>

<spawn_contract>
write_scope:
  mode: scoped_write
  allowed_paths:
    - {phase_dir}/{phase_number}-RESEARCH.md
expected_artifacts:
  - {phase_dir}/{phase_number}-RESEARCH.md
shared_state_policy: return_only
</spawn_contract>
```

```bash
RESEARCH_RETURN=$(
task(
  prompt="First, read {GRD_AGENTS_DIR}/grd-phase-researcher.md for your role and instructions.\n\n" + continuation_prompt,
  subagent_type="grd-phase-researcher",
  model="{researcher_model}",
  readonly=false,
  description="Continue research Phase {phase_number}"
)
)
```

After the continuation returns, rerun the same `grd_return.files_written` and on-disk artifact gate above before advancing.

## 5.5. Experiment Design (Numerical/Computational Phases)

**Skip if:** `--light` flag, `--skip-research` flag, or the phase description does not involve numerical computation.

**Research mode effects on experiment design:**

| Mode | Experiment Designer | Rationale |
|------|-------------------|-----------|
| **explore** | Always spawn (even if numerical indicators are weak) | Broad exploration benefits from structured experiment design |
| **balanced** | Spawn if numerical indicators detected (default behavior) | Standard heuristic |
| **exploit** | Skip unless EXPERIMENT-DESIGN.md is explicitly required by CONTEXT.md | Exploit mode minimizes overhead |
| **adaptive** | Follow balanced behavior until prior decisive evidence or an explicit approach lock stabilizes the method family; then reuse validated experiment templates for the locked approach | Evidence-driven reuse once the method is stable |

**Detection:** Check the phase goal and research content for numerical indicators:

```bash
PHASE_GOAL=$(echo "$INIT" | grd json get .phase_name --default "")

# Re-read RESEARCH.md from disk — `research_content` from INIT (step 1) is **stale**
# because the researcher in step 5 may have just created/updated it.
RESEARCH_FILE=$(ls "${PHASE_DIR}"/*-RESEARCH.md 2>/dev/null | head -1)
if [ -n "$RESEARCH_FILE" ]; then
  RESEARCH_CONTENT=$(cat "$RESEARCH_FILE")
fi
```

Scan `PHASE_GOAL` and `RESEARCH_CONTENT` for indicators of computational work: "Monte Carlo", "simulation", "numerical", "finite-size", "convergence", "parameter sweep", "benchmark", "grid", "discretization", "timestep", "sampling".

**If numerical indicators found AND no existing EXPERIMENT-DESIGN.md:**

Display banner:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 GRD > DESIGNING NUMERICAL EXPERIMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

* Spawning experiment designer...
```

### Spawn grd-experiment-designer

```bash
EXPERIMENT_MODEL=$(grd resolve-model grd-experiment-designer)
```

Experiment design prompt:

```markdown
<objective>
Design the numerical experiment protocol for Phase {phase_number}: {phase_name}
</objective>

<phase_context>
**Phase description:** {phase_description}
**Research:** {research_content}
**Conventions:** $(grd --raw convention list 2>/dev/null)
**Context:** {context_content}
</phase_context>

<output>
Write to: {phase_dir}/{phase}-EXPERIMENT-DESIGN.md
</output>
```

```
task(
  prompt="First, read {GRD_AGENTS_DIR}/grd-experiment-designer.md for your role and instructions.\n\n" + experiment_prompt,
  subagent_type="grd-experiment-designer",
  model="{experiment_model}",
  readonly=false,
  description="Design experiment for Phase {phase}"
)
```

### Handle Experiment Designer Return

**If the experiment designer agent fails to spawn or returns an error:** Experiment design is optional supplementary context for the planner. Proceed without it — the planner will work with RESEARCH.md and CONTEXT.md. Note that experiment design was skipped.

- **`EXPERIMENT DESIGN COMPLETE`:** Verify EXPERIMENT-DESIGN.md exists, display confirmation, continue to step 6
- **`DESIGN BLOCKED`:** Display blocker, offer: 1) Provide context, 2) Skip experiment design, 3) Abort

**If EXPERIMENT-DESIGN.md created:** The planner stage payload already carries this as `experiment_design_content`. Keep it in the stage-local payload rather than re-reading it from disk.

```markdown
**Experiment Design:** {experiment_design_content}
```

**If no numerical indicators OR `--light` mode:** Skip silently.

## 6. Check Existing Plans

```bash
ls "${PHASE_DIR}"/*-PLAN.md 2>/dev/null
```

**If exists:** Offer: 1) Add more plans, 2) View existing, 3) Replan from scratch.

## 7. Use Context Files from INIT

Refresh the stage-local planning payload now that research routing is complete and immediately rebind the live shell variables:

```bash
# Extract from INIT JSON
STATE_CONTENT=$(echo "$INIT" | grd json get .state_content --default "")
ROADMAP_CONTENT=$(echo "$INIT" | grd json get .roadmap_content --default "")
REQUIREMENTS_CONTENT=$(echo "$INIT" | grd json get .requirements_content --default "")
VERIFICATION_CONTENT=$(echo "$INIT" | grd json get .verification_content --default "")
UAT_CONTENT=$(echo "$INIT" | grd json get .validation_content --default "")
CONTEXT_CONTENT=$(echo "$INIT" | grd json get .context_content --default "")
PROJECT_CONTRACT=$(echo "$INIT" | grd json get .project_contract --default "")
PROTOCOL_BUNDLE_CONTEXT=$(echo "$INIT" | grd json get .protocol_bundle_context --default "")
ACTIVE_REFERENCE_CONTEXT=$(echo "$INIT" | grd json get .active_reference_context --default "")
REFERENCE_ARTIFACTS_CONTENT=$(echo "$INIT" | grd json get .reference_artifacts_content --default "")
```

**CRITICAL: Re-read RESEARCH.md from disk if the researcher was spawned in step 5.**

The `research_content` from INIT (step 1) is **stale** — it was loaded before the researcher wrote RESEARCH.md.
If you pass the stale INIT value to the planner, the planner will plan WITHOUT the researcher's output.
**ALWAYS** read the fresh file from disk after step 5 completes:

```bash
# Re-read RESEARCH.md from disk (researcher may have just created/updated it)
RESEARCH_FILE=$(ls "${PHASE_DIR}"/*-RESEARCH.md 2>/dev/null | head -1)
if [ -n "$RESEARCH_FILE" ]; then
  RESEARCH_CONTENT=$(cat "$RESEARCH_FILE")
else
  RESEARCH_CONTENT=$(echo "$INIT" | grd json get .research_content --default "")
fi
```

**Load EXPERIMENT-DESIGN.md if it was created in step 5.5:**

```bash
EXPERIMENT_FILE=$(ls "${PHASE_DIR}"/*-EXPERIMENT-DESIGN.md 2>/dev/null | head -1)
if [ -n "$EXPERIMENT_FILE" ]; then
  EXPERIMENT_DESIGN_CONTENT=$(cat "$EXPERIMENT_FILE")
fi
bind_plan_phase_init "$INIT"
```

## 8. Spawn grd-planner Agent

Display banner:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 GRD > PLANNING PHASE {X}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

* Spawning planner...
```

Planner prompt:

Use `templates/planner-subagent-prompt.md` here as the stage-local planner template and render its `## Standard Planning Template` section.

```markdown
Render the template's `## Standard Planning Template` into `filled_prompt` with these bindings:

- `{phase_number}` -> {phase_number}
- `{standard | gap_closure}` -> `standard` unless this is explicit gap-closure planning
- `{full | light}` -> `light` only when `--light`; otherwise `full`
- `{research_mode}` -> {RESEARCH_MODE}
- `{autonomy}` -> {AUTONOMY}
- `{state_content}` -> {state_content}
- `{project_contract}` -> {project_contract}
- `{project_contract_gate}` -> {project_contract_gate}
- `{project_contract_load_info}` -> {project_contract_load_info}
- `{project_contract_validation}` -> {project_contract_validation}
- `{contract_intake}` -> {contract_intake}
- `{effective_reference_intake}` -> {effective_reference_intake}
- `{roadmap_content}` -> {roadmap_content}
- `{requirements_content}` -> {requirements_content}
- `{protocol_bundle_context}` -> {protocol_bundle_context}
- `{active_reference_context}` -> {active_reference_context}
- `{reference_artifacts_content}` -> {reference_artifacts_content}
- `{context_content}` -> {context_content}
- `{research_content}` -> {research_content}
- `{experiment_design_content}` -> {experiment_design_content}
- `{verification_content}` -> {verification_content}
- `{validation_content}` -> {validation_content}
Keep `{contract_intake}` and `{effective_reference_intake}` visible in the rendered prompt.
Stable knowledge docs may appear inside `{active_reference_context}` and `{reference_artifacts_content}`. Treat them as reviewed background syntheses only; they may refine assumptions, caveats, or method choice when consistent with stronger sources, but they do not override `convention_lock`, `project_contract`, the PLAN `contract`, or direct evidence.
If a plan materially depends on a reviewed knowledge doc and that reliance must be gateable downstream, express it with explicit `knowledge_deps`; keep implicit stable background advisory only.

**Project State:** {state_content}
**Project Contract:** {project_contract}
**Contract Intake:** {contract_intake}
**Effective Reference Intake:** {effective_reference_intake}
**Roadmap:** {roadmap_content}
**Requirements:** {requirements_content}
**Protocol Bundles:** {protocol_bundle_context}
**Active References:** {active_reference_context}
**Reference Artifacts:** {reference_artifacts_content}

## Canonical PLAN Contract Schema

Use `templates/plan-contract-schema.md` as the canonical contract schema reference.

**Phase Context:**
IMPORTANT: If context exists below, it contains USER DECISIONS from /grd:discuss-phase.

- **Decisions** = LOCKED -- honor exactly, do not revisit
- **Agent's Discretion** = Freedom -- make methodological choices
- **Deferred Ideas** = Out of scope -- do NOT include

{context_content}

**Research:** {research_content}
**Experiment Design (if exists):** {experiment_design_content}
**Gap Closure (if --gaps):** {verification_content} {validation_content}
</planning_context>

<physics_planning_requirements>
Each plan MUST include:

- **Mathematical rigor checkpoints:** Points where derivations must be verified for dimensional consistency, symmetry preservation, and correct tensor structure
- **Limiting case validation:** Explicit checks that results reduce correctly in all known limits (classical, non-relativistic, weak-coupling, thermodynamic, etc.)
- **Order-of-magnitude estimates:** Before any detailed calculation, estimate the expected scale of the answer
- **Error budget:** For numerical work, specify target precision and identify dominant error sources
- **Consistency checks:** Cross-checks between independent methods or approaches where possible
- **Anchor discipline:** If a benchmark, paper, dataset, or prior artifact is contract-critical, surface it in the plan instead of treating it as optional background
- **Contract completeness:** Every plan must include claims, deliverables, references, acceptance tests, forbidden proxies, and uncertainty markers in frontmatter
- **Protocol bundle coverage:** If protocol bundles are selected, carry their estimator policies, decisive artifact guidance, and verifier extensions into the plan explicitly
</physics_planning_requirements>

<contract_requirements>
Planning requires `project_contract`:

- If `project_contract` is empty, stale, or too underspecified to identify the phase contract slice, return `## CHECKPOINT REACHED` instead of writing a weak or guessed plan.
- Every PLAN.md must include a `contract` frontmatter block with exact IDs for claims, deliverables, references, acceptance tests, and forbidden proxies.
- Every PLAN.md must carry forward required context from the contract: must-read refs, prior outputs, baselines, and user anchors when execution depends on them.
- Every PLAN.md must include uncertainty markers from the contract when they constrain interpretation or verification.
- Every PLAN.md should express result wiring through `contract.links` or explicit task/verification handoffs, not through a second ad hoc success schema.
- Validate each finished plan with `grd validate plan-contract <PLAN.md>` before treating it as approved.
- Autonomy mode and model profile may change cadence or detail, but they do NOT relax contract completeness.
</contract_requirements>

<light_mode_instructions>
**If plan depth is `light`:** Keep the full canonical frontmatter, including `wave`, `depends_on`, `files_modified`, `interactive`, `conventions`, and `contract`.

Simplify only the body: one high-level task block per plan, concise verification, concise success criteria. The light plan is a shorter execution script, not a strategic outline that drops required contract fields.
</light_mode_instructions>

<context_budget_guidance>
Context windows are finite (~200k tokens, ~80% usable). Plans must be sized accordingly:

- **Target per plan:** ~50% context budget (40% for hypothesis-driven plans)
- **Segment large phases** into multiple plans rather than one overloaded plan
- **Flag context-heavy plans** in frontmatter: `context_note: "Heavy - consider splitting if >6 tasks"`
- **Group related tasks** that share intermediate results in the same plan
- **Use waves** for independent work -- each subagent gets a fresh context window

**Signs a plan needs splitting:** >6-8 substantive tasks, multiple independent derivations, tasks requiring different large reference files, mix of symbolic derivation and numerical verification.

See `{GRD_INSTALL_DIR}/references/orchestration/context-budget.md` for detailed budget allocation by workflow type.
</context_budget_guidance>

<downstream_consumer>
Output consumed by /grd:execute-phase. Plans need:

- Frontmatter (wave, depends_on, files_modified, interactive, contract)
- Tasks in XML format
- Verification criteria with mathematical rigor requirements
- contract-complete frontmatter before execution starts
- contract links or explicit task-level dependency wiring for critical handoffs, including limiting-case checks
- protocol-bundle guidance reflected in task structure, verification, and decisive artifact selection when applicable
</downstream_consumer>

<quality_gate>

- [ ] PLAN.md files created in phase directory
- [ ] Each plan has valid frontmatter
- [ ] Each plan has a complete contract block (claims, deliverables, references, acceptance tests, forbidden proxies, uncertainty markers)
- [ ] Each plan passes `grd validate plan-contract <PLAN.md>`
- [ ] Tasks are specific and actionable with clear mathematical deliverables
- [ ] Dependencies correctly identified (including prerequisite derivations)
- [ ] Waves assigned for parallel execution
- [ ] Contract links or explicit task-level dependency wiring cover the decisive handoffs and limiting-case recovery path
- [ ] Required refs, prior outputs, and baselines are surfaced in `<context>` or verification paths
- [ ] Selected protocol bundles are reflected in verification paths or decisive artifact choices where relevant
- [ ] Forbidden proxies are rejected explicitly in `<done>` or `<success_criteria>`
- [ ] Dimensional analysis check specified for each quantitative result
- [ ] Validation checkpoints placed after each major derivation step
</quality_gate>
```

```
task(
  prompt="First, read {GRD_AGENTS_DIR}/grd-planner.md for your role and instructions.\n\n" + filled_prompt,
  subagent_type="grd-planner",
  model="{planner_model}",
  readonly=false,
  description="Plan Phase {phase}"
)
```

> Runtime delegation rule: this is a one-shot handoff. If the planner needs user input, it checkpoints and returns; the wrapper must start a fresh continuation after the user responds.

## 9. Handle Planner Return

**If the planner agent fails to spawn or returns an error:** Do not infer completion from files that already exist on disk. Treat any preexisting `PLAN.md` artifacts as a stale baseline unless this run returns a fresh typed `grd_return` that names them in `grd_return.files_written`. If no fresh planner return is available, keep the handoff incomplete. Offer: 1) Retry planner, 2) Create plans in the main context, 3) Abort.

Human-readable headings such as `## PLANNING COMPLETE`, `## CHECKPOINT REACHED`, and `## PLANNING INCONCLUSIVE` are presentation only. Route on the planner's structured `grd_return.status`, `grd_return.files_written`, and the on-disk artifact check.

- **`grd_return.status: completed`:** Before accepting the success state, verify that at least one readable `*-PLAN.md` artifact exists in `${PHASE_DIR}` and extract the fresh plan artifact list from `grd_return.files_written`; verify that every named file exists, is readable, and ends in `-PLAN.md`. Do not accept the planner return text alone. Use the init snapshot (`has_plans`, `plan_count`) as the stale baseline: a plan file that already existed before this handoff only counts as fresh output if this planner return explicitly names it in `grd_return.files_written`. If the planner says complete but no plan files are present, treat the handoff as incomplete until a fresh continuation names them in `grd_return.files_written`. Display plan count. If `AUTONOMY=supervised`, show the written draft plans and get user confirmation before advancing to checker or next-step output. If `--skip-verify` or `plan_checker_enabled` is false (from init): skip to step 13 only when no proof-bearing plans were written. Proof-bearing plans still require checker review or an equivalent main-context audit before planning is considered complete. Otherwise: step 10.
- **`grd_return.status: checkpoint`:** Present to user, get response, spawn a fresh planner continuation handoff. Do not route planner checkpoints into the checker revision loop.
- **`grd_return.status: blocked` or `failed`:** Show attempts, offer: Add context / Retry / Manual

Before the checker loop, validate only the fresh plan artifacts named by the planner return:

```bash
FRESH_PLAN_FILES=$(echo "$PLANNER_RETURN" | grd json list .grd_return.files_written --default "")
if [ -z "$FRESH_PLAN_FILES" ]; then
  echo "ERROR: planner returned completed without naming fresh PLAN.md artifacts"
  exit 1
fi

for plan_file in $FRESH_PLAN_FILES; do
  [ -f "$plan_file" ] || continue
  grd validate plan-contract "$plan_file" || exit 1
done
```

## 9b. Handle Planner Checkpoint

**Planner checkpoints are a separate one-shot continuation path**

If the planner returns `grd_return.status: checkpoint`, present the checkpoint to the user, collect the response, and spawn a fresh `grd-planner` continuation handoff with the updated context. Keep this path distinct from checker-driven revision.

Before continuing, verify that the planner's expected `PLAN.md` artifacts still exist and are readable. If the planner continuation changes the plans, re-run the explicit plan-contract validation against the refreshed `grd_return.files_written` set before checker review.

Only after the planner returns `completed` should the workflow advance to checker review.

## 10. Spawn grd-plan-checker Agent

Display banner (include iteration count if in revision loop):

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 GRD > VERIFYING PLANS (attempt {iteration_count}/3)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

* Spawning plan checker...
```

Refresh the checker/revision payload before entering the checker loop:

```bash
INIT=$(grd --raw init plan-phase "$PHASE" --stage checker_revision)
if [ $? -ne 0 ]; then
  echo "ERROR: staged plan-phase init failed: $INIT"
  exit 1
fi
bind_plan_phase_init "$INIT"
```

```bash
PLANS_CONTENT=""
for plan_file in $FRESH_PLAN_FILES; do
  PLANS_CONTENT="${PLANS_CONTENT}$(cat "$plan_file" 2>/dev/null)"
done
```

Checker prompt:

```markdown
<verification_context>
**Phase:** {phase_number}
**Phase Goal:** {goal from ROADMAP}

**Plans to verify:** {plans_content}
**Requirements:** {requirements_content}
**Project Contract:** {project_contract}
**Project Contract Gate:** {project_contract_gate}
**Project Contract Load Info:** {project_contract_load_info}
**Project Contract Validation:** {project_contract_validation}
**Contract Intake:** {contract_intake}
**Effective Reference Intake:** {effective_reference_intake}
**Protocol Bundles:** {protocol_bundle_context}
**Active References:** {active_reference_context}
**Reference Artifacts:** {reference_artifacts_content}
Treat stable knowledge docs in `active_reference_context` and `reference_artifacts_content` as reviewed background synthesis. They may influence assumptions or method choice when consistent with stronger sources, but they do not override `convention_lock`, `project_contract`, the PLAN `contract`, or decisive evidence.
Check that any downstream-gateable reliance on a reviewed knowledge doc is written as explicit `knowledge_deps`, not only implied by background context.

**Phase Context:**
IMPORTANT: Plans MUST honor user decisions. Flag as issue if plans contradict.

- **Decisions** = LOCKED -- plans must implement exactly
- **Agent's Discretion** = Freedom areas -- plans can choose approach
- **Deferred Ideas** = Out of scope -- plans must NOT include

{context_content}
</verification_context>

<physics_verification_criteria>
In addition to structural checks, verify:

- [ ] **Dimensional consistency:** All equations are dimensionally correct
- [ ] **Limiting cases specified:** Plans identify which limits must be recovered and where checks occur
- [ ] **Approximation validity:** Each approximation has stated regime of validity and error estimates
- [ ] **Conservation laws:** Plans respect relevant conservation laws (energy, momentum, charge, unitarity, etc.)
- [ ] **Symmetry preservation:** Approximations and numerical methods preserve relevant symmetries
- [ ] **Independent cross-checks:** At least one independent verification method per major result
- [ ] **Order-of-magnitude sanity:** Expected scales are stated before detailed calculations
- [ ] **Anchor coverage:** Required references, baselines, and prior outputs are surfaced where the plan depends on them
- [ ] **Protocol-bundle coverage:** Selected protocol bundles are reflected in task structure, estimator guards, decisive artifacts, or verification paths
- [ ] **Contract completeness:** Each plan includes decisive claims, deliverables, acceptance tests, forbidden proxies, and uncertainty markers
- [ ] **Decisive outputs:** The plan set covers decisive claims and deliverables rather than only infrastructure or proxy work
- [ ] **Acceptance tests:** Every decisive claim or deliverable has at least one executable or reviewable test
- [ ] **Disconfirming path:** Risky plans name the observation or comparison that would force a rethink
- [ ] **Forbidden proxies:** Proxy-only success conditions are rejected explicitly
- [ ] **Proof-obligation audit path:** Proof-bearing plans expose theorem targets, named parameters/hypotheses/quantifiers, and a sibling `{plan_id}-PROOF-REDTEAM.md` review artifact
- [ ] **Anti-bypass language:** Plans do not rely on `--skip-verify`, sparse cadence, or later human inspection to waive proof red-teaming
</physics_verification_criteria>

<expected_output>

- ## VERIFICATION PASSED -- all checks pass
- ## ISSUES FOUND -- structured issue list
- ## PARTIAL APPROVAL -- some plans approved, others need revision (see partial_approval protocol in your agent instructions)
</expected_output>
```

```
task(
  prompt="First, read {GRD_AGENTS_DIR}/grd-plan-checker.md for your role and instructions.\n\n" + checker_prompt,
  subagent_type="grd-plan-checker",
  model="{checker_model}",
  readonly=false,
  description="Verify Phase {phase} plans"
)
```

## 11. Handle Checker Return

**If the plan-checker agent fails to spawn or returns an error:** Proceed without plan verification. Plans are still executable. Note that verification was skipped and recommend the user review the plans manually before executing. If any plan is proof-bearing, do NOT waive this gate: run an equivalent main-context proof-plan audit against the checker criteria above or STOP and report that proof-obligation planning could not be cleared safely.

Human-readable headings such as `## VERIFICATION PASSED`, `## ISSUES FOUND`, and `## PARTIAL APPROVAL` are presentation only. Route on the checker's structured `grd_return.status` and plan lists.

- **`grd_return.status: completed`:** Treat as a full pass only after plan-ID reconciliation succeeds. Before accepting the success state, verify:

  1. `approved_plans` names only readable `*-PLAN.md` artifacts in `FRESH_PLAN_FILES`
  2. `blocked_plans` is empty
  3. every approved plan file still exists and matches the approved plan IDs
  4. the checker's `files_written` value does not claim unrelated artifacts

  If any of those checks fail, reject the success state and send the checker output back through the revision loop as a fail-closed mismatch.

  Display iteration-aware confirmation and proceed to step 13 only after reconciliation passes:

  ```
  Plan passed checker (attempt {iteration_count}/3)
  ```

- **`grd_return.status: checkpoint`:** Some plans passed, others need revision. Split the work:

  1. Record approved plans from the structured `approved_plans` list only.
  2. Record blocked plans from the structured `blocked_plans` list only.
  3. Reject the return if any listed plan ID does not map to a readable `*-PLAN.md` file in `FRESH_PLAN_FILES`.
  4. Display status:

     ```
     Partial approval (attempt {iteration_count}/3): {N_approved} plans approved, {N_blocked} need revision
     ```

  5. Send ONLY the blocked plans from the fresh returned plan set to the revision loop (step 12). Pass the checker's blocker details as `{structured_issues_from_checker}`. Do NOT re-check already-approved plans unless their inputs change during revision, and do not treat preexisting blocked-plan files as revised unless the fresh planner return names them in `grd_return.files_written`.
  6. After revision + re-check cycle, if the re-check returns `grd_return.status: completed` for the revised plans, merge approved sets and proceed to step 13. If it returns `grd_return.status: checkpoint` again, repeat. If `grd_return.status: failed`, enter standard revision loop for remaining plans.
  7. Approved plans from partial approval are final only after the plan-ID reconciliation checks pass.

- **`grd_return.status: blocked`:** The checker found a blocker that prevents accepting the current plan set as-is. If `approved_plans` is empty, treat this as a full rejection and send all plans to the revision loop. If `approved_plans` is non-empty, preserve the approved subset only after plan-ID reconciliation passes, then send the blocked subset to the revision loop with the structured issues.

- **`grd_return.status: failed`:** Display iteration-aware status, show issues, check iteration count, proceed to step 12:

  ```
  Checker found {N} issues (attempt {iteration_count}/3). Revising plan...
  ```

## 12. Revision Loop (Max 3 Iterations)

Maximum iterations: 3. After 3 rejections by the plan-checker:
1. Present the best plan to the user with the checker's remaining objections
2. Ask: "The plan-checker has rejected this plan 3 times. Would you like to: (a) proceed anyway, (b) modify the plan manually, or (c) abandon this phase?"
3. Do NOT loop indefinitely

Track `iteration_count` (starts at 1 after initial plan + check).

**If iteration_count < 3:**

Display: `Checker found issues, revising plan (attempt {N}/3)...`

  ```bash
  # If PARTIAL APPROVAL: only load blocked plans (stored in BLOCKED_PLANS list from step 11)
  # If ISSUES FOUND: load all plans
  if [ -n "$BLOCKED_PLANS" ]; then
    PLANS_CONTENT=""
    for plan_id in $BLOCKED_PLANS; do
      for plan_file in $FRESH_PLAN_FILES; do
        case "$plan_file" in
          *-"$plan_id"-PLAN.md) PLANS_CONTENT="${PLANS_CONTENT}$(cat "$plan_file" 2>/dev/null)" ;;
        esac
      done
    done
  else
    for plan_file in $FRESH_PLAN_FILES; do
      PLANS_CONTENT="${PLANS_CONTENT}$(cat "$plan_file" 2>/dev/null)"
    done
  fi
  ```

Before spawning the revision planner, confirm that every `plan_id` in `BLOCKED_PLANS` maps to exactly one readable `*-PLAN.md` file in `FRESH_PLAN_FILES`. If any blocked ID is missing or ambiguous, stop and report the reconciliation failure rather than inventing a fallback mapping.

Revision prompt:

Use `templates/planner-subagent-prompt.md` here as the stage-local planner template and render its `## Revision Template` section.

```markdown
Render the template's `## Revision Template` into `revision_prompt` with these bindings:

- `{phase_number}` -> {phase_number}
- `{plans_content}` -> {plans_content}
- `{structured_issues_from_checker}` -> {structured_issues_from_checker}
- `{state_content}` -> {state_content}
- `{project_contract}` -> {project_contract}
- `{project_contract_gate}` -> {project_contract_gate}
- `{project_contract_load_info}` -> {project_contract_load_info}
- `{project_contract_validation}` -> {project_contract_validation}
- `{contract_intake}` -> {contract_intake}
- `{effective_reference_intake}` -> {effective_reference_intake}
- `{protocol_bundle_context}` -> {protocol_bundle_context}
- `{active_reference_context}` -> {active_reference_context}
- `{reference_artifacts_content}` -> {reference_artifacts_content}
- `{context_content}` -> {context_content}
If the revised fix plan still needs specialized tooling or other machine-checkable hard requirements, keep them in PLAN frontmatter `tool_requirements`.
Treat `effective_reference_intake` as the structured source of carry-forward anchors; `active_reference_context` is the readable projection, not the source of truth.

Keep the revision prompt scoped to targeted checker fixes. Do not restate template-owned revision policy here.
```

```
task(
  prompt="First, read {GRD_AGENTS_DIR}/grd-planner.md for your role and instructions.\n\n" + revision_prompt,
  subagent_type="grd-planner",
  model="{planner_model}",
  readonly=false,
  description="Revise Phase {phase} plans"
)
```

**If the revision planner agent fails to spawn or returns an error:** Do not proceed to re-check just because revised `PLAN.md` files exist on disk. Treat any such files as incomplete until a fresh typed planner return explicitly names them in `grd_return.files_written`. If no fresh revision return is available, keep the loop fail-closed and offer: 1) Retry revision planner, 2) Apply revisions manually in the main context using checker feedback, 3) Force proceed with current plans despite checker issues.

After planner returns -> spawn checker again (step 10), increment iteration_count. If revising from PARTIAL APPROVAL, only pass the revised plans (not already-approved plans) to the checker.

**If iteration_count >= 3:**

Display: `Max iterations reached. {N} issues remain:` + issue list

Offer: 1) Force proceed, 2) Provide guidance and retry, 3) Abandon

## 13. Present Final Status

Route to `<offer_next>`.

</process>

<offer_next>
Output this markdown directly (not as a code block):

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 GRD > PHASE {X} PLANNED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Phase {X}: {Name}** -- {N} plan(s) in {M} wave(s)

| Wave | Plans  | What it builds |
| ---- | ------ | -------------- |
| 1    | 01, 02 | [objectives]   |
| 2    | 03     | [objective]    |

Research: {Completed | Used existing | Skipped}
Verification: {Passed | Partial (N approved, M revised) | Passed with override | Skipped}

---

## >> Next Up

**Execute Phase {X}** -- run all {N} plans

/grd:execute-phase {X}

<sub>/clear first -> fresh context window</sub>

---

**Also available:**

- cat .grd/phases/{phase-dir}/\*-PLAN.md -- review plans
- /grd:plan-phase {X} --research -- re-research first

---

</offer_next>

<success_criteria>

- [ ] .grd/ directory validated
- [ ] Phase validated against roadmap
- [ ] Phase directory created if needed
- [ ] CONTEXT.md loaded early (step 4) and passed to ALL agents
- [ ] Research completed (unless --skip-research or --gaps or exists)
- [ ] grd-phase-researcher spawned with CONTEXT.md
- [ ] grd-experiment-designer spawned for numerical phases (unless --light or no numerical indicators)
- [ ] Existing plans checked
- [ ] grd-planner spawned with CONTEXT.md + RESEARCH.md
- [ ] Plans created (PLANNING COMPLETE or CHECKPOINT handled)
- [ ] grd-plan-checker spawned with CONTEXT.md
- [ ] Verification passed OR user override OR max iterations with user decision
- [ ] Plans include dimensional consistency checks
- [ ] Plans include limiting case validation
- [ ] Plans include approximation validity bounds
- [ ] User sees status between agent spawns
- [ ] User knows next steps
</success_criteria>
