# Quick Start: Build an Agent-Native Feature

**Step 1: Define atomic tools**
```typescript
const tools = [
  tool("read_file", "Read any file", { path: z.string() }, ...),
  tool("write_file", "Write any file", { path: z.string(), content: z.string() }, ...),
  tool("list_files", "List directory", { path: z.string() }, ...),
  tool("complete_task", "Report terminal task state", {
    summary: z.string(),
    status: z.enum(["success", "partial", "blocked"]),
  }, ...),
];
```

**Step 2: Write behavior in the system prompt**
```markdown
## Your Responsibilities
When organizing content:
1. Read existing files to understand the structure
2. Analyze what organization makes sense
3. Create/move files using your tools
4. Use your judgment about layout and formatting
5. Call complete_task with success, partial, or blocked, and summarize outcomes and remaining work

You decide the structure. Make it good.
```

**Step 3: Let the agent work in a loop**
```typescript
const result = await agent.run({
  prompt: userMessage,
  tools: tools,
  systemPrompt: systemPrompt,
  // A terminal call stops the loop; application-owned checks must accept success
});
```

Implement terminal-state preservation and acceptance checks using [agent-execution-patterns.md](./agent-execution-patterns.md). Stopping the loop or receiving a summary alone does not establish successful completion.
