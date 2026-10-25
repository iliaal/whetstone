<overview>
Agent execution patterns for building reliable agent loops: how agents signal completion, track partial progress for resume, select appropriate model tiers, and handle context limits.
</overview>

<completion_signals>
## Completion Signals

Agents need an explicit way to say "I'm done."

### Anti-Pattern: Heuristic Detection

Detecting completion through heuristics is fragile:

- Consecutive iterations without tool calls
- Checking for expected output files
- Tracking "no progress" states
- Time-based timeouts

These break in edge cases and create unpredictable behavior.

### Pattern: Explicit Completion Tool

Provide a `complete_task` tool that:
- Takes a summary of what was accomplished
- Returns both a terminal status and a signal that stops the loop
- Works identically across all agent types

Preserve `success`, `partial`, and `blocked` through tool results, checkpoints, and the final response. Stopping the loop does not establish successful completion. Let the application define the complete criterion set and evaluate each criterion against observed state. Derive the aggregate outcome and remaining criterion IDs from those results; an agent's summary is not acceptance evidence.

```typescript
type CriterionResult = { id: string; status: "passed" | "failed" | "unknown" };
type AcceptanceCriterion = { id: string; check: () => Promise<boolean> };

function registerCompletionTool(criteria: readonly AcceptanceCriterion[]) {
  const checks = criteria.map(criterion => ({ ...criterion }));
  if (checks.length === 0 || checks.some(c => c.id.trim() === "") ||
      new Set(checks.map(c => c.id)).size !== checks.length) {
    throw new Error("Acceptance criteria require nonempty, unique IDs");
  }
  tool("complete_task", {
    summary: z.string().describe("Summary of outcomes and remaining work"),
    status: z.enum(["success", "partial", "blocked"]),
  }, async ({ summary, status }): Promise<ToolResult> => {
    const acceptance = await Promise.all(checks.map(async (c): Promise<CriterionResult> => {
      try {
        return { id: c.id, status: await c.check() ? "passed" : "failed" };
      } catch {
        return { id: c.id, status: "unknown" };
      }
    }));
    const remaining = acceptance.filter(c => c.status !== "passed").map(c => c.id);
    if (status === "success" && remaining.length > 0) {
      return {
        success: false,
        output: `Unmet criteria: ${remaining.join(", ")}. Continue or report partial/blocked.`,
        shouldContinue: true,
      };
    }

    return {
      success: true,
      output: summary,
      shouldContinue: false,
      terminalStatus: status,
      acceptanceStatus: remaining.length === 0 ? "passed" : "unmet",
      acceptance,
      remaining,
    };
  });
}
```

Supply the checks from the application for the current request. Persist the computed `acceptanceStatus`, criterion results, and remaining IDs with the terminal report, including `partial` and `blocked`. Keep the requested stop status separate from the application-derived acceptance aggregate; a conservative `partial` or `blocked` cannot overwrite observed acceptance. Reject missing, duplicate, or invented criterion IDs if accepting reports across a process boundary. Treat `unknown` as unmet; never upgrade it to success from the agent's prose.

### The ToolResult Pattern

Structure tool results to separate success from continuation:

```typescript
type TerminalStatus = "success" | "partial" | "blocked" | "cancelled";

type ToolResult =
  | { success: boolean; output: string; shouldContinue: true }
  | {
      success: true;
      output: string;
      shouldContinue: false;
      terminalStatus: TerminalStatus;
      acceptanceStatus: "passed" | "unmet";
      acceptance: CriterionResult[];
      remaining: string[];
    };
```

### Key Insight

**This is different from success/failure:**

- A tool can **succeed** AND signal **stop** (terminal outcome)
- A tool can **fail** AND signal **continue** (recoverable error, try something else)
- A completion tool can succeed at recording `partial` or `blocked` while the task remains unfinished

