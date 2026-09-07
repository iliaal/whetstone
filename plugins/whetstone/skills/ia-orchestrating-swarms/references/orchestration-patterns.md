# Orchestration Patterns

> When to read: when designing a multi-agent workflow shape — parallel specialists, sequential pipeline, hub-and-spoke, or hierarchical sub-teams.

Claude examples below use the active `Agent`, `SendMessage`, and optional Task tools. For named teammates, first confirm an interactive session with agent teams enabled. Team setup and session cleanup are automatic; use the actual session-derived paths. Supply the full dispatch contract and fresh reviewer context with each example. Task IDs are illustrative: use IDs returned by TaskCreate. If Task tools are absent, the orchestrator tracks dependencies and dispatches ready work through messages.

## Pattern 1: Parallel Specialists (Leader Pattern)

Multiple specialists review code simultaneously:

```javascript
// 1. Prepare the work items in the current session

// 2. Spawn specialists without waiting for earlier workers to finish
Agent({
  name: "security",
  description: "Assigned security work",
  subagent_type: "whetstone:ia-security-sentinel",
  prompt: "Review the PR for security vulnerabilities. Focus on: SQL injection, XSS, auth bypass. Send findings to team-lead.",
  run_in_background: true
})

Agent({
  name: "performance",
  description: "Assigned performance work",
  subagent_type: "whetstone:ia-performance-oracle",
  prompt: "Review the PR for performance issues. Focus on: N+1 queries, memory leaks, slow algorithms. Send findings to team-lead.",
  run_in_background: true
})

Agent({
  name: "simplicity",
  description: "Assigned simplicity work",
  subagent_type: "whetstone:ia-code-simplicity-reviewer",
  prompt: "Review the PR for unnecessary complexity. Focus on: over-engineering, premature abstraction, YAGNI violations. Send findings to team-lead.",
  run_in_background: true
})

// 3. Wait for results (check inbox)
// Use the current session's delivered messages and runtime-provided paths

// 4. Synthesize findings and request shutdown
SendMessage({ to: "security", message: { type: "shutdown_request", reason: "Assigned work complete" } })
SendMessage({ to: "performance", message: { type: "shutdown_request", reason: "Assigned work complete" } })
SendMessage({ to: "simplicity", message: { type: "shutdown_request", reason: "Assigned work complete" } })
// Wait for shutdown acknowledgements; session cleanup is automatic.
```

## Pattern 2: Pipeline (Sequential Dependencies)

Each stage depends on the previous:

```javascript
// 1. Prepare the work items in the current session

TaskCreate({ subject: "Research", description: "Research best practices for the feature", activeForm: "Researching..." })
TaskCreate({ subject: "Plan", description: "Create implementation plan based on research", activeForm: "Planning..." })
TaskCreate({ subject: "Implement", description: "Implement the feature according to plan", activeForm: "Implementing..." })
TaskCreate({ subject: "Test", description: "Write and run tests for the implementation", activeForm: "Testing..." })
TaskCreate({ subject: "Review", description: "Final code review before merge", activeForm: "Reviewing..." })

// Set up sequential dependencies
TaskUpdate({ taskId: "2", addBlockedBy: ["1"] })
TaskUpdate({ taskId: "3", addBlockedBy: ["2"] })
TaskUpdate({ taskId: "4", addBlockedBy: ["3"] })
TaskUpdate({ taskId: "5", addBlockedBy: ["4"] })

// 2. Spawn workers that claim and complete tasks
Agent({
  name: "researcher",
  description: "Assigned researcher work",
  subagent_type: "whetstone:ia-best-practices-researcher",
  prompt: "Claim task #1, research best practices, complete it, send findings to team-lead. Then check for more work.",
  run_in_background: true
})

Agent({
  name: "implementer",
  description: "Assigned implementer work",
  subagent_type: "general-purpose",
  prompt: "Poll TaskList every 30 seconds. When task #3 unblocks, claim it and implement. Then complete and notify team-lead.",
  run_in_background: true
})

// Tasks auto-unblock as dependencies complete
```

## Pattern 3: Swarm (Self-Organizing)

Workers grab available tasks from a pool:

```javascript
// 1. Prepare the work items in the current session

// Create many independent tasks (no dependencies)
for (const file of ["auth.ts", "user.ts", "apiController.ts", "payment.ts"]) {
  TaskCreate({
    subject: `Review ${file}`,
    description: `Review ${file} for security and code quality issues`,
    activeForm: `Reviewing ${file}...`
  })
}

// 2. Spawn worker swarm
Agent({
  name: "worker-1",
  description: "Assigned worker-1 work",
  subagent_type: "general-purpose",
  prompt: `
    You are a swarm worker. Your job:
    1. Call TaskList to see available tasks
    2. Find a task with status 'pending' and no owner
    3. Claim it with TaskUpdate (set owner to your name)
    4. Do the work
    5. Mark it completed with TaskUpdate
    6. Send findings to team-lead via SendMessage
    7. Repeat until no tasks remain
  `,
  run_in_background: true
})

Agent({
  name: "worker-2",
  description: "Assigned worker-2 work",
  subagent_type: "general-purpose",
  prompt: `[Same prompt as worker-1]`,
  run_in_background: true
})

Agent({
  name: "worker-3",
  description: "Assigned worker-3 work",
  subagent_type: "general-purpose",
  prompt: `[Same prompt as worker-1]`,
  run_in_background: true
})

// Workers race to claim tasks, naturally load-balance
```

## Pattern 4: Research + Implementation

Research first, then implement:

```javascript
// 1. Research phase (synchronous, returns results)
const research = await Agent({
  subagent_type: "whetstone:ia-best-practices-researcher",
  description: "Research caching patterns",
  prompt: "Research best practices for implementing API caching. Include: cache invalidation strategies, Redis vs Memcached, cache key design."
})

// 2. Use research to guide implementation
Agent({
  subagent_type: "general-purpose",
  description: "Implement caching",
  prompt: `
    Implement API caching based on this research:

    ${research.content}

    Focus on the usersController.ts endpoints.
  `
})
```

## Pattern 5: Plan Approval Workflow

Require a reviewed plan before implementation. The runtime's automatic teammate plan approval is not this gate.

1. Dispatch a read-only planner for the complete requirements and acceptance criteria.
2. Inspect its returned plan, resolve contradictions, and obtain any genuinely missing user decision.
3. Dispatch implementation only after the review passes and the action is authorized.

```javascript
Agent({
  subagent_type: "Plan",
  description: "Plan authentication changes",
  prompt: "Design an OAuth2 implementation plan including failure recovery and rate limiting. Read-only: return the plan and unresolved decisions, then stop."
})
```

After reviewing the returned artifact, send a separate implementation brief with the accepted plan and owned files. Do not use an automatic plan-mode transition as proof of review. Legacy protocol responses, if the active schema exposes them, are documented in [teammate-operations.md](./teammate-operations.md).

## Pattern 6: Coordinated Multi-File Refactoring

```javascript
// 1. Prepare the work items in the current session

// 2. Create tasks with clear file boundaries
TaskCreate({
  subject: "Refactor User model",
  description: "Extract authentication methods to an `AuthenticatableUser` trait/mixin (src/lib/authenticatableUser.ts)",
  activeForm: "Refactoring User model..."
})

TaskCreate({
  subject: "Refactor Session controller",
  description: "Update src/controllers/api/v1/sessionsController.ts to use the new `AuthenticatableUser` trait/mixin",
  activeForm: "Refactoring Sessions..."
})

TaskCreate({
  subject: "Update tests",
  description: "Update all authentication tests for new structure",
  activeForm: "Updating tests..."
})

// Dependencies: specs depend on both refactors completing
TaskUpdate({ taskId: "3", addBlockedBy: ["1", "2"] })

// 3. Spawn workers for each task
Agent({
  name: "model-worker",
  description: "Assigned model-worker work",
  subagent_type: "general-purpose",
  prompt: "Claim task #1, refactor the User model, complete when done",
  run_in_background: true
})

Agent({
  name: "controller-worker",
  description: "Assigned controller-worker work",
  subagent_type: "general-purpose",
  prompt: "Claim task #2, refactor the Session controller, complete when done",
  run_in_background: true
})

Agent({
  name: "test-worker",
  description: "Assigned test-worker work",
  subagent_type: "general-purpose",
  prompt: "Wait for task #3 to unblock (when #1 and #2 complete), then update tests",
  run_in_background: true
})
```

---

## Complete Workflows

### Workflow 1: Full Code Review with Parallel Specialists

