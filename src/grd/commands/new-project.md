---
name: grd:new-project
description: Initialize a new physics research project with deep context gathering and PROJECT.md
argument-hint: "[--auto] [--minimal [@file.md]]"
context_mode: projectless
allowed-tools:
  - file_read
  - shell
  - file_write
  - task
  - ask_user
---

<context>
**Flags:**
- `--auto` — Automatic mode. Synthesizes a scoping contract from the supplied document, asks for one explicit scope approval, then runs research → requirements → roadmap with minimal follow-up interaction. Expects a research proposal document via @ reference.
- `--minimal` — Fast bootstrapping mode. Uses one structured intake plus one scoping approval gate, then creates all `.grd/` artifacts with lean content. Scope, anchors, and decisive outputs are still required.
- `--minimal @file.md` — Create project directly from a markdown file describing your research and phases. Parses research question, phases, and key parameters from the file.
</context>

<objective>
Initialize a new physics research project through one flow: questioning or structured intake → scoping contract approval → literature survey (optional) → requirements → staged roadmap/conventions handoff.

If no project config exists yet, start with physics questioning, surface a preset choice before workflow preferences, and ask detailed config questions only after scope approval and before the first project-artifact commit.

**Creates:**

- `.grd/PROJECT.md` — research project context
- `.grd/config.json` — workflow preferences
- `.grd/research/` — domain and literature research (optional)
- `.grd/REQUIREMENTS.md` — scoped research requirements
- `.grd/ROADMAP.md` — phase structure
- `.grd/STATE.md` — project memory
- `.grd/state.json` `project_contract` — authoritative machine-readable scoping contract

**After this command:** Run `/grd:discuss-phase 1` to clarify the first phase before planning.
</objective>

<execution_context>
@{GRD_INSTALL_DIR}/workflows/new-project.md
@{GRD_INSTALL_DIR}/references/research/questioning.md
@{GRD_INSTALL_DIR}/references/ui/ui-brand.md
@{GRD_INSTALL_DIR}/templates/project.md
@{GRD_INSTALL_DIR}/templates/requirements.md
@{GRD_INSTALL_DIR}/templates/state-json-schema.md
</execution_context>

<process>
**CRITICAL: First, read the full workflow file using the file_read tool:**
Read the file at {GRD_INSTALL_DIR}/workflows/new-project.md — this contains the complete step-by-step instructions (1693 lines) for initializing a research project. Do NOT improvise. Follow the workflow file exactly.

Also read these reference files:
- {GRD_INSTALL_DIR}/references/research/questioning.md (questioning protocol)
- {GRD_INSTALL_DIR}/templates/project.md (PROJECT.md template)
- {GRD_INSTALL_DIR}/templates/requirements.md (REQUIREMENTS.md template)
- {GRD_INSTALL_DIR}/templates/state-json-schema.md (project contract object shape and ID linkage rules)

Before synthesizing or revising the raw `project_contract`, use the `project_contract` section of `state-json-schema.md` as the schema source of truth. Do not invent ad-hoc fields, replace object arrays with strings, or create unresolved ID references.

Execute the workflow end-to-end. Preserve all workflow gates (validation, approvals, routing).

## Flag Detection

Check `$ARGUMENTS` for flags:

- **`--auto`** → Structured synthesis + scope approval
- **`--minimal`** → Fast staged-init with scope approval
- **`--minimal @file.md`** → Minimal mode with input file

**If `--minimal` detected:** After Setup, route to the **minimal staged initialization path**. It keeps intake to one response, still requires a scoping contract with decisive outputs and anchors, and then hands roadmap and conventions creation to the staged post-scope agents instead of building them directly in the main context.

**If `--auto` detected:** After Setup, synthesize context from the provided document, repair blocking gaps only, present the scoping contract for approval, then run research → requirements → roadmap with smart defaults.
</process>

<output>

- `.grd/PROJECT.md`
- `.grd/config.json`
- `.grd/research/` (if research selected)
  - `PRIOR-WORK.md`
  - `METHODS.md`
  - `COMPUTATIONAL.md`
  - `PITFALLS.md`
  - `SUMMARY.md`
- `.grd/REQUIREMENTS.md`
- `.grd/ROADMAP.md`
- `.grd/STATE.md`
- `.grd/CONVENTIONS.md` (established by grd-notation-coordinator)

</output>

<success_criteria>

**Full mode success criteria:**
- [ ] .grd/ directory created and git repo initialized
- [ ] Deep questioning completed (research context fully captured)
- [ ] Scoping contract captures decisive outputs, anchors, weakest assumptions, and unresolved gaps
- [ ] Scoping contract explicitly approved before requirements or roadmap generation
- [ ] PROJECT.md created with full context -- committed
- [ ] config.json created with workflow settings -- committed
- [ ] Literature survey completed (if selected) -- committed
- [ ] REQUIREMENTS.md created with REQ-IDs -- committed
- [ ] ROADMAP.md created with phases and requirement mappings -- committed
- [ ] STATE.md initialized
- [ ] CONVENTIONS.md created via grd-notation-coordinator -- committed
- [ ] Convention lock populated via grd convention set
- [ ] User informed next step is /grd:discuss-phase 1

**Minimal mode success criteria (if `--minimal`):**

- [ ] .grd/ directory created
- [ ] Git repo initialized
- [ ] Structured intake captured core question, decisive outputs, anchors, and known gaps
- [ ] Scoping contract approved before requirements or roadmap generation
- [ ] `PROJECT.md` created from one description or input file and committed
- [ ] `ROADMAP.md` created from the input and committed
- [ ] `REQUIREMENTS.md` created with auto-generated REQ-IDs and committed
- [ ] `STATE.md` initialized and committed
- [ ] `config.json` created with defaults and committed
- [ ] All files committed in one commit: `docs: initialize research project (minimal)`
- [ ] Same directory structure and file set as full path
- [ ] User offered "Discuss phase 1 now?"

</success_criteria>
