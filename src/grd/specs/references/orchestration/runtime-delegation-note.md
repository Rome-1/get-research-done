# Runtime Delegation Note

Spawn a fresh subagent for the task below. This is a one-shot handoff: if the child needs human input, it must return `status: checkpoint` and stop. Do not make the child wait in place. If the task produces files, verify the expected artifacts on disk before marking the handoff complete. The orchestrator owns any fresh continuation handoff. Adapt the `task()` call to your runtime's agent spawning mechanism. If `model` resolves to `null` or an empty string, omit it so the runtime uses its default model. Always pass `readonly=false` for file-producing agents.
