# Anti-Patterns

## Common Approaches That Aren't Fully Agent-Native

These aren't necessarily wrong -- they may be appropriate for your use case. But they're worth recognizing as different from the architecture this document describes.

**Agent as router** -- The agent figures out what the user wants, then calls the right function. The agent's intelligence is used to route, not to act. This can work, but you're using a fraction of what agents can do.

**Build the app, then add agent** -- You build features the traditional way (as code), then expose them to an agent. The agent can only do what your features already do. You won't get emergent capability.

**Request/response thinking** -- Agent gets input, does one thing, returns output. This misses the loop: agent gets an outcome to achieve, operates until it's done, handles unexpected situations along the way.

**Defensive tool design** -- You over-constrain tool inputs because you're used to defensive programming. Strict enums, validation at every layer. This is safe, but it prevents the agent from doing things you didn't anticipate.

**Happy path in code, agent just executes** -- Traditional software handles edge cases in code -- you write the logic for what happens when X goes wrong. Agent-native lets the agent handle edge cases with judgment. If your code handles all the edge cases, the agent is just a caller.

---

## Specific Anti-Patterns

**THE CARDINAL SIN: Agent executes your code instead of figuring things out**

```typescript
// WRONG - You wrote the workflow, agent just executes it
tool("process_feedback", async ({ message }) => {
  const category = categorize(message);      // Your code decides
  const priority = calculatePriority(message); // Your code decides
  await store(message, category, priority);   // Your code orchestrates
  if (priority > 3) await notify();           // Your code decides
});

// RIGHT - Agent figures out how to process feedback
tools: store_item, send_message  // Primitives
prompt: "Rate importance 1-5 based on actionability, store feedback, notify if >= 4"
```

**Workflow-shaped tools** -- `analyze_and_organize` bundles judgment into the tool. Break it into primitives and let the agent compose them.

**Context starvation** -- Agent doesn't know what resources exist in the app.
```
User: "Write something about Catherine the Great in my feed"
Agent: "What feed? I don't understand what system you're referring to."
```
Fix: Inject available resources, capabilities, and vocabulary into system prompt.

**Orphan UI actions** -- User can do something through the UI that the agent can't achieve. Fix: maintain parity.

**Silent actions** -- Agent changes state but UI doesn't update. Fix: Use shared data stores with reactive binding, or file system observation.

**Heuristic completion detection** -- Detecting agent completion through heuristics (consecutive iterations without tool calls, checking for expected output files). This is fragile. Fix: Require agents to explicitly signal completion through a `complete_task` tool.

**Static tool mapping for dynamic APIs** -- Building 50 tools for 50 API endpoints when a `discover` + `access` pattern would give more flexibility.
```typescript
// WRONG - Every API type needs a hardcoded tool
tool("read_steps", ...)
tool("read_heart_rate", ...)
tool("read_sleep", ...)
// When glucose tracking is added... code change required

// RIGHT - Dynamic capability discovery
tool("list_available_types", ...)  // Discover what's available
tool("read_health_data", { dataType: z.string() }, ...)  // Access any type
```

**Incomplete CRUD** -- Agent can create but not update or delete.
```typescript
// User: "Delete that journal entry"
// Agent: "I don't have a tool for that"
tool("create_journal_entry", ...)  // Missing: update, delete
```
Fix: Every entity needs full CRUD.

**Sandbox isolation** -- Agent works in separate data space from user.
```
Documents/
  user_files/        <-- User's space
  agent_output/      <-- Agent's space (isolated)
```
Fix: Use shared workspace where both operate on same files.

**Gates without reason** -- Domain tool is the only way to do something, and you didn't intend to restrict access. The default is open. Keep primitives available unless there's a specific reason to gate.

**Artificial capability limits** -- Restricting what the agent can do out of vague safety concerns rather than specific risks. Be thoughtful about restricting capabilities. The agent should generally be able to do what users can do.
