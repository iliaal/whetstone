# Orchestration Patterns

## Pattern 1: Parallel Specialists (Leader Pattern)

Multiple specialists review code simultaneously:

```javascript
// 1. Create team
Teammate({ operation: "spawnTeam", team_name: "code-review" })

// 2. Spawn specialists in parallel (single message, multiple Task calls)
Task({
  team_name: "code-review",
  name: "security",
  subagent_type: "whetstone:review:security-sentinel",
  prompt: "Review the PR for security vulnerabilities. Focus on: SQL injection, XSS, auth bypass. Send findings to team-lead.",
  run_in_background: true
})

Task({
  team_name: "code-review",
  name: "performance",
  subagent_type: "whetstone:review:performance-oracle",
  prompt: "Review the PR for performance issues. Focus on: N+1 queries, memory leaks, slow algorithms. Send findings to team-lead.",
  run_in_background: true
})

Task({
  team_name: "code-review",
  name: "simplicity",
  subagent_type: "whetstone:review:code-simplicity-reviewer",
  prompt: "Review the PR for unnecessary complexity. Focus on: over-engineering, premature abstraction, YAGNI violations. Send findings to team-lead.",
  run_in_background: true
})

// 3. Wait for results (check inbox)
// cat ~/.claude/teams/code-review/inboxes/team-lead.json

// 4. Synthesize findings and cleanup
Teammate({ operation: "requestShutdown", target_agent_id: "security" })
Teammate({ operation: "requestShutdown", target_agent_id: "performance" })
Teammate({ operation: "requestShutdown", target_agent_id: "simplicity" })
// Wait for approvals...
Teammate({ operation: "cleanup" })
```

## Pattern 2: Pipeline (Sequential Dependencies)

Each stage depends on the previous:

```javascript
// 1. Create team and task pipeline
Teammate({ operation: "spawnTeam", team_name: "feature-pipeline" })

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
Task({
  team_name: "feature-pipeline",
  name: "researcher",
  subagent_type: "whetstone:research:best-practices-researcher",
  prompt: "Claim task #1, research best practices, complete it, send findings to team-lead. Then check for more work.",
  run_in_background: true
})

Task({
  team_name: "feature-pipeline",
  name: "implementer",
  subagent_type: "general-purpose",
  prompt: "Poll TaskList every 30 seconds. When task #3 unblocks, claim it and implement. Then complete and notify team-lead.",
  run_in_background: true
})

// Tasks auto-unblock as dependencies complete
```

## Pattern 3: Swarm (Self-Organizing)

Workers grab available tasks from a pool:

```javascript
// 1. Create team and task pool
Teammate({ operation: "spawnTeam", team_name: "file-review-swarm" })

// Create many independent tasks (no dependencies)
for (const file of ["auth.ts", "user.ts", "apiController.ts", "payment.ts"]) {
  TaskCreate({
    subject: `Review ${file}`,
    description: `Review ${file} for security and code quality issues`,
    activeForm: `Reviewing ${file}...`
  })
}

// 2. Spawn worker swarm
Task({
  team_name: "file-review-swarm",
  name: "worker-1",
  subagent_type: "general-purpose",
  prompt: `
    You are a swarm worker. Your job:
    1. Call TaskList to see available tasks
    2. Find a task with status 'pending' and no owner
    3. Claim it with TaskUpdate (set owner to your name)
    4. Do the work
    5. Mark it completed with TaskUpdate
    6. Send findings to team-lead via Teammate write
    7. Repeat until no tasks remain
  `,
  run_in_background: true
})

Task({
  team_name: "file-review-swarm",
  name: "worker-2",
  subagent_type: "general-purpose",
  prompt: `[Same prompt as worker-1]`,
  run_in_background: true
})

Task({
  team_name: "file-review-swarm",
  name: "worker-3",
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
const research = await Task({
  subagent_type: "whetstone:research:best-practices-researcher",
  description: "Research caching patterns",
  prompt: "Research best practices for implementing API caching. Include: cache invalidation strategies, Redis vs Memcached, cache key design."
})

// 2. Use research to guide implementation
Task({
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

Require plan approval before implementation:

```javascript
// 1. Create team
Teammate({ operation: "spawnTeam", team_name: "careful-work" })

// 2. Spawn architect with plan_mode_required
Task({
  team_name: "careful-work",
  name: "architect",
  subagent_type: "Plan",
  prompt: "Design an implementation plan for adding OAuth2 authentication",
  mode: "plan",  // Requires plan approval
  run_in_background: true
})

// 3. Wait for plan approval request
// You'll receive: {"type": "plan_approval_request", "from": "architect", "requestId": "plan-xxx", ...}

// 4. Review and approve/reject
Teammate({
  operation: "approvePlan",
  target_agent_id: "architect",
  request_id: "plan-xxx"
})
// OR
Teammate({
  operation: "rejectPlan",
  target_agent_id: "architect",
  request_id: "plan-xxx",
  feedback: "Please add rate limiting considerations"
})
```

## Pattern 6: Coordinated Multi-File Refactoring

```javascript
// 1. Create team for coordinated refactoring
Teammate({ operation: "spawnTeam", team_name: "refactor-auth" })

// 2. Create tasks with clear file boundaries
TaskCreate({
  subject: "Refactor User model",
  description: "Extract authentication methods to AuthenticatableUser concern",
  activeForm: "Refactoring User model..."
})

TaskCreate({
  subject: "Refactor Session controller",
  description: "Update to use new AuthenticatableUser concern",
  activeForm: "Refactoring Sessions..."
})

