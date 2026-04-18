<overview>
How to design MCP tools following prompt-native principles. Tools should be primitives that enable capability, not workflows that encode decisions.

**Core principle:** Whatever a user can do, the agent should be able to do. Don't artificially limit the agent--give it the same primitives a power user would have.
</overview>

<principle name="primitives-not-workflows">
## Tools Are Primitives, Not Workflows

**Wrong approach:** Tools that encode business logic
```typescript
tool("process_feedback", {
  feedback: z.string(),
  category: z.enum(["bug", "feature", "question"]),
  priority: z.enum(["low", "medium", "high"]),
}, async ({ feedback, category, priority }) => {
  // Tool decides how to process
  const processed = categorize(feedback);
  const stored = await saveToDatabase(processed);
  const notification = await notify(priority);
  return { processed, stored, notification };
});
```

**Right approach:** Primitives that enable any workflow
```typescript
tool("store_item", {
  key: z.string(),
  value: z.any(),
}, async ({ key, value }) => {
  await db.set(key, value);
  return { text: `Stored ${key}` };
});

tool("send_message", {
  channel: z.string(),
  content: z.string(),
}, async ({ channel, content }) => {
  await messenger.send(channel, content);
  return { text: "Sent" };
});
```

The agent decides categorization, priority, and when to notify based on the system prompt.
</principle>

<principle name="descriptive-names">
## Tools Should Have Descriptive, Primitive Names

Names should describe the capability, not the use case:

| Wrong | Right |
|-------|-------|
| `process_user_feedback` | `store_item` |
| `create_feedback_summary` | `write_file` |
| `send_notification` | `send_message` |
| `deploy_to_production` | `git_push` |

The prompt tells the agent *when* to use primitives. The tool just provides *capability*.
</principle>

<principle name="simple-inputs">
## Inputs Should Be Simple

Tools accept data. They don't accept decisions.

**Wrong:** Tool accepts decisions
```typescript
tool("format_content", {
  content: z.string(),
  format: z.enum(["markdown", "html", "json"]),
  style: z.enum(["formal", "casual", "technical"]),
}, ...)
```

**Right:** Tool accepts data, agent decides format
```typescript
tool("write_file", {
  path: z.string(),
  content: z.string(),
}, ...)
// Agent decides to write index.html with HTML content, or data.json with JSON
```
</principle>

<principle name="rich-outputs">
## Outputs Should Be Rich

Return enough information for the agent to verify and iterate.

**Wrong:** Minimal output
```typescript
async ({ key }) => {
  await db.delete(key);
  return { text: "Deleted" };
}
```

**Right:** Rich output
```typescript
async ({ key }) => {
  const existed = await db.has(key);
  if (!existed) {
    return { text: `Key ${key} did not exist` };
  }
  await db.delete(key);
  return { text: `Deleted ${key}. ${await db.count()} items remaining.` };
}
```
</principle>

<design_template>
## Tool Design Template

```typescript
import { createSdkMcpServer, tool } from "@anthropic-ai/claude-agent-sdk";
import { z } from "zod";

export const serverName = createSdkMcpServer({
  name: "server-name",
  version: "1.0.0",
  tools: [
    // READ operations
    tool(
      "read_item",
      "Read an item by key",
      { key: z.string().describe("Item key") },
      async ({ key }) => {
        const item = await storage.get(key);
        return {
          content: [{
            type: "text",
            text: item ? JSON.stringify(item, null, 2) : `Not found: ${key}`,
          }],
          isError: !item,
        };
      }
    ),

    tool(
      "list_items",
      "List all items, optionally filtered",
      {
        prefix: z.string().optional().describe("Filter by key prefix"),
        limit: z.number().default(100).describe("Max items"),
      },
      async ({ prefix, limit }) => {
        const items = await storage.list({ prefix, limit });
        return {
          content: [{
            type: "text",
            text: `Found ${items.length} items:\n${items.map(i => i.key).join("\n")}`,
          }],
        };
      }
    ),

    // WRITE operations
    tool(
      "store_item",
      "Store an item",
      {
        key: z.string().describe("Item key"),
        value: z.any().describe("Item data"),
      },
      async ({ key, value }) => {
        await storage.set(key, value);
        return {
          content: [{ type: "text", text: `Stored ${key}` }],
        };
      }
    ),

    tool(
      "delete_item",
      "Delete an item",
      { key: z.string().describe("Item key") },
      async ({ key }) => {
        const existed = await storage.delete(key);
        return {
          content: [{
            type: "text",
            text: existed ? `Deleted ${key}` : `${key} did not exist`,
          }],
        };
      }
    ),

    // EXTERNAL operations
    tool(
      "call_api",
      "Make an HTTP request",
      {
        url: z.string().url(),
        method: z.enum(["GET", "POST", "PUT", "DELETE"]).default("GET"),
        body: z.any().optional(),
      },
      async ({ url, method, body }) => {
        const response = await fetch(url, { method, body: JSON.stringify(body) });
        const text = await response.text();
        return {
          content: [{
            type: "text",
            text: `${response.status} ${response.statusText}\n\n${text}`,
          }],
          isError: !response.ok,
        };
      }
    ),
  ],
});
```
</design_template>