```typescript
// Examples:
read_file("/missing.txt")
// → { success: false, output: "File not found", shouldContinue: true }
// Agent can try a different file or ask for clarification

complete_task({ summary: "Organized all downloads into folders", status: "success" })
// → terminalStatus: "success", shouldContinue: false, application checks passed

write_file("/output.md", content)
// → { success: true, output: "Wrote file", shouldContinue: true }
// Agent keeps working toward the goal
```

### System Prompt Guidance

Tell the agent when to complete:

```markdown
## Completing Tasks

When you've accomplished the user's request:
1. Verify your work (read back files you created, check results)
2. Call `complete_task` with status "success" and a summary of outcomes
3. Don't keep working after the goal is achieved

If some requested work remains unfinished:
- Call `complete_task` with status "partial" and identify the remaining work

If you're blocked and can't proceed:
- Call `complete_task` with status "blocked" and explain why
- Don't loop forever trying the same thing
```
</completion_signals>

<cancellation>
## Cooperative Cancellation and Cleanup

Accept cancellation through a durable flag even while an action holds the run lock. Have the running loop observe the flag between actions; serialize state changes and compensation under the same run lock or lease. Persist `cancelling` before cleanup starts. Reconcile an in-flight action with an unknown outcome before deciding whether it needs compensation.

Compensate only recorded side effects that actually occurred and are eligible for reversal. Preserve intended business results unless reversal is authorized. Persist a cleanup outcome of `not_required`, `verified`, `failed`, or `unavailable`, plus any outstanding effects. Finish cancellation as `cancelled`, never `success`; block normal completion while cancellation is pending. For ordinary completion, require verified removal of temporary effects, or `not_required` when none existed. Failed or unavailable cleanup prevents success and requires reconciliation before resume.
</cancellation>

<partial_completion>
## Partial Completion

For multi-step tasks, track progress at the task level for resume capability.

### Task State Tracking

```typescript
type TaskStatus = "pending" | "inProgress" | "completed" | "failed" | "skipped";
type AgentTask = {
  id: string;
  description: string;
  status: TaskStatus;
  notes: string | null;
};

function taskProgress(tasks: readonly AgentTask[]): { completed: number; total: number } {
  return {
    completed: tasks.filter(task => task.status === "completed").length,
    total: tasks.length,
  };
}

function tasksFinished(tasks: readonly AgentTask[]): boolean {
  return tasks.every(task => task.status === "completed" || task.status === "skipped");
}
```

A skipped task needs an explicitly accepted scope reason; finishing the task list does not bypass application-owned acceptance checks.

### UI Progress Display

Show users what's happening:

```
Progress: 3/5 tasks complete (60%)
✅ [1] Find source materials
✅ [2] Download full text
✅ [3] Extract key passages
❌ [4] Generate summary - Error: context limit exceeded
⏳ [5] Create outline - Pending
```

### Partial Completion Scenarios

**Agent hits max iterations before finishing:**
- Some tasks completed, some pending
- Checkpoint saved with current state
- Resume continues from where it left off, not from beginning

**Delegated agents reach a limit:**
Enforce a configured maximum delegation depth in the harness; withhold the spawn capability from children at that depth. Bound each child's turns and mark its output `partial` on exhaustion, retaining a checkpoint the parent can resume. Keep these limits in orchestration rather than relying on instructions to stop recursive spawning.

**Agent fails on one task:**
- Task marked `failed` with error in notes
- Other tasks may continue (agent decides)
- Orchestrator doesn't automatically abort entire session

**Network error mid-task:**
- Current iteration throws
- Session marked `failed`
- Checkpoint preserves messages up to that point
- Resume possible from checkpoint

### Checkpoint Structure

