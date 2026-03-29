<purpose>
Provide a beginner-friendly first-run entry point for GPD. Inspect the current
folder, explain what GPD can do here in plain language, and route into the real
existing workflows without inventing a parallel onboarding state machine.
</purpose>

<required_reading>
Read all files referenced by the invoking prompt's execution_context before
starting.
</required_reading>

<process>

<step name="detect_workspace_state">
Determine what kind of folder the researcher is in before offering commands.

```bash
HAS_GPD_PROJECT=false
if [ -f GPD/PROJECT.md ] || [ -f GPD/STATE.md ] || [ -f GPD/ROADMAP.md ]; then
  HAS_GPD_PROJECT=true
fi

HAS_RESEARCH_MAP=false
if [ -d GPD/research-map ]; then
  HAS_RESEARCH_MAP=true
fi

RESEARCH_FILES=$(rg --files \
  -g '!GPD/**' \
  -g '!.git/**' \
  -g '!.venv/**' \
  -g '!node_modules/**' \
  -g '!dist/**' \
  -g '!build/**' \
  -g '*.tex' \
  -g '*.bib' \
  -g '*.pdf' \
  -g '*.ipynb' \
  -g '*.py' \
  -g '*.jl' \
  -g '*.m' \
  -g '*.wl' \
  -g '*.nb' \
  -g '*.csv' \
  -g '*.tsv' \
  . 2>/dev/null | head -n 12)

RESEARCH_FILE_COUNT=$(printf "%s\n" "$RESEARCH_FILES" | sed '/^$/d' | wc -l | tr -d ' ')
```

Interpret the folder state like this:

- If `HAS_GPD_PROJECT=true`: this is an existing GPD project in the current folder.
- Else if `HAS_RESEARCH_MAP=true`: this folder has been mapped by GPD, but a full project may not exist yet.
- Else if `RESEARCH_FILE_COUNT > 0`: this looks like an existing research folder with prior work.
- Else: treat this as a fresh or mostly empty folder.

If `$ARGUMENTS` is non-empty, treat it as a short statement of what the
researcher is trying to do and show it back as context, but still use the
folder-state routing rules above.
</step>

<step name="explain_current_state">
Present one short, plain-language summary before asking the researcher to pick a
path.

Use one of these summaries:

- Existing GPD project:
  `This folder already has a GPD project. The safest next step is usually to resume it instead of starting over.`
- Research map only:
  `This folder already has a GPD research map. You can turn it into a full GPD project or refresh the map.`
- Existing research folder:
  `This folder looks like it already contains research files. The safest next step is usually to map the folder before creating a new GPD project.`
- Fresh folder:
  `This folder does not look like an existing GPD project or research folder yet, so you can start a new project here.`

If `RESEARCH_FILES` is non-empty, show up to 5 sample files so the researcher
can see what GPD noticed.
</step>

<step name="offer_relevant_choices">
Offer only the options that make sense for the detected state.

> **Platform note:** If `ask_user` is not available, present these choices in
> plain text and wait for the user's freeform response.

**If this is an existing GPD project:**

- `Resume this project` — continue from the selected project state through `/gpd:resume-work`
- `Suggest the next best action` — get the shortest high-signal recommendation through `/gpd:suggest-next`
- `Review project status first` — inspect broader state through `/gpd:progress`
- `Do a small bounded task` — use `/gpd:quick`
- `Explain a concept` — use `/gpd:explain`
- `Show full command reference` — use `/gpd:help --all`

**If this folder has a research map but not a full project yet:**

- `Turn this mapped folder into a GPD project` — use `/gpd:new-project`
- `Refresh the research map` — use `/gpd:map-research`
- `Take a guided tour first` — use `/gpd:tour`
- `Show full command reference` — use `/gpd:help --all`

**If this looks like an existing research folder without GPD state:**

