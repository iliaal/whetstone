<overview>
Self-modification is the advanced tier of agent native engineering: agents that can evolve their own code, prompts, and behavior. Not required for every app, but a big part of the future.

This is the logical extension of "whatever the developer can do, the agent can do."
</overview>

<why_self_modification>
## Why Self-Modification?

Traditional software is static--it does what you wrote, nothing more. Self-modifying agents can:

- **Fix their own bugs** - See an error, patch the code, restart
- **Add new capabilities** - User asks for something new, agent implements it
- **Evolve behavior** - Learn from feedback and adjust prompts
- **Deploy themselves** - Push code, trigger builds, restart

The agent becomes a living system that improves over time, not frozen code.
</why_self_modification>

<capabilities>
## What Self-Modification Enables

**Code modification:**
- Read and understand source files
- Write fixes and new features
- Commit and push to version control
- Trigger builds and verify they pass

**Prompt evolution:**
- Edit the system prompt based on feedback
- Add new features as prompt sections
- Refine judgment criteria that aren't working

**Infrastructure control:**
- Pull latest code from upstream
- Merge from other branches/instances
- Restart after changes
- Roll back if something breaks

**Site/output generation:**
- Generate and maintain websites
- Create documentation
- Build dashboards from data
</capabilities>

<guardrails>
## Required Guardrails

Self-modification is powerful. It needs safety mechanisms.

**Approval gates for code changes:**
Use the [approval-gates pattern](./architecture-patterns.md): `write_file` proposes a revisioned draft for protected paths; trusted orchestration applies only the exact approved content and destination. Ordinary writes still require the caller's workspace grant and revision-conditional persistence. A chat reply of "yes" must resolve to the specific draft shown to that authenticated user.

**Checkpoint an exclusive deployment checkout before changes:**

Run this recipe only in a dedicated deployment checkout with an exclusive deployment lock held for the whole operation. Refuse dirty or untracked user files; never stash a shared checkout. Build into that checkout's generated output, with no external side effects. The serving process must continue using the prior immutable release until restart. If the application reads mutable build files at runtime, use separate release directories and switch a release pointer instead.

```typescript
tool("self_deploy", async () => {
  if (runGit("status --porcelain --untracked-files=all").trim()) {
    return { text: "Deployment checkout is dirty; preserve its changes", isError: true };
  }
  const previousCommit = runGit("rev-parse HEAD").trim();
  runGit("fetch origin");
  runGit("merge --ff-only origin/main");
  try {
    runCommand("npm run build", { timeout: 120000 });
  } catch (error) {
    try {
      runGit(`reset --hard ${previousCommit}`);
      runCommand("npm run build", { timeout: 120000 });
    } catch (rollbackError) {
      return { text: `Deploy failed; rollback failed: ${rollbackError}`, isError: true };
    }
    return { text: "Build failed; previous source and build restored; no restart", isError: true };
  }
  scheduleRestart();
  return { text: "Build passed; restart scheduled, runtime health not yet verified" };
});
```

**Build verification:**

The command wrappers above must throw on nonzero exit. A successful merge has no active merge to abort. Restore the recorded commit and rebuild its generated artifacts before reporting rollback, and report rollback failure distinctly. Exercise both build failure after a successful fast-forward and failure while rebuilding the prior revision. Check the running revision and application health after restart before claiming deployment success.

**Health checks after restart:**
The trusted deployment controller persists the expected immutable release revision before restart. Probe the serving application's own endpoint, which reports the revision loaded at process startup and checks required dependencies.

```typescript
type HealthEvidence = {
  status: "healthy" | "unhealthy" | "unverified";
  expectedRevision: string;
  servedRevision?: string;
  reason: string;
};

async function checkDeployment(
  healthURL: URL,
  expectedRevision: string,
): Promise<HealthEvidence> {
  if (!expectedRevision) throw new Error("Expected release revision is required");
  try {
    const response = await fetch(healthURL, {
      signal: AbortSignal.timeout(5000),
      redirect: "error",
    });
    const payload: unknown = await response.json();
    if (typeof payload !== "object" || payload === null) {
      throw new Error("Health endpoint returned no evidence object");
    }
    const evidence = payload as Record<string, unknown>;
    if (typeof evidence.revision !== "string" ||
        typeof evidence.healthy !== "boolean" ||
        typeof evidence.buildPresent !== "boolean") {
      throw new Error("Health evidence is incomplete");
    }
    const healthy = response.ok && evidence.healthy && evidence.buildPresent &&
      evidence.revision === expectedRevision;
    return {
      status: healthy ? "healthy" : "unhealthy",
      expectedRevision,
      servedRevision: evidence.revision,
      reason: healthy ? "Application checks passed for the expected release"
        : "Application checks failed, build is missing, or served revision differs",
    };
  } catch {
    return {
      status: "unverified",
      expectedRevision,
      reason: "Serving application health evidence could not be verified",
    };
  }
}
```