```typescript
type JSONValue = null | boolean | number | string | JSONValue[] |
  { [key: string]: JSONValue };

type AgentCheckpoint = {
  version: 1;
  sessionId: string;
  agentType: string;
  messages: Message[];
  iterationCount: number;
  tasks: AgentTask[];
  customState: { [key: string]: JSONValue };
  waitingReason: string | null;
  resumeState: "running" | "waitingForUser" | "partial" | "blocked";
  terminalReport: {
    status: TerminalStatus;
    acceptanceStatus: "passed" | "unmet";
    acceptance: CriterionResult[];
    remaining: string[];
  } | null;
  attemptIds: string[];
  timestamp: number;
};

function checkpointIsFresh(checkpoint: AgentCheckpoint, now = Date.now()): boolean {
  const age = now - checkpoint.timestamp;
  return checkpoint.version === 1 && age >= 0 && age < 3600_000;
}

function encodeCheckpoint(checkpoint: AgentCheckpoint): string {
  return JSON.stringify(checkpoint);
}
```

Use the preceding `AgentTask` type and the `Message` union in Unified Agent Orchestrator below. Preserve assistant tool-call IDs, names, and inputs and each result's matching call ID in checkpoint JSON. Accept only schema-validated JSON values at runtime; reject unsupported versions, non-finite numbers, cycles, and missing fields rather than coercing them into a valid-looking checkpoint. Persist encoded bytes by atomic replacement and propagate errors. A stale checkpoint is retained for reconciliation and explicit user disposition, not silently replayed or deleted. Reconcile every durable attempt before running remaining effects; follow [mobile-execution.md](./mobile-execution.md).

### Resume Flow

1. On app launch, scan for valid checkpoints
2. Show user: "You have an incomplete session. Resume?"
3. On resume:
   - Restore messages to conversation
   - Restore task states
   - Continue agent loop from where it left off
4. On dismiss:
   - Delete checkpoint
   - Start fresh if user tries again
</partial_completion>

<model_tier_selection>
## Model Tier Selection

Different agents need different intelligence levels. Use the cheapest model that achieves the outcome.

### Tier Guidelines

| Agent Type | Recommended Tier | Reasoning |
|------------|-----------------|-----------|
| Chat/Conversation | Balanced (Sonnet) | Fast responses, good reasoning |
| Research | Balanced (Sonnet) | Tool loops, not ultra-complex synthesis |
| Content Generation | Balanced (Sonnet) | Creative but not synthesis-heavy |
| Complex Analysis | Powerful (Opus) | Multi-document synthesis, nuanced judgment |
| Profile Generation | Powerful (Opus) | Photo analysis, complex pattern recognition |
| Quick Queries | Fast (Haiku) | Simple lookups, quick transformations |
| Simple Classification | Fast (Haiku) | High volume, simple decisions |

### Implementation

Configure the tier's provider ID at startup using the validated `configuredModel` function in [mobile-cost.md](./mobile-cost.md), including current input and output token rates.

```typescript
type AgentConfig = {
  name: string;
  modelTier: "fast" | "balanced" | "powerful";
  toolNames: readonly string[];
  systemPrompt: string;
  maxIterations: number;
};

const researchConfig: AgentConfig = {
  name: "research",
  modelTier: "balanced",
  toolNames: ["read_file", "write_file", "web_search", "web_fetch"],
  systemPrompt: "Research the selected book and persist sourced findings.",
  maxIterations: 20,
};

const quickLookupConfig: AgentConfig = {
  name: "lookup",
  modelTier: "fast",
  toolNames: ["read_library"],
  systemPrompt: "Answer quick questions using the authorized library.",
  maxIterations: 3,
};
```

Resolve these names to the installed, authorized tool registry; reject missing entries. Model tiers express a quality/cost choice, not a fixed historical model family.

### Cost Optimization Strategies

1. **Start with balanced, upgrade if quality insufficient**
2. **Use fast tier for tool-heavy loops** where each turn is simple
3. **Reserve powerful tier for synthesis tasks** (comparing multiple sources)
4. **Consider token limits per turn** to control costs
5. **Cache expensive operations** to avoid repeated calls
</model_tier_selection>

<context_limits>
## Context Limits

Agent sessions can extend indefinitely, but context windows don't. Design for bounded context from the start.

### The Problem

```
Turn 1: User asks question → 500 tokens
Turn 2: Agent reads file → 10,000 tokens
Turn 3: Agent reads another file → 10,000 tokens
Turn 4: Agent researches → 20,000 tokens
...
Turn 10: Context window exceeded
```

