<purpose>
Give a first-run chooser for people who may not know GRD yet. Explain the folder state in plain English, offer only the choices that fit that state, and route into the existing workflows instead of creating a separate onboarding flow.
</purpose>

<required_reading>
Read all files referenced by the invoking prompt's execution_context before starting.
</required_reading>

<process>

<step name="detect_workspace_state">
Figure out what kind of folder this is before offering any commands.

```bash
HAS_GPD_PROJECT=false
if [ -f GRD/PROJECT.md ] || [ -f GRD/STATE.md ] || [ -f GRD/ROADMAP.md ]; then
  HAS_GPD_PROJECT=true
fi

HAS_RESEARCH_MAP=false
if [ -d GRD/research-map ]; then
  HAS_RESEARCH_MAP=true
fi

RESEARCH_FILES=$(rg --files \
  -g '!GRD/**' \
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

Use these meanings:

- `HAS_GPD_PROJECT=true` means this folder already has a `GRD project` (a folder where GRD already saved its own project files, notes, and state), such as `GRD/PROJECT.md`.
- `HAS_RESEARCH_MAP=true` means this folder already has a `research map` (GRD's summary of an existing research folder before full project setup).
- `RESEARCH_FILE_COUNT > 0` means this looks like an existing research folder. Example files might be `.tex`, `.py`, `.ipynb`, `.pdf`, or `.csv`.
- Otherwise, treat this as a fresh folder with no obvious GRD state yet.

If `$ARGUMENTS` is non-empty, briefly repeat it back as the researcher’s goal, but keep the folder-state routing rules above.
</step>

<step name="explain_current_state">
Give one short summary before asking for a choice.

Use one of these plain-English summaries:

- Existing GRD project:
  `This folder already has a GRD project (GRD's saved project files and working state), so the safest next step is usually to resume it instead of starting over.`
- Research map only:
  `This folder already has a GRD research map (GRD's summary of the folder before full setup), so you can refresh that map or turn it into a full project.`
- Existing research folder:
  `This folder already looks like real research work, so the safest next step is usually to map it before creating a new project. In GRD terms, \`map-research\` means inspect an existing folder before planning.`
- Fresh folder:
  `This folder does not look like an existing GRD project or research folder yet, so you can start from scratch here. In GRD terms, \`new-project\` creates the project scaffolding GRD will use later.`

If `RESEARCH_FILES` is non-empty, show up to 5 sample files so the researcher can see what GRD noticed.

If advanced terms appear in the summary, explain them once in parentheses and then keep using the official term consistently.
</step>

<step name="offer_relevant_choices">
Offer only the choices that fit the detected state.

If `ask_user` is available, present the choices as normal selectable options.

If `ask_user` is not available, show the same choices as numbered options and wait for the user to reply with a number or short phrase. Say explicitly: `Reply with the number or the option name.`

Before listing choices, add one short line in plain English such as:

- `I will show the safest next steps first and the broader options second.`
- `The official GRD command names are included so you can learn them as you go.`
- `Keep the numbered list short. Put extra capabilities in a separate \`Other useful options\` block instead of making the user compare too many first choices.`

**This folder already has saved GRD work (`GRD project`)**

Recommended next steps:

1. Resume this project (recommended) - use `grd:resume-work`. This is the in-runtime continue command for an existing GRD project. Example: `I already worked on this GRD project and want to keep going.`
2. Review the project status first - use `grd:progress`. Example: `I want a broader snapshot before I continue.`
3. Take a guided tour first - use `grd:tour`. Example: `I want a read-only overview before I continue.`

Other useful options, only if one of these is what you need:

- Suggest the next best step - use `grd:suggest-next`. Example: `I resumed the project and only want the next action.`
- Do one small bounded task - use `grd:quick`. Example: `I only want one contained job, not a full session.`
- Explain one concept - use `grd:explain`. Example: `Explain a method or equation before I continue.`
- Show all commands - use `grd:help --all`.

**This folder already has GRD's folder summary (`research map`)**

Recommended next steps:

1. Turn this into a full GRD project (recommended) - use `grd:new-project`. A research map is GRD's summary of an existing folder before full setup. Example: `The folder was already mapped and now I want the full project.`
2. Refresh the research map - use `grd:map-research`. Example: `The folder changed and I want GRD to inspect it again.`
3. Take a guided tour first - use `grd:tour`. Example: `I want the commands explained before I choose.`

Other useful options, only if one of these is what you need:

- Explain one concept - use `grd:explain`.
- Show all commands - use `grd:help --all`.

**This folder already has research files, but GRD is not set up here yet**

Recommended next steps:

1. Map this folder first (recommended) - use `grd:map-research`. Example: `This folder already has papers, notes, code, or notebooks.`
2. Take a guided tour first - use `grd:tour`.
3. Start a brand-new GRD project anyway - use `grd:new-project --minimal`. Example: `I want to ignore the old files and begin fresh.`

Other useful options, only if one of these is what you need:

- Explain one concept - use `grd:explain`.
- Show all commands - use `grd:help --all`.

**This folder looks new or mostly empty**

Recommended next steps:

1. Fast start (recommended) - use `grd:new-project --minimal`. Example: `I have a new project idea and want the shortest setup path.`
2. Full guided setup - use `grd:new-project`. Example: `I want the fuller guided questioning path.`
3. Take a guided tour first - use `grd:tour`.

Other useful options, only if one of these is what you need:

- Explain one concept - use `grd:explain`.
- Show all commands - use `grd:help --all`.

If you need to reopen a different GRD project, use `grd resume --recent` in your normal terminal first. That is the explicit multi-project picker in the recovery ladder; the rows are advisory, and once you open the selected workspace `grd:resume-work` reloads its canonical state. If it finds exactly one recoverable project it may auto-select it, otherwise choose from the list. Then open the workspace and continue with `grd:resume-work`.

Add one final sentence before asking for the choice:

`If you want the broader capability overview before choosing, pick \`tour\`. It will explain later paths such as planning phases, verifying work, writing papers, and handling tangents without changing anything.`

Ask for exactly one choice.
</step>

<step name="route_choice">
Route immediately into the real existing workflow for the chosen path.

**If the researcher chooses `Resume this project (recommended)` or `Continue where I left off`:**

- Read `{GRD_INSTALL_DIR}/workflows/resume-work.md` with the file-read tool.
- Follow that workflow as if the researcher had run `grd:resume-work`.

**If the researcher chooses `Review project status first`:**

- Read `{GRD_INSTALL_DIR}/workflows/progress.md` with the file-read tool.
- Follow that workflow as if the researcher had run `grd:progress`.

**If the researcher chooses `Suggest the next best step`:**

- `suggest-next` is a workflow-exempt command, not a shared workflow include.
- Follow the installed `grd:suggest-next` command contract directly, as if the researcher had run it.

**If the researcher chooses `Map this folder first (recommended)` or `Refresh the research map`:**

- Read `{GRD_INSTALL_DIR}/workflows/map-research.md` with the file-read tool.
- Follow that workflow as if the researcher had run `grd:map-research`.

**If the researcher chooses `Fast start`:**

- Follow the installed `grd:new-project --minimal` command contract directly, as if the researcher had run it.

**If the researcher chooses `Full guided setup` or `Turn this into a full GRD project`:**

- Follow the installed `grd:new-project` command contract directly, as if the researcher had run it.

**If the researcher chooses `Take a guided tour first`:**

- Follow the installed `grd:tour` command contract directly, as if the researcher had run it.

**If the researcher chooses `Do a small bounded task`:**

- Read `{GRD_INSTALL_DIR}/workflows/quick.md` with the file-read tool.
- Follow that workflow as if the researcher had run `grd:quick`.

**If the researcher chooses `Explain one concept`:**

- If `$ARGUMENTS` contains a usable concept or question, reuse it.
- Otherwise ask for one short concept or question before continuing.
- Read `{GRD_INSTALL_DIR}/workflows/explain.md` with the file-read tool.
- Follow that workflow as if the researcher had run `grd:explain <topic>`.

**If the researcher chooses `Show all commands`:**

- Follow the installed `grd:help --all` command contract directly, as if the researcher had run it.

**If the researcher chooses `Reopen a different GRD project`:**

- Do not silently switch projects from inside the runtime.
- Explain exactly:
  - `Use \`grd resume --recent\` in your normal terminal to find the project first.`
  - `The recent-project picker is advisory; choose the workspace there, then \`grd:resume-work\` reloads canonical state for that project.`
  - `If there is exactly one recoverable project, GRD may auto-select it; otherwise choose the project explicitly from the recent-project picker.`
  - `Then open that project folder in the runtime and run \`grd:resume-work\`.`
  - `In GRD terms, \`resume-work\` is the in-runtime continuation step once the recovery ladder has identified the right project and reopened its workspace.`
- STOP after giving those instructions.
</step>

<step name="guardrails">
Keep the routing strict:

- `grd:start` is the chooser, not a second implementation of `grd:new-project`, `grd:resume-work`, `grd:map-research`, `grd:quick`, `grd:explain`, or `grd:help`.
- Do not silently create project files from `grd:start` itself.
- Do not silently switch the user into a different project folder.
- When in doubt between a fresh folder and an existing research folder, prefer `map-research` as the safer recommendation.
- Keep the wording beginner-friendly, but keep the official GRD terms visible in plain-English form so the researcher learns them.
</step>

</process>

<success_criteria>
- [ ] The folder is classified as an existing GRD project, research map only, existing research folder, or fresh folder
- [ ] The researcher sees only the choices that fit that state
- [ ] The chosen path routes into the real existing workflow instead of duplicating it
- [ ] Cross-project recovery stays explicit through `grd resume --recent` from the normal terminal
- [ ] `grd:start` stays a beginner-friendly chooser, not a parallel onboarding state machine
</success_criteria>