Bind the endpoint to the configured deployment target; do not accept an arbitrary agent-supplied URL or expected revision. Keep raw upstream and library diagnostics in operator-controlled logs rather than returned health evidence. Uptime, git status, and a local build file are diagnostics, not evidence of the serving application's health. Exercise the endpoint against the expected release before announcing deployment success.
</guardrails>

<git_architecture>
## Git-Based Self-Modification

Use git as the foundation for self-modification. It provides:
- Version history (rollback capability)
- Branching (experiment safely)
- Merge (sync with other instances)
- Push/pull (deploy and collaborate)

**Essential git tools:**
```typescript
tool("status", "Show git status", {}, ...);
tool("diff", "Show file changes", { path: z.string().optional() }, ...);
tool("log", "Show commit history", { count: z.number() }, ...);
tool("commit_code", "Commit code changes", { message: z.string() }, ...);
tool("git_push", "Push to GitHub", { branch: z.string().optional() }, ...);
tool("pull", "Pull from GitHub", { source: z.enum(["main", "instance"]) }, ...);
tool("rollback", "Revert recent commits", { commits: z.number() }, ...);
```

**Multi-instance architecture:**
```
main                      # Shared code
├── instance/bot-a       # Instance A's branch
├── instance/bot-b       # Instance B's branch
└── instance/bot-c       # Instance C's branch
```

Each instance can:
- Pull updates from main
- Push improvements back to main (via PR)
- Sync features from other instances
- Maintain instance-specific config
</git_architecture>

<prompt_evolution>
## Self-Modifying Prompts

The system prompt is a file the agent can read and write.

```typescript
// Agent can read its own prompt
tool("read_file", ...);  // Can read src/prompts/system.md

// Agent can propose changes
tool("write_file", ...);  // Can write to src/prompts/system.md (with approval)
```

**System prompt as living document:**
```markdown
## Feedback Processing

When someone shares feedback:
1. Acknowledge warmly
2. Rate importance 1-5
3. Store using feedback tools

<!-- Note to self: Video walkthroughs should always be 4-5,
     learned this from Dan's feedback on 2024-12-07 -->
```

The agent can:
- Add notes to itself
- Refine judgment criteria
- Add new feature sections
- Document edge cases it learned
</prompt_evolution>

<when_to_use>
## When to Implement Self-Modification

**Good candidates:**
- Long-running autonomous agents
- Agents that need to adapt to feedback
- Systems where behavior evolution is valuable
- Internal tools where rapid iteration matters

**Not necessary for:**
- Simple single-task agents
- Highly regulated environments
- Systems where behavior must be auditable
- One-off or short-lived agents

Start with a non-self-modifying prompt-native agent. Add self-modification when you need it.
</when_to_use>

<example_tools>
## Complete Self-Modification Toolset

```typescript
const selfMcpServer = createSdkMcpServer({
  name: "self",
  version: "1.0.0",
  tools: [
    // FILE OPERATIONS
    tool("read_file", "Read any project file", { path: z.string() }, ...),
    tool("write_file", "Write a file (code requires approval)", { path, content }, ...),
    tool("list_files", "List directory contents", { path: z.string() }, ...),
    tool("search_code", "Search for patterns", { pattern: z.string() }, ...),

    // APPROVAL WORKFLOW
    tool("apply_pending", "Request application of one approved draft", {
      draftId: z.string(), revision: z.number().int().positive(),
    }, ...),
    tool("get_pending", "Show pending changes", {}, ...),
    tool("clear_pending", "Discard pending changes", {}, ...),

    // RESTART
    tool("restart", "Rebuild and restart", {}, ...),
    tool("health_check", "Check if bot is healthy", {}, ...),
  ],
});

const gitMcpServer = createSdkMcpServer({
  name: "git",
  version: "1.0.0",
  tools: [
    // STATUS
    tool("status", "Show git status", {}, ...),
    tool("diff", "Show changes", { path: z.string().optional() }, ...),
    tool("log", "Show history", { count: z.number() }, ...),

    // COMMIT & PUSH
    tool("commit_code", "Commit code changes", { message: z.string() }, ...),
    tool("git_push", "Push to GitHub", { branch: z.string().optional() }, ...),

    // SYNC
    tool("pull", "Pull from upstream", { source: z.enum(["main", "instance"]) }, ...),
    tool("self_deploy", "Pull, build, restart", { source: z.enum(["main", "instance"]) }, ...),

    // SAFETY
    tool("rollback", "Revert commits", { commits: z.number() }, ...),
    tool("health_check", "Detailed health report", {}, ...),
  ],
});
```
</example_tools>

<checklist>
## Self-Modification Checklist

Before enabling self-modification:
- [ ] Git-based version control set up
- [ ] Approval gates for code changes
- [ ] Build verification before restart
- [ ] Rollback mechanism available
- [ ] Health check endpoint
- [ ] Instance identity configured

When implementing:
- [ ] Agent can read all project files
- [ ] Agent can write files (with appropriate approval)
- [ ] Agent can commit and push
- [ ] Agent can pull updates
- [ ] Agent can restart itself
- [ ] Agent can roll back if needed
</checklist>