```javascript
// === STEP 1: Setup ===

// === STEP 2: Spawn reviewers in parallel ===
// (Send all these in a single message for parallel execution)
Agent({
  name: "security",
  description: "Assigned security work",
  subagent_type: "whetstone:ia-security-sentinel",
  prompt: `Review PR #123 for security vulnerabilities.

  Focus on:
  - SQL injection
  - XSS vulnerabilities
  - Authentication/authorization bypass
  - Sensitive data exposure

  When done, send your findings to team-lead using:
  SendMessage({ to: "team-lead", message: "Your findings here" })`,
  run_in_background: true
})

Agent({
  name: "perf",
  description: "Assigned perf work",
  subagent_type: "whetstone:ia-performance-oracle",
  prompt: `Review PR #123 for performance issues.

  Focus on:
  - N+1 queries
  - Missing indexes
  - Memory leaks
  - Inefficient algorithms

  Send findings to team-lead when done.`,
  run_in_background: true
})

Agent({
  name: "arch",
  description: "Assigned arch work",
  subagent_type: "whetstone:ia-architecture-strategist",
  prompt: `Review PR #123 for architectural concerns.

  Focus on:
  - Design pattern adherence
  - SOLID principles
  - Separation of concerns
  - Testability

  Send findings to team-lead when done.`,
  run_in_background: true
})

// === STEP 3: Monitor and collect results ===
// Poll inbox or wait for idle notifications
// Use the current session's delivered messages and runtime-provided paths

// === STEP 4: Synthesize findings ===
// Combine all reviewer findings into a cohesive report

// === STEP 5: Request shutdown ===
SendMessage({ to: "security", message: { type: "shutdown_request", reason: "Assigned work complete" } })
SendMessage({ to: "perf", message: { type: "shutdown_request", reason: "Assigned work complete" } })
SendMessage({ to: "arch", message: { type: "shutdown_request", reason: "Assigned work complete" } })
// Wait for shutdown acknowledgements; session cleanup is automatic.
```

### Workflow 2: Research -> Plan -> Implement -> Test Pipeline

```javascript
// === SETUP ===

// === CREATE PIPELINE ===
TaskCreate({ subject: "Research OAuth providers", description: "Research OAuth2 best practices and compare providers (Google, GitHub, Auth0)", activeForm: "Researching OAuth..." })
TaskCreate({ subject: "Create implementation plan", description: "Design OAuth implementation based on research findings", activeForm: "Planning..." })
TaskCreate({ subject: "Implement OAuth", description: "Implement OAuth2 authentication according to plan", activeForm: "Implementing OAuth..." })
TaskCreate({ subject: "Write tests", description: "Write comprehensive tests for OAuth implementation", activeForm: "Writing tests..." })
TaskCreate({ subject: "Final review", description: "Review complete implementation for security and quality", activeForm: "Final review..." })

// Set dependencies
TaskUpdate({ taskId: "2", addBlockedBy: ["1"] })
TaskUpdate({ taskId: "3", addBlockedBy: ["2"] })
TaskUpdate({ taskId: "4", addBlockedBy: ["3"] })
TaskUpdate({ taskId: "5", addBlockedBy: ["4"] })

// === SPAWN SPECIALIZED WORKERS ===
Agent({
  name: "researcher",
  description: "Assigned researcher work",
  subagent_type: "whetstone:ia-best-practices-researcher",
  prompt: "Claim task #1. Research OAuth2 best practices, compare providers, document findings. Mark task complete and send summary to team-lead.",
  run_in_background: true
})

Agent({
  name: "planner",
  description: "Assigned planner work",
  subagent_type: "Plan",
  prompt: "Wait for task #2 to unblock. Read research from task #1. Create detailed implementation plan. Mark complete and send plan to team-lead.",
  run_in_background: true
})

Agent({
  name: "implementer",
  description: "Assigned implementer work",
  subagent_type: "general-purpose",
  prompt: "Wait for task #3 to unblock. Read plan from task #2. Implement OAuth2 authentication. Mark complete when done.",
  run_in_background: true
})

Agent({
  name: "tester",
  description: "Assigned tester work",
  subagent_type: "general-purpose",
  prompt: "Wait for task #4 to unblock. Write comprehensive tests for the OAuth implementation. Run tests. Mark complete with results.",
  run_in_background: true
})

Agent({
  name: "reviewer",
  description: "Assigned reviewer work",
  subagent_type: "whetstone:ia-security-sentinel",
  prompt: "Wait for task #5 to unblock. Review the complete OAuth implementation for security. Send final assessment to team-lead.",
  run_in_background: true
})

// Pipeline auto-progresses as each stage completes
```

### Workflow 3: Self-Organizing Code Review Swarm

