---
name: grd:peer-review
description: Conduct a staged six-pass peer review of a manuscript and supporting research artifacts in the current GRD project
argument-hint: "[paper directory or manuscript path]"
context_mode: project-required
requires:
  files: ["paper/*.tex", "paper/*.md", "manuscript/*.tex", "manuscript/*.md", "draft/*.tex", "draft/*.md"]
review-contract:
  review_mode: publication
  schema_version: 1
  required_outputs:
    - ".grd/review/CLAIMS{round_suffix}.json"
    - ".grd/review/STAGE-reader{round_suffix}.json"
    - ".grd/review/STAGE-literature{round_suffix}.json"
    - ".grd/review/STAGE-math{round_suffix}.json"
    - ".grd/review/STAGE-physics{round_suffix}.json"
    - ".grd/review/STAGE-interestingness{round_suffix}.json"
    - ".grd/review/REVIEW-LEDGER{round_suffix}.json"
    - ".grd/review/REFEREE-DECISION{round_suffix}.json"
    - ".grd/REFEREE-REPORT{round_suffix}.md"
    - ".grd/REFEREE-REPORT{round_suffix}.tex"
  required_evidence:
    - "existing manuscript"
    - "phase summaries or milestone digest"
    - "verification reports"
    - "manuscript-root bibliography audit"
    - "manuscript-root artifact manifest"
    - "manuscript-root reproducibility manifest"
    - "manuscript-root publication artifacts"
  blocking_conditions:
    - "missing project state"
    - "missing roadmap"
    - "missing conventions"
    - "missing manuscript"
    - "no research artifacts"
    - "degraded review integrity"
    - "unsupported physical significance claims"
    - "collapsed novelty or venue fit"
  preflight_checks:
    - "command_context"
    - "project_state"
    - "roadmap"
    - "conventions"
    - "research_artifacts"
    - "verification_reports"
    - "manuscript"
    - "artifact_manifest"
    - "bibliography_audit"
    - "bibliography_audit_clean"
    - "reproducibility_manifest"
    - "reproducibility_ready"
    - "manuscript_proof_review"
  stage_artifacts:
    - ".grd/review/CLAIMS{round_suffix}.json"
    - ".grd/review/STAGE-reader{round_suffix}.json"
    - ".grd/review/STAGE-literature{round_suffix}.json"
    - ".grd/review/STAGE-math{round_suffix}.json"
    - ".grd/review/STAGE-physics{round_suffix}.json"
    - ".grd/review/STAGE-interestingness{round_suffix}.json"
    - ".grd/review/REVIEW-LEDGER{round_suffix}.json"
    - ".grd/review/REFEREE-DECISION{round_suffix}.json"
  final_decision_output: ".grd/review/REFEREE-DECISION{round_suffix}.json"
  requires_fresh_context_per_stage: true
  max_review_rounds: 3
allowed-tools:
  - file_read
  - file_write
  - shell
  - find_files
  - search_files
  - task
  - ask_user
  - web_search
---


<objective>
Conduct a skeptical peer review of a completed manuscript and its supporting research artifacts within the current GRD project.

Keep the wrapper focused on the manuscript target, review prerequisites, and final routing. When announcing the panel to the user, say what each stage does in one concise sentence: Stage 1 maps the paper's claims; Stages 2-3 check prior work and mathematical soundness in parallel; theorem-bearing claims also trigger the auxiliary grd-check-proof critic; Stage 4 checks whether the physical interpretation is supported; Stage 5 judges significance and venue fit; Stage 6 synthesizes everything into the final recommendation.

**Why subagent:** Staged manuscript review burns context fast. Fresh context keeps the orchestrator lean.
</objective>

<execution_context>
@{GRD_INSTALL_DIR}/workflows/peer-review.md
</execution_context>

<context>
Review target: $ARGUMENTS (optional paper directory or manuscript path)

@.grd/STATE.md
@.grd/ROADMAP.md

The default manuscript family is limited to `paper/`, `manuscript/`, and `draft/`.
Let centralized preflight resolve the active manuscript entrypoint from the explicit argument when provided, otherwise from the manuscript-root `ARTIFACT-MANIFEST.json`, then `PAPER-CONFIG.json`, then the canonical current manuscript entrypoint rules for those roots. Do not use ad hoc wildcard discovery.
If none of those roots exist, pass an explicit manuscript path or paper directory and let centralized preflight reject anything outside the supported target family.

```bash
# Regression guardrail wording retained for test alignment:
# Do not use ad hoc glob discovery.
```

</context>

<process>
**Run centralized context preflight first:**

```bash
CONTEXT=$(grd --raw validate command-context peer-review "$ARGUMENTS")
if [ $? -ne 0 ]; then
  echo "$CONTEXT"
  exit 1
fi
```

**Follow the peer-review workflow** from `@{GRD_INSTALL_DIR}/workflows/peer-review.md`.

The workflow forwards the resolved `$ARGUMENTS` manuscript target into review preflight and keeps manuscript-root-relative support artifacts anchored to that same explicit root instead of falling back to `paper/...`.

When announcing the panel to the user, say what each stage does in one concise sentence, for example:

`Launching the six-stage review panel: Stage 1 maps the paper's claims; Stages 2-3 check prior work and mathematical soundness in parallel; Stage 4 checks whether the physical interpretation is supported; Stage 5 judges significance and venue fit; Stage 6 synthesizes everything into the final recommendation.`

The workflow handles all logic including:

1. **Init** — Load project context, detect manuscript target, and resolve scope
2. **Preflight** — Run review preflight validation for the peer-review command
3. **Artifact discovery** — Load manuscript files, bibliography, verification reports, and review-grade paper artifacts
4. **Stage 1** — Spawn `grd-review-reader` to read the whole manuscript and write `.grd/review/CLAIMS{round_suffix}.json` plus the Stage 1 handoff artifact
5. **Stages 2-5** — Run four fresh-context specialist reviewers with compact stage artifacts: `grd-review-literature`, `grd-review-math`, `grd-review-physics`, and `grd-review-significance`
6. **Final adjudication** — Spawn `grd-referee` as the meta-reviewer to synthesize stage artifacts, populate `.grd/review/REVIEW-LEDGER{round_suffix}.json` and `.grd/review/REFEREE-DECISION{round_suffix}.json`, validate the decision floor, and issue the canonical final recommendation
7. **Report handling** — Read the generated referee report and classify the recommendation
8. **Next-step routing** — Route to respond-to-referees, manuscript edits, or arxiv-submission depending on the outcome
</process>

<success_criteria>
- [ ] Manuscript target located or explicitly resolved from arguments
- [ ] Review preflight passed or blocking issues were surfaced clearly
- [ ] Claim index and specialist stage artifacts written under `.grd/review/`
- [ ] `.grd/review/REVIEW-LEDGER{round_suffix}.json` and `.grd/review/REFEREE-DECISION{round_suffix}.json` created
- [ ] Final adjudicating grd-referee spawned with the stage artifacts and manuscript
- [ ] `.grd/REFEREE-REPORT{round_suffix}.md` created with matching `.tex` companion
- [ ] `.grd/CONSISTENCY-REPORT.md` created when supported by the referee workflow
- [ ] Recommendation, issue counts, and actionable next steps presented
- [ ] Revision rounds respected if prior author responses already exist
</success_criteria>