- `Map this folder first (recommended)` — use `/gpd:map-research`
- `Start a brand-new GPD project anyway` — use `/gpd:new-project --minimal`
- `Take a guided tour first` — use `/gpd:tour`
- `Explain a concept` — use `/gpd:explain`
- `Show full command reference` — use `/gpd:help --all`
- `Reopen a different GPD project` — use `gpd resume --recent` in your normal terminal

**If this is a fresh folder:**

- `Fast start` — use `/gpd:new-project --minimal`
- `Full guided setup` — use `/gpd:new-project`
- `Take a guided tour first` — use `/gpd:tour`
- `Explain a concept` — use `/gpd:explain`
- `Show full command reference` — use `/gpd:help --all`
- `Reopen a different GPD project` — use `gpd resume --recent` in your normal terminal

Ask the researcher to choose exactly one path.
</step>

<step name="route_choice">
Route immediately into the real existing workflow for the chosen path.

**If the researcher chooses `Resume this project`:**

- Read `{GPD_INSTALL_DIR}/workflows/resume-work.md` with the file-read tool.
- Follow that workflow as if the researcher had run `/gpd:resume-work`.

**If the researcher chooses `Review project status first`:**

- Read `{GPD_INSTALL_DIR}/workflows/progress.md` with the file-read tool.
- Follow that workflow as if the researcher had run `/gpd:progress`.

**If the researcher chooses `Suggest the next best action`:**

- `suggest-next` is a workflow-exempt command, not a shared workflow include.
- Follow the installed `/gpd:suggest-next` command contract directly, as if the researcher had run it.

**If the researcher chooses `Map this folder first` or `Refresh the research map`:**

- Read `{GPD_INSTALL_DIR}/workflows/map-research.md` with the file-read tool.
- Follow that workflow as if the researcher had run `/gpd:map-research`.

**If the researcher chooses `Fast start`:**

- Follow the installed `/gpd:new-project --minimal` command contract directly, as if the researcher had run it.

**If the researcher chooses `Full guided setup` or `Turn this mapped folder into a GPD project`:**

- Follow the installed `/gpd:new-project` command contract directly, as if the researcher had run it.

**If the researcher chooses `Take a guided tour first`:**

- Follow the installed `/gpd:tour` command contract directly, as if the researcher had run it.

**If the researcher chooses `Do a small bounded task`:**

- Read `{GPD_INSTALL_DIR}/workflows/quick.md` with the file-read tool.
- Follow that workflow as if the researcher had run `/gpd:quick`.

**If the researcher chooses `Explain a concept`:**

- If `$ARGUMENTS` contains a usable concept or question, reuse it.
- Otherwise ask for one short concept or question before continuing.
- Read `{GPD_INSTALL_DIR}/workflows/explain.md` with the file-read tool.
- Follow that workflow as if the researcher had run `/gpd:explain <topic>`.

**If the researcher chooses `Show full command reference`:**

- Follow the installed `/gpd:help --all` command contract directly, as if the researcher had run it.

**If the researcher chooses `Reopen a different GPD project`:**

- Do not try to switch projects silently from inside the runtime.
- Explain exactly:
  - `Use \`gpd resume --recent\` in your normal terminal to find the project first.`
  - `Then open that project folder in the runtime and run \`/gpd:resume-work\`.`
- STOP after giving those instructions.
</step>

<step name="guardrails">
Keep the routing strict:

- `start` is the chooser, not a second implementation of `new-project`, `resume-work`, `map-research`, `quick`, `explain`, or `help`.
- Do not silently create project files from `/gpd:start` itself.
- Do not silently switch the user into a different project folder.
- When in doubt between a fresh folder and an existing-research folder, prefer `map-research` as the safer recommendation.
</step>

</process>

<success_criteria>
- [ ] The current folder is classified as existing GPD project, mapped folder, existing research folder, or fresh folder
- [ ] The researcher sees only the choices that make sense for that state
- [ ] The chosen path routes into the real existing workflow instead of duplicating it
- [ ] Cross-project recovery stays explicit through `gpd resume --recent` from the normal terminal
- [ ] `/gpd:start` remains a beginner-friendly chooser, not a parallel onboarding state machine
</success_criteria>