TaskCreate({
  subject: "Update specs",
  description: "Update all authentication specs for new structure",
  activeForm: "Updating specs..."
})

// Dependencies: specs depend on both refactors completing
TaskUpdate({ taskId: "3", addBlockedBy: ["1", "2"] })

// 3. Spawn workers for each task
Task({
  team_name: "refactor-auth",
  name: "model-worker",
  subagent_type: "general-purpose",
  prompt: "Claim task #1, refactor the User model, complete when done",
  run_in_background: true
})

Task({
  team_name: "refactor-auth",
  name: "controller-worker",
  subagent_type: "general-purpose",
  prompt: "Claim task #2, refactor the Session controller, complete when done",
  run_in_background: true
})

Task({
  team_name: "refactor-auth",
  name: "spec-worker",
  subagent_type: "general-purpose",
  prompt: "Wait for task #3 to unblock (when #1 and #2 complete), then update specs",
  run_in_background: true
})
```

---

## Complete Workflows

### Workflow 1: Full Code Review with Parallel Specialists

```javascript
// === STEP 1: Setup ===
Teammate({ operation: "spawnTeam", team_name: "pr-review-123", description: "Reviewing PR #123" })

// === STEP 2: Spawn reviewers in parallel ===
// (Send all these in a single message for parallel execution)
Task({
  team_name: "pr-review-123",
  name: "security",
  subagent_type: "whetstone:review:security-sentinel",
  prompt: `Review PR #123 for security vulnerabilities.

  Focus on:
  - SQL injection
  - XSS vulnerabilities
  - Authentication/authorization bypass
  - Sensitive data exposure

  When done, send your findings to team-lead using:
  Teammate({ operation: "write", target_agent_id: "team-lead", value: "Your findings here" })`,
  run_in_background: true
})

Task({
  team_name: "pr-review-123",
  name: "perf",
  subagent_type: "whetstone:review:performance-oracle",
  prompt: `Review PR #123 for performance issues.

  Focus on:
  - N+1 queries
  - Missing indexes
  - Memory leaks
  - Inefficient algorithms

  Send findings to team-lead when done.`,
  run_in_background: true
})

Task({
  team_name: "pr-review-123",
  name: "arch",
  subagent_type: "whetstone:review:architecture-strategist",
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
// cat ~/.claude/teams/pr-review-123/inboxes/team-lead.json

// === STEP 4: Synthesize findings ===
// Combine all reviewer findings into a cohesive report

// === STEP 5: Cleanup ===
Teammate({ operation: "requestShutdown", target_agent_id: "security" })
Teammate({ operation: "requestShutdown", target_agent_id: "perf" })
Teammate({ operation: "requestShutdown", target_agent_id: "arch" })
// Wait for approvals...
Teammate({ operation: "cleanup" })
```

### Workflow 2: Research -> Plan -> Implement -> Test Pipeline

```javascript
// === SETUP ===
Teammate({ operation: "spawnTeam", team_name: "feature-oauth" })

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
Task({
  team_name: "feature-oauth",
  name: "researcher",
  subagent_type: "whetstone:research:best-practices-researcher",
  prompt: "Claim task #1. Research OAuth2 best practices, compare providers, document findings. Mark task complete and send summary to team-lead.",
  run_in_background: true
})

Task({
  team_name: "feature-oauth",
  name: "planner",
  subagent_type: "Plan",
  prompt: "Wait for task #2 to unblock. Read research from task #1. Create detailed implementation plan. Mark complete and send plan to team-lead.",
  run_in_background: true
})

Task({
  team_name: "feature-oauth",
  name: "implementer",
  subagent_type: "general-purpose",
  prompt: "Wait for task #3 to unblock. Read plan from task #2. Implement OAuth2 authentication. Mark complete when done.",
  run_in_background: true
})

Task({
  team_name: "feature-oauth",
  name: "tester",
  subagent_type: "general-purpose",
  prompt: "Wait for task #4 to unblock. Write comprehensive tests for the OAuth implementation. Run tests. Mark complete with results.",
  run_in_background: true
})

Task({
  team_name: "feature-oauth",
  name: "reviewer",
  subagent_type: "whetstone:review:security-sentinel",
  prompt: "Wait for task #5 to unblock. Review the complete OAuth implementation for security. Send final assessment to team-lead.",
  run_in_background: true
})

// Pipeline auto-progresses as each stage completes
```

### Workflow 3: Self-Organizing Code Review Swarm

```javascript
// === SETUP ===
Teammate({ operation: "spawnTeam", team_name: "codebase-review" })

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
   - Send findings to team-lead via Teammate write
   - Go back to step 1
4. If no tasks available:
   - Send idle notification to team-lead
   - Wait 30 seconds
   - Try again (up to 3 times)
   - If still no tasks, exit

Replace YOUR_NAME with your actual agent name from $CLAUDE_CODE_AGENT_NAME.
`

// Spawn 3 workers
Task({ team_name: "codebase-review", name: "worker-1", subagent_type: "general-purpose", prompt: swarmPrompt, run_in_background: true })
Task({ team_name: "codebase-review", name: "worker-2", subagent_type: "general-purpose", prompt: swarmPrompt, run_in_background: true })
Task({ team_name: "codebase-review", name: "worker-3", subagent_type: "general-purpose", prompt: swarmPrompt, run_in_background: true })

// Workers self-organize: race to claim tasks, naturally load-balance
// Monitor progress with TaskList() or by reading inbox
```
