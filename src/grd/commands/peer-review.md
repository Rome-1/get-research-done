---
name: grd:peer-review
description: Conduct a staged six-pass peer review of a manuscript and supporting research artifacts in the current GRD project
argument-hint: "[paper directory or manuscript path]"
context_mode: project-required
requires:
  files: ["paper/*.tex", "manuscript/*.tex", "draft/*.tex"]
review-contract:
  review_mode: publication
  schema_version: 1
  required_outputs:
    - ".grd/review/CLAIMS.json"
    - ".grd/review/STAGE-reader.json"
    - ".grd/review/STAGE-literature.json"
    - ".grd/review/STAGE-math.json"
    - ".grd/review/STAGE-physics.json"
    - ".grd/review/STAGE-interestingness.json"
    - ".grd/review/REVIEW-LEDGER.json"
    - ".grd/review/REFEREE-DECISION.json"
    - ".grd/REFEREE-REPORT.md"
    - ".grd/REFEREE-REPORT.tex"
    - ".grd/CONSISTENCY-REPORT.md"
  required_evidence:
    - "existing manuscript"
    - "phase summaries or milestone digest"
    - "verification reports"
    - "bibliography audit"
    - "artifact manifest"
    - "reproducibility manifest"
    - "stage review artifacts"
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
    - "project_state"
    - "roadmap"
    - "conventions"
    - "research_artifacts"
    - "manuscript"
  stage_ids:
    - "reader"
    - "literature"
    - "math"
    - "physics"
    - "interestingness"
    - "meta"
  stage_artifacts:
    - ".grd/review/CLAIMS.json"
    - ".grd/review/STAGE-reader.json"
    - ".grd/review/STAGE-literature.json"
    - ".grd/review/STAGE-math.json"
    - ".grd/review/STAGE-physics.json"
    - ".grd/review/STAGE-interestingness.json"
    - ".grd/review/REVIEW-LEDGER.json"
    - ".grd/review/REFEREE-DECISION.json"
  final_decision_output: ".grd/review/REFEREE-DECISION.json"
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

<!-- Tool names and @ includes are platform-specific. The installer translates paths for your runtime. -->
<!-- Allowed-tools are runtime-specific. Other platforms may use different tool interfaces. -->

<objective>
Conduct a skeptical peer review of a completed manuscript and its supporting research artifacts within the current GRD project.

This command promotes manuscript review to a first-class workflow instead of hiding it inside `write-paper`. It now runs a staged six-agent panel instead of a single all-purpose referee pass: full-manuscript reader, literature reviewer, mathematical-soundness reviewer, physical-soundness reviewer, significance reviewer, and final adjudicating referee.

**Orchestrator role:** Locate the manuscript, validate review prerequisites, gather supporting artifacts, spawn the staged review panel with fresh context between stages, and present actionable outcomes based on the final recommendation.

Peer review is not the same as verification. Verification asks whether a derivation or computation checks out. Peer review asks whether the claimed contribution is correct, complete, clear, well-situated in the literature, reproducible, and publishable.
</objective>

<execution_context>
@{GRD_INSTALL_DIR}/workflows/peer-review.md
</execution_context>

<context>
Review target: $ARGUMENTS (optional paper directory or manuscript path)

@.grd/STATE.md
@.grd/ROADMAP.md

Check for candidate manuscripts:

```bash
ls paper/main.tex manuscript/main.tex draft/main.tex 2>/dev/null
find . -maxdepth 3 \( -name "main.tex" -o -name "*.tex" \) 2>/dev/null | head -20
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

The workflow handles all logic including:

1. **Init** — Load project context, detect manuscript target, and resolve scope
2. **Preflight** — Run review preflight validation for the peer-review command
3. **Artifact discovery** — Load manuscript files, bibliography, verification reports, and review-grade paper artifacts
4. **Stage 1** — Spawn `grd-review-reader` to read the whole manuscript and write `.grd/review/CLAIMS.json` plus the Stage 1 handoff artifact
5. **Stages 2-5** — Run four fresh-context specialist reviewers with compact stage artifacts: `grd-review-literature`, `grd-review-math`, `grd-review-physics`, and `grd-review-significance`
6. **Final adjudication** — Spawn `grd-referee` as the meta-reviewer to synthesize stage artifacts, populate `.grd/review/REVIEW-LEDGER.json`, validate the decision floor, and issue the canonical final recommendation
7. **Report handling** — Read the generated referee report and classify the recommendation
8. **Next-step routing** — Route to respond-to-referees, manuscript edits, or arxiv-submission depending on the outcome
</process>

<success_criteria>
- [ ] Manuscript target located or explicitly resolved from arguments
- [ ] Review preflight passed or blocking issues were surfaced clearly
- [ ] Claim index and specialist stage artifacts written under `.grd/review/`
- [ ] `.grd/review/REVIEW-LEDGER.json` and `.grd/review/REFEREE-DECISION.json` created
- [ ] Final adjudicating grd-referee spawned with the stage artifacts and manuscript
- [ ] `.grd/REFEREE-REPORT.md` or `.grd/REFEREE-REPORT-R{N}.md` created with matching `.tex` companion
- [ ] `.grd/CONSISTENCY-REPORT.md` created when supported by the referee workflow
- [ ] Recommendation, issue counts, and actionable next steps presented
- [ ] Revision rounds respected if prior author responses already exist
</success_criteria>