```javascript
// === SETUP ===

// === CREATE TASK POOL (all independent, no dependencies) ===
const filesToReview = [
  "src/models/user.ts",
  "src/models/payment.ts",
  "src/controllers/api/v1/usersController.ts",
  "src/controllers/api/v1/paymentsController.ts",
  "src/services/paymentProcessor.ts",
  "src/services/notificationService.ts",
  "src/lib/encryptionHelper.ts"
]

for (const file of filesToReview) {
  TaskCreate({
    subject: `Review ${file}`,
    description: `Review ${file} for security vulnerabilities, code quality, and performance issues`,
    activeForm: `Reviewing ${file}...`
  })
}

// === SPAWN WORKER SWARM ===
const swarmPrompt = `
You are a swarm worker. Your job is to continuously process available tasks.

LOOP:
1. Call TaskList() to see available tasks
2. Find a task that is:
   - status: 'pending'
   - no owner
   - not blocked
3. If found:
   - Claim it: TaskUpdate({ taskId: "X", owner: "YOUR_NAME" })
   - Start it: TaskUpdate({ taskId: "X", status: "in_progress" })
   - Do the review work
   - Complete it: TaskUpdate({ taskId: "X", status: "completed" })
   - Send findings to team-lead via SendMessage
   - Go back to step 1
4. If no tasks available:
   - Send idle notification to team-lead
   - Wait 30 seconds
   - Try again (up to 3 times)
   - If still no tasks, exit

Replace YOUR_NAME with the worker name explicitly supplied in its dispatch.
`

// Spawn 3 workers
Agent({ name: "worker-1", description: "Assigned worker-1 work", subagent_type: "general-purpose", prompt: swarmPrompt, run_in_background: true })
Agent({ name: "worker-2", description: "Assigned worker-2 work", subagent_type: "general-purpose", prompt: swarmPrompt, run_in_background: true })
Agent({ name: "worker-3", description: "Assigned worker-3 work", subagent_type: "general-purpose", prompt: swarmPrompt, run_in_background: true })

// Workers self-organize: race to claim tasks, naturally load-balance
// Monitor progress with TaskList() or by reading inbox
```

## Delivery and credit discipline

Keep the overwhelming majority of open implementation units tied to runnable capability. A coordination, validation, or operations unit must name the capability or observed defect class it gates. Use the ratio as a drift signal, never as a quota to game.

Make closable units vertical: implementation and its tests ship together. Internal steps may separate types, code, and tests for sequencing, but they do not earn separate closures. A trivial commit, placeholder scaffold, refusal-only path, or stub that merely type-checks is not delivered capability.

Claim the highest-priority ready capability that the worker can actually complete. Surface stale high-priority work instead of repeatedly selecting low-risk units. Only the role assigned closure authority may close shared work; never close a peer's unit merely to release dependents.

After each wave, compare runnable units delivered with coordination, review, and governance rounds consumed. If orchestration activity grows while the deliverable count is flat, freeze the machinery at its current sufficient state and redirect the next wave to the deliverable.

## One implementation unit per worker

A worker dispatched to implement a unit gets a context carrying no prior implementation unit, and it is retired once that unit is integrated -- never retasked onto a second unit, never held as an idle pool. The same handle may continue or recover *its own* unit (the crash-relaunch path in the main skill), but a worker that has already reasoned about one unit's constraints carries them into the next as unstated assumptions.

This binds implementation dispatch on the subagent surface only. The persistent teammate model is deliberately long-lived and unaffected, as is the mode-to-mode carry-forward in Context Carry-Forward.

Invoke an explicit close or release only where the harness exposes one and assigns that action to the caller. Clean up an isolated workspace only after confirming the unit's work was integrated -- never infer a cleanup command from the provider name.

## Coordination models

| Aspect | Stateless (copy-paste outputs) | Stateful (file ownership + dependencies) |
|--------|-------------------------------|------------------------------------------|
| How agents share state | Leader copies full outputs between prompts | Agents read/write shared task files, claim ownership |
| Best for | Short pipelines, 2-3 agents, sequential handoffs | Parallel work, 4+ agents, complex dependency graphs |
| Failure mode | Context grows linearly with agent count | Concurrent modification conflicts |
| Mitigation | Summarize before passing (keep essentials, drop navigation) | Use worktrees or exclusive file ownership per agent |

For most work, start with stateless handoffs. Graduate to stateful coordination only when parallelism provides a real speedup and either worktree isolation or every shared-tree wave condition prevents file conflicts.