<example name="feedback-server">
## Example: Feedback Storage Server

This server provides primitives for storing feedback. It does NOT decide how to categorize or organize feedback--that's the agent's job via the prompt.

```typescript
export const feedbackMcpServer = createSdkMcpServer({
  name: "feedback",
  version: "1.0.0",
  tools: [
    tool(
      "store_feedback",
      "Store a feedback item",
      {
        item: z.object({
          id: z.string(),
          author: z.string(),
          content: z.string(),
          importance: z.number().min(1).max(5),
          timestamp: z.string(),
          status: z.string().optional(),
          urls: z.array(z.string()).optional(),
          metadata: z.any().optional(),
        }).describe("Feedback item"),
      },
      async ({ item }) => {
        await db.feedback.insert(item);
        return {
          content: [{
            type: "text",
            text: `Stored feedback ${item.id} from ${item.author}`,
          }],
        };
      }
    ),

    tool(
      "list_feedback",
      "List feedback items",
      {
        limit: z.number().default(50),
        status: z.string().optional(),
      },
      async ({ limit, status }) => {
        const items = await db.feedback.list({ limit, status });
        return {
          content: [{
            type: "text",
            text: JSON.stringify(items, null, 2),
          }],
        };
      }
    ),

    tool(
      "update_feedback",
      "Update a feedback item",
      {
        id: z.string(),
        updates: z.object({
          status: z.string().optional(),
          importance: z.number().optional(),
          metadata: z.any().optional(),
        }),
      },
      async ({ id, updates }) => {
        await db.feedback.update(id, updates);
        return {
          content: [{ type: "text", text: `Updated ${id}` }],
        };
      }
    ),
  ],
});
```

The system prompt then tells the agent *how* to use these primitives:

```markdown
## Feedback Processing

When someone shares feedback:
1. Extract author, content, and any URLs
2. Rate importance 1-5 based on actionability
3. Store using feedback.store_feedback
4. If high importance (4-5), notify the channel

Use your judgment about importance ratings.
```
</example>

<principle name="dynamic-capability-discovery">
## Dynamic Capability Discovery vs Static Tool Mapping

**This pattern is specifically for agent-native apps** where you want the agent to have full access to an external API--the same access a user would have. It follows the core agent-native principle: "Whatever the user can do, the agent can do."

If you're building a constrained agent with limited capabilities, static tool mapping may be intentional. But for agent-native apps integrating with HealthKit, HomeKit, GraphQL, or similar APIs:

**Static Tool Mapping (Anti-pattern for Agent-Native):**
Build individual tools for each API capability. Always out of date, limits agent to only what you anticipated.

```typescript
// ❌ Static: Every API type needs a hardcoded tool
tool("read_steps", async ({ startDate, endDate }) => {
  return healthKit.query(HKQuantityType.stepCount, startDate, endDate);
});

tool("read_heart_rate", async ({ startDate, endDate }) => {
  return healthKit.query(HKQuantityType.heartRate, startDate, endDate);
});

tool("read_sleep", async ({ startDate, endDate }) => {
  return healthKit.query(HKCategoryType.sleepAnalysis, startDate, endDate);
});

// When HealthKit adds glucose tracking... you need a code change
```

**Dynamic Capability Discovery (Preferred):**
Build a meta-tool that discovers what's available, and a generic tool that can access anything.

```typescript
// ✅ Dynamic: Agent discovers and uses any capability

// Discovery tool - returns what's available at runtime
tool("list_available_capabilities", async () => {
  const quantityTypes = await healthKit.availableQuantityTypes();
  const categoryTypes = await healthKit.availableCategoryTypes();

  return {
    text: `Available health metrics:\n` +
          `Quantity types: ${quantityTypes.join(", ")}\n` +
          `Category types: ${categoryTypes.join(", ")}\n` +
          `\nUse read_health_data with any of these types.`
  };
});

// Generic access tool - type is a string, API validates
tool("read_health_data", {
  dataType: z.string(),  // NOT z.enum - let HealthKit validate
  startDate: z.string(),
  endDate: z.string(),
  aggregation: z.enum(["sum", "average", "samples"]).optional()
}, async ({ dataType, startDate, endDate, aggregation }) => {
  // HealthKit validates the type, returns helpful error if invalid
  const result = await healthKit.query(dataType, startDate, endDate, aggregation);
  return { text: JSON.stringify(result, null, 2) };
});
```

