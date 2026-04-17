---
name: grd:respond-to-referees
description: Structure a point-by-point response to referee reports and update the manuscript
argument-hint: "[path to referee report or 'paste']"
context_mode: project-required
requires:
  files: ["paper/*.tex", "paper/*.md", "manuscript/*.tex", "manuscript/*.md", "draft/*.tex", "draft/*.md"]
review-contract:
  review_mode: publication
  schema_version: 1
  required_outputs:
    - ".grd/paper/REFEREE_RESPONSE{round_suffix}.md"
    - ".grd/AUTHOR-RESPONSE{round_suffix}.md"
  required_evidence:
    - existing manuscript
    - referee report source when provided as a path
  blocking_conditions:
    - missing project state
    - missing manuscript
    - missing referee report source when provided as a path
    - missing conventions
    - degraded review integrity
  preflight_checks:
    - command_context
    - project_state
    - manuscript
    - referee_report_source
    - conventions
allowed-tools:
  - file_read
  - file_write
  - file_edit
  - shell
  - search_files
  - find_files
  - task
  - ask_user
---
<objective>
Structure a point-by-point response to referee reports and revise the manuscript accordingly.

Keep the wrapper focused on referee triage, revision routing, and synchronized response artifacts while the workflow owns the full revision pipeline.

**Why subagent:** Referee triage and synchronized manuscript revision burn context fast. Fresh context keeps the orchestrator lean.
</objective>

<execution_context>
@{GRD_INSTALL_DIR}/workflows/respond-to-referees.md
</execution_context>

<context>
Referee report source: $ARGUMENTS (file path or "paste" for inline input)

@.grd/STATE.md
@.grd/AUTHOR-RESPONSE{round_suffix}.md
@.grd/paper/REFEREE_RESPONSE{round_suffix}.md
@.grd/review/REVIEW-LEDGER{round_suffix}.json
@.grd/review/REFEREE-DECISION{round_suffix}.json

Check for existing paper and prior response files:

```bash
ls paper/main.tex manuscript/main.tex draft/main.tex 2>/dev/null
ls .grd/AUTHOR-RESPONSE*.md 2>/dev/null
ls .grd/paper/REFEREE_RESPONSE*.md 2>/dev/null
ls .grd/review/REVIEW-LEDGER*.json .grd/review/REFEREE-DECISION*.json 2>/dev/null
```

The workflow resolves the manuscript root, staged review artifacts, and revision targets.
</context>

<process>
Execute the respond-to-referees workflow from @{GRD_INSTALL_DIR}/workflows/respond-to-referees.md end-to-end.
If staged peer-review artifacts exist under `.grd/review/`, absorb them as structured decision context while keeping `.grd/REFEREE-REPORT{round_suffix}.md` as the canonical issue-ID source.
Preserve all validation gates (report parsing, triage confirmation, compilation check, consistency verification, bounded revision loop).
</process>

<success_criteria>
- [ ] Referee reports parsed and all comments categorized and prioritized
- [ ] `.grd/review/REVIEW-LEDGER*.json` and `.grd/review/REFEREE-DECISION*.json` consumed when available
- [ ] `.grd/AUTHOR-RESPONSE{round_suffix}.md` and `.grd/paper/REFEREE_RESPONSE{round_suffix}.md` created with complete point-by-point structure
- [ ] Comments triaged into response-only, revision, and new calculation groups
- [ ] All responses drafted and revisions applied via paper-writer agents
- [ ] Revised manuscript compiles without errors
- [ ] Internal consistency verified after revisions (max 3 iterations)
- [ ] Response letter generated with change summary
- [ ] All artifacts committed
</success_criteria>