### Design Principles

**1. Tools should support iterative refinement**

Instead of all-or-nothing, design for summary → detail → full:

```typescript
// Good: Supports iterative refinement
tool("read_file", {
  path: z.string(),
  preview: z.boolean().default(true),  // Return first 1000 chars by default
  full: z.boolean().default(false),    // Opt-in to full content
}, ...);

tool("search_files", {
  query: z.string(),
  summaryOnly: z.boolean().default(true),  // Return matches, not full files
}, ...);
```

**2. Provide consolidation tools**

Give agents a way to consolidate learnings mid-session:

```typescript
tool("summarize_and_continue", {
  keyPoints: z.array(z.string()),
  nextSteps: z.array(z.string()),
}, async ({ keyPoints, nextSteps }) => {
  // Store summary, potentially truncate earlier messages
  await saveSessionSummary({ keyPoints, nextSteps });
  return { text: "Summary saved. Continuing with focus on: " + nextSteps.join(", ") };
});
```

**3. Design for truncation**

Assume the orchestrator may truncate early messages. Important context should be:
- In the system prompt (always present)
- In files (can be re-read)
- Summarized in context.md

### Implementation Strategies

Use application adapters for token estimation and summarization. Partition history only between complete assistant-call/result groups. Keep retained groups unchanged, including IDs, names, and inputs. Retain an in-flight group verbatim until its durable attempts are reconciled; summarize only completed older groups. A summary is context, not a replacement call record to replay.

```typescript
function compactContext<M>(
  systemMessage: M,
  olderMessages: readonly M[],
  recentMessages: readonly M[],
  estimateTokens: (messages: readonly M[]) => number,
  summarize: (messages: readonly M[]) => M[],
): M[] {
  const targetContextTokens = 80_000;
  const messages = [systemMessage, ...olderMessages, ...recentMessages];
  if (estimateTokens(messages) <= targetContextTokens) return messages;
  const compacted = [systemMessage, ...summarize(olderMessages), ...recentMessages];
  if (estimateTokens(compacted) > targetContextTokens) {
    throw new Error("Context still exceeds target; reduce data before generation");
  }
  return compacted;
}
```

### System Prompt Guidance

```markdown
## Managing Context

For long tasks, periodically consolidate what you've learned:
1. If you've gathered a lot of information, summarize key points
2. Save important findings to files (they persist beyond context)
3. Use `summarize_and_continue` if the conversation is getting long

Don't try to hold everything in memory. Write it down.
```
</context_limits>

<orchestrator_pattern>
## Unified Agent Orchestrator

One execution engine, many agent types. All agents use the same orchestrator with different configurations.

