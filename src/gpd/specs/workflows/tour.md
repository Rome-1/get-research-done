<purpose>
Provide a gentle, read-only walkthrough of the core GPD command surface for
new users. Teach what the main commands do and when to use them, without
creating files or routing into other workflows.
</purpose>

<required_reading>
Read all files referenced by the invoking prompt's execution_context before
starting.
</required_reading>

<process>

<step name="orient_the_user">
Open with one short sentence:

`This is a guided tour of the main GPD commands. It does not change your files.`

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

<step name="show_simple_decision_rules">
Summarize the decision tree in plain language:

- If the folder is empty or new, start with `/gpd:start` or `/gpd:new-project --minimal`
- If the folder already contains research material, use `/gpd:map-research`
- If the folder already has GPD state, use `/gpd:resume-work`
- If the user only wants a concept explained, use `/gpd:explain <topic>`
- If the user only wants the next step, use `/gpd:suggest-next`

Keep this section short and explicitly note that `tour` does not execute those
commands.
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
- `If you want to practice on your current folder, choose one of the commands above based on the state of the folder.`

Do not ask the user to pick a branch and do not continue into another workflow.
</step>

<success_criteria>
- [ ] The user sees that `tour` is read-only and non-destructive
- [ ] The core GPD entry points are explained in beginner language
- [ ] The difference between `start`, `new-project`, `map-research`, and `resume-work` is clear
- [ ] The response does not silently route into another workflow
- [ ] The response ends with simple next-step guidance
</success_criteria>