**When to Use Each Approach:**

| Dynamic (Agent-Native) | Static (Constrained Agent) |
|------------------------|---------------------------|
| Agent should access anything user can | Agent has intentionally limited scope |
| External API with many endpoints (HealthKit, HomeKit, GraphQL) | Internal domain with fixed operations |
| API evolves independently of your code | Tightly coupled domain logic |
| You want full action parity | You want strict guardrails |

**The agent-native default is Dynamic.** Only use Static when you're intentionally limiting the agent's capabilities.

**Complete Dynamic Pattern:**

```swift
// 1. Discovery tool: What can I access?
tool("list_health_types", "Get available health data types") { _ in
    let store = HKHealthStore()

    let quantityTypes = HKQuantityTypeIdentifier.allCases.map { $0.rawValue }
    let categoryTypes = HKCategoryTypeIdentifier.allCases.map { $0.rawValue }
    let characteristicTypes = HKCharacteristicTypeIdentifier.allCases.map { $0.rawValue }

    return ToolResult(text: """
        Available HealthKit types:

        ## Quantity Types (numeric values)
        \(quantityTypes.joined(separator: ", "))

        ## Category Types (categorical data)
        \(categoryTypes.joined(separator: ", "))

        ## Characteristic Types (user info)
        \(characteristicTypes.joined(separator: ", "))

        Use read_health_data or write_health_data with any of these.
        """)
}

// 2. Generic read: Access any type by name
tool("read_health_data", "Read any health metric", {
    dataType: z.string().describe("Type name from list_health_types"),
    startDate: z.string(),
    endDate: z.string()
}) { request in
    // Let HealthKit validate the type name
    guard let type = HKQuantityTypeIdentifier(rawValue: request.dataType)
                     ?? HKCategoryTypeIdentifier(rawValue: request.dataType) else {
        return ToolResult(
            text: "Unknown type: \(request.dataType). Use list_health_types to see available types.",
            isError: true
        )
    }

    let samples = try await healthStore.querySamples(type: type, start: startDate, end: endDate)
    return ToolResult(text: samples.formatted())
}

// 3. Context injection: Tell agent what's available in system prompt
func buildSystemPrompt() -> String {
    let availableTypes = healthService.getAuthorizedTypes()

    return """
    ## Available Health Data

    You have access to these health metrics:
    \(availableTypes.map { "- \($0)" }.joined(separator: "\n"))

    Use read_health_data with any type above. For new types not listed,
    use list_health_types to discover what's available.
    """
}
```

**Benefits:**
- Agent can use any API capability, including ones added after your code shipped
- API is the validator, not your enum definition
- Smaller tool surface (2-3 tools vs N tools)
- Agent naturally discovers capabilities by asking
- Works with any API that has introspection (HealthKit, GraphQL, OpenAPI)
</principle>

<principle name="crud-completeness">
## CRUD Completeness

Every data type the agent can create, it should be able to read, update, and delete. Incomplete CRUD = broken action parity.

**Anti-pattern: Create-only tools**
```typescript
// ❌ Can create but not modify or delete
tool("create_experiment", { hypothesis, variable, metric })
tool("write_journal_entry", { content, author, tags })
// User: "Delete that experiment" → Agent: "I can't do that"
```

**Correct: Full CRUD for each entity**
```typescript
// ✅ Complete CRUD
tool("create_experiment", { hypothesis, variable, metric })
tool("read_experiment", { id })
tool("update_experiment", { id, updates: { hypothesis?, status?, endDate? } })
tool("delete_experiment", { id })

tool("create_journal_entry", { content, author, tags })
tool("read_journal", { query?, dateRange?, author? })
tool("update_journal_entry", { id, content, tags? })
tool("delete_journal_entry", { id })
```

**The CRUD Audit:**
For each entity type in your app, verify:
- [ ] Create: Agent can create new instances
- [ ] Read: Agent can query/search/list instances
- [ ] Update: Agent can modify existing instances
- [ ] Delete: Agent can remove instances

If any operation is missing, users will eventually ask for it and the agent will fail.
</principle>

<principle name="tool-annotations">
## Tool Annotations

Every tool must declare its behavioral hints so clients can make safe decisions without reading implementation:

| Annotation | Values | Purpose |
|-----------|--------|---------|
| `readOnlyHint` | `true`/`false` | Tool does not modify state. Clients can auto-approve. |
| `destructiveHint` | `true`/`false` | Tool may irreversibly delete or overwrite data. |
| `idempotentHint` | `true`/`false` | Calling twice with same args produces same result. |
| `openWorldHint` | `true`/`false` | Tool interacts with external entities beyond the server's control. |

