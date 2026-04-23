# Dispatch Anti-Patterns

Load this reference when designing a multi-agent workflow. Named failure modes to recognize before they ship — each one looks reasonable in isolation and each one produces worse outcomes than direct execution.

| Anti-pattern | What it looks like | Why it fails |
|--------------|-------------------|--------------|
| **Router persona** | An agent whose job is "decide which other agent to spawn, then spawn it" | Adds a serialization point with no judgment value. The caller could make the same decision from the task description. Removes context that the downstream agent needs. |
| **Persona calls persona** | Agent A dispatches agent B mid-task, agent B dispatches agent C | Claude Code does not allow subagents to spawn subagents — the Task tool is not available inside subagent contexts. Designs that assume nested dispatch silently fall back to "agent A does the work of B and C itself," usually worse. |
| **Sequential paraphraser** | An orchestrator that runs agents serially and rewrites each output before passing it downstream | Introduces drift at every hop. If agents must be sequential, pass outputs verbatim — summarize only at the final synthesis step, not between stages. |
| **Deep persona trees** | 4+ levels of agent specialization for a single task ("architect → reviewer → security-sub-reviewer → XSS-specialist") | Each level adds coordination cost without adding discrimination. Two levels (orchestrator + specialists in parallel) handle almost all real work. |

Rule of thumb: if the proposed swarm has more coordinator roles than worker roles, collapse it.