```typescript
interface ToolCall {
  id: string;
  name: string;
  input: JSONValue;
}

type Message =
  | { role: "system" | "user"; content: string }
  | { role: "assistant"; content: string; toolCalls: ToolCall[] }
  | { role: "tool"; content: string; toolCallId: string; name: string };

interface ModelResponse {
  content: string;
  toolCalls: ToolCall[];
}

interface AgentConfig {
  systemPrompt: string;
  maxIterations: number;
}

interface AgentResult {
  status: TerminalStatus | "responded";
  stopReason?: "turn_limit";
  output: string;
  iterations: number;
}

class AgentOrchestrator {
  constructor(
    private generateResponse: (
      config: AgentConfig,
      messages: Message[],
    ) => Promise<ModelResponse>,
    private executeToolCall: (call: ToolCall) => Promise<ToolResult>,
    private saveMessages: (messages: readonly Message[]) => Promise<void>,
  ) {}

  async run(config: AgentConfig, userMessage: string): Promise<AgentResult> {
    const messages: Message[] = [
      { role: "system", content: config.systemPrompt },
      { role: "user", content: userMessage },
    ];
    await this.saveMessages(messages);

    for (let iteration = 0; iteration < config.maxIterations; iteration += 1) {
      const response = await this.generateResponse(config, messages);
      const knownIds = new Set(messages.flatMap(message =>
        message.role === "assistant" ? message.toolCalls.map(call => call.id) : []
      ));
      for (const call of response.toolCalls) {
        if (!call.id || knownIds.has(call.id)) throw new Error("Invalid tool-call ID");
        knownIds.add(call.id);
      }
      messages.push({
        role: "assistant",
        content: response.content,
        toolCalls: structuredClone(response.toolCalls),
      });
      await this.saveMessages(messages);

      for (const [index, toolCall] of response.toolCalls.entries()) {
        const result = await this.executeToolCall(toolCall);
        messages.push({
          role: "tool", toolCallId: toolCall.id, name: toolCall.name,
          content: JSON.stringify(result),
        });
        await this.saveMessages(messages);

        if (!result.shouldContinue) {
          for (const skipped of response.toolCalls.slice(index + 1)) {
            messages.push({
              role: "tool", toolCallId: skipped.id, name: skipped.name,
              content: JSON.stringify({
                success: false, output: "Not executed: the run stopped.",
                shouldContinue: true,
              }),
            });
          }
          await this.saveMessages(messages);
          return {
            status: result.terminalStatus,
            output: result.output,
            iterations: iteration + 1,
          };
        }
      }

      if (response.toolCalls.length === 0) {
        return {
          status: "responded",
          output: response.content,
          iterations: iteration + 1,
        };
      }
    }

    return {
      status: "partial",
      stopReason: "turn_limit",
      output: messages[messages.length - 1].content,
      iterations: config.maxIterations,
    };
  }
}
```

The provider adapter must return stable tool-call IDs and map the complete `Message` union to its assistant-call and tool-result fields. Validate names, JSON inputs, and response shapes at that boundary. Implement `saveMessages` with the checkpoint service: encode a snapshot of the complete messages, persist it durably, and propagate failure before the next action. The loop saves assistant calls before dispatching effects and their correlated results after the executor durably records outcomes; restore those same messages from checkpoints. Results for unexecuted calls in a terminal batch explicitly report that they did not run. Never infer call identity from result text or keep essential history only in adapter closure state.

Have the tool executor validate and persist runtime results before returning this type. Preserve the terminal status in persistence and UI labels. A reply without a completion signal remains `responded`. Save a checkpoint before returning `partial` with `turn_limit`; exhaustion remains unfinished. Wrap action boundaries with the cooperative cancellation and cleanup lifecycle above.

### Benefits

- Consistent lifecycle management across all agent types
- Automatic checkpoint/resume (critical for mobile)
- Shared tool protocol
- Easy to add new agent types
- Centralized error handling and logging
</orchestrator_pattern>

<checklist>
## Agent Execution Checklist

### Completion Signals
- [ ] `complete_task` tool provided (explicit completion)
- [ ] No heuristic completion detection
- [ ] Tool results include `shouldContinue` flag
- [ ] Terminal statuses survive orchestration and checkpoint restore
- [ ] Assistant calls and correlated results retain IDs, names, and inputs through provider translation, checkpoints, and compaction
- [ ] `success` requires application-observed acceptance evidence
- [ ] Terminal reports cover exactly the application's criterion set and compute unmet IDs
- [ ] Cancellation persists its lifecycle, cleanup outcome, and outstanding effects
- [ ] System prompt guides when to complete

### Partial Completion
- [ ] Tasks tracked with status (pending, in_progress, completed, failed)
- [ ] Checkpoints saved for resume
- [ ] Progress visible to user
- [ ] Resume continues from where left off
- [ ] Delegation depth and per-agent turns are enforced by the harness

### Model Tiers
- [ ] Tier selected based on task complexity
- [ ] Cost optimization considered
- [ ] Fast tier for simple operations
- [ ] Powerful tier reserved for synthesis

### Context Limits
- [ ] Tools support iterative refinement (preview vs full)
- [ ] Consolidation mechanism available
- [ ] Important context persisted to files
- [ ] Truncation strategy defined
</checklist>
