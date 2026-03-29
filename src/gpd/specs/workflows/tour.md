<purpose>
Provide a beginner-friendly guided tour of the core GPD command surface for
new users. Teach what the main commands do and when to use them, and make clear
that the tour does not create project artifacts, create files, or route into
other workflows.
</purpose>

<required_reading>
Read all files referenced by the invoking prompt's execution_context before
starting.
</required_reading>

<process>

<step name="orient_the_user">
Open with one short sentence:

`This is a guided tour of the main GPD commands. It does not change your files.`

If `$ARGUMENTS` is non-empty, show it back as one short context line such as
`You asked about: <goal>. I will use that as context for the tour.`
Do not narrow the command list or route based on it.

Then explain that GPD has two broad entry modes:

- `start` for choosing the right first action in a folder
- direct commands for when the user already knows what they want
</step>

<step name="explain_the_core_paths">
Use a compact, beginner-facing table or bullet list with these entries:

- `/gpd:start` - Use when you are not sure what this folder should do yet
- `/gpd:new-project --minimal` - Use for the fastest start on brand-new work
- `/gpd:new-project` - Use when you want the full guided setup
- `/gpd:map-research` - Use when you already have papers, notes, or code and want GPD to map them first
- `/gpd:resume-work` - Use when an existing GPD project is already set up and you want to continue
- `/gpd:progress` - Use when you want a broader status snapshot
- `/gpd:suggest-next` - Use when you want the next best action after resuming
- `/gpd:explain <topic>` - Use when you want a concept explained in plain language
- `/gpd:quick` - Use for a small bounded task
- `/gpd:help` - Use when you want the command reference

For each entry, include one plain-English sentence about when it is the right
choice and one sentence about when it is not the right choice.
</step>

<step name="show_simple_distinctions">
Summarize the most common command distinctions in plain language:

- If you want GPD to inspect the current folder and tell you the right path, use `/gpd:start`
- If you already know the work is brand-new, use `/gpd:new-project --minimal` or `/gpd:new-project`
- If you already know the folder contains existing research material, use `/gpd:map-research`
- If you already know the folder already has GPD state, use `/gpd:resume-work`
- If you only want a concept explained, use `/gpd:explain <topic>`
- If you only want the next step after resuming, use `/gpd:suggest-next`

Keep this section short and explicitly note that `tour` does not execute those
commands, inspect the folder for you, or continue into another workflow.
</step>

<step name="highlight_common_mistakes">
Call out the beginner traps to avoid:

- Do not use `new-project` if you only want to look around
- Do not use `resume-work` unless the project already has GPD state
- Do not use `map-research` for a truly empty folder
- Do not treat `help` as a setup wizard; it is the reference surface

Keep the tone explanatory, not corrective.
</step>

<step name="close_with_next_steps">
End with a short wrap-up that says:

- `If you are still unsure, run /gpd:start.`
- `If you want the reference list again later, run /gpd:help.`
- `If you want to practice on your current folder, choose one of the commands above only after you know which path fits; otherwise use /gpd:start to decide safely.`

Do not ask the user to pick a branch and do not continue into another workflow.
</step>

<success_criteria>
- [ ] The user sees that `tour` is read-only and non-destructive
- [ ] The core GPD entry points are explained in beginner language
- [ ] The difference between `start`, `new-project`, `map-research`, and `resume-work` is clear
- [ ] The response does not silently route into another workflow
- [ ] The response ends with simple next-step guidance
</success_criteria>