```typescript
tool("delete_item", "Delete an item by key", {
  key: z.string()
}, async ({ key }) => { /* ... */ }, {
  annotations: {
    readOnlyHint: false,
    destructiveHint: true,
    idempotentHint: true,
    openWorldHint: false,
  }
});
```
</principle>

<principle name="structured-output">
## Structured Output and Actionable Errors

Define `outputSchema` where possible so agents process structured data instead of parsing text. Use `structuredContent` in tool responses when returning complex data.

Error messages must guide agents toward solutions, not just report failure:

```typescript
// Wrong: opaque error
return { text: "Error: too many results", isError: true };

// Right: actionable error with recovery suggestion
return {
  text: "Query returned 5,000 results (limit 100). Try filter='active_only' to reduce results, or add a date range.",
  isError: true
};
```

**Pagination contract:** List endpoints must return `has_more`, `next_offset`, and `total_count`. Default page size 20-50 items. Never load all results into memory.
</principle>

<principle name="transport-selection">
## Transport Selection

| Transport | When to use |
|-----------|------------|
| **stdio** | Local/single-client tools, CLI integrations, same-machine only |
| **Streamable HTTP** | Remote/multi-client, production deployments, cross-network |
| **SSE** | Deprecated -- avoid for new servers |

For local HTTP servers, bind to `127.0.0.1` (not `0.0.0.0`) and validate the `Origin` header to prevent DNS rebinding attacks.
</principle>

<principle name="tool-naming-multi-server">
## Tool Naming for Multi-Server Environments

When multiple MCP servers coexist, prefix tool names with the service: `slack_send_message`, `github_create_issue`, `sentry_list_issues`. Without prefixes, tool name collisions across servers cause ambiguous routing.
</principle>

<principle name="evaluation-methodology">
## Evaluation: How to Prove an MCP Server Works

Do not ship an MCP server without a quality gate. Build a 10-question evaluation set before the server is merged:

- **10 human-readable Q/A pairs** -- each question is a realistic user ask (`"How many commits did Alice land on the payments module in Q3 2025?"`), each answer is a single string-comparable value (`"27"`, `"2024-08-14"`, `"kieran@example.com"`).
- **Multi-hop**: each question requires calling 2-3 tools in sequence (list → filter → aggregate). Single-tool questions don't stress the capability graph.
- **Read-only**: questions never mutate state. Every eval run must be reproducible.
- **Closed / historical data**: answers derive from data that doesn't change over time (a closed quarter, an archived project, a committed git range). Live data makes answers drift and the eval becomes noise.
- **Dozens of invocations per run**: the full eval should fire 20-40 tool calls. Servers that look fine on a single call often break on the 15th (rate limits, pagination edge cases, state pollution).

Run the eval in CI. Scoring is binary per question: exact string match or fail. Pass threshold: 9/10. Investigate any drop from a prior run -- eval regressions usually indicate a tool schema change broke client inference.

**What the eval catches that unit tests don't:**
- Vague tool descriptions that cause the agent to call the wrong tool
- Missing `outputSchema` fields that force the agent to parse error-prone text
- Pagination that works for page 1 but breaks on page 3
- Error messages that don't surface the recovery path, so the agent gives up

The eval is the single best proxy for "does a real agent successfully use this server?". Skipping it ships servers that pass unit tests and fail in practice.
</principle>

<checklist>
## MCP Tool Design Checklist

**Fundamentals:**
- [ ] Tool names describe capability, not use case
- [ ] Inputs are data, not decisions
- [ ] Outputs are rich (enough for agent to verify)
- [ ] CRUD operations are separate tools (not one mega-tool)
- [ ] No business logic in tool implementations
- [ ] Error states clearly communicated via `isError`
- [ ] Descriptions explain what the tool does, not when to use it
- [ ] Tool annotations set (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`)
- [ ] Error messages include recovery suggestions, not just failure descriptions
- [ ] List endpoints paginate with `has_more`, `next_offset`, `total_count`
- [ ] Multi-server tool names use service prefix (`service_action_resource`)
- [ ] 10 Q/A eval pairs defined before merge (read-only, multi-hop, closed-data); eval passes ≥ 9/10 in CI on every PR; regressions investigated before shipping. See the Evaluation principle above.

**Dynamic Capability Discovery (for agent-native apps):**
- [ ] For external APIs where agent should have full access, use dynamic discovery
- [ ] Include a `list_*` or `discover_*` tool for each API surface
- [ ] Use string inputs (not enums) when the API validates
- [ ] Inject available capabilities into system prompt at runtime
- [ ] Only use static tool mapping if intentionally limiting agent scope

**CRUD Completeness:**
- [ ] Every entity has create, read, update, delete operations
- [ ] Every UI action has a corresponding agent tool
- [ ] Test: "Can the agent undo what it just did?"
</checklist>
