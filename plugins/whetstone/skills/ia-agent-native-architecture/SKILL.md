---
name: ia-agent-native-architecture
class: meta
description: >-
  Design agent-native applications where agents replace UI users as the primary
  actor. Use when designing MCP tools, agent-loop architectures, system prompt
  design, hooks policy, shared-workspace file patterns, or self-modifying agent
  systems.
---

# Agent-Native Architecture

## Working rules

- Keep authority, scope, approval, and runtime isolation in trusted orchestration; prompts alone cannot enforce them.
- Provide explicit completion and partial-progress signals, durable state, and observable action results.
- Validate capabilities with real tasks, including failure and interruption paths; do not infer improvement from elapsed usage.
- Use the selected topic's references and the architecture checklist to produce a concrete design with evidence and unresolved constraints.

## Core Principles

Five principles govern agent-native design. For detailed explanations, examples, and test criteria, see [core-principles.md](./references/core-principles.md).

| Principle | One-line test |
|-----------|--------------|
| **Parity** | Can the agent achieve every outcome the UI allows? |
| **Granularity** | Changing behavior means editing prose, not refactoring code |
| **Composability** | Can a feature be added by writing a new prompt, without new code? |
| **Emergent Capability** | Can the agent handle open-ended requests it wasn't designed for? |
| **Improvement Over Time** | Does the app work better after a month, even without code changes? |


## Focus Area Selection

1. **Design architecture** - Plan a new agent-native system from scratch
2. **Files & workspace** - Use files as the universal interface, shared workspace patterns
3. **Tool design** - Build primitive tools, dynamic capability discovery, CRUD completeness
4. **Domain tools** - Know when to add domain tools vs stay with primitives
5. **Execution patterns** - Completion signals, partial completion, context limits
6. **System prompts** - Define agent behavior in prompts, judgment criteria
7. **Context injection** - Inject runtime app state into agent prompts
8. **Action parity** - Ensure agents can do everything users can do
9. **Self-modification** - Enable agents to safely evolve themselves
10. **Product design** - Progressive disclosure, latent demand, approval patterns
11. **Mobile patterns** - iOS storage, background execution, checkpoint/resume
12. **Testing** - Test agent-native apps for capability and parity
13. **Refactoring** - Make existing code more agent-native
14. **Anti-patterns** - Common mistakes and how to avoid them
15. **Success criteria** - Verify your architecture is agent-native
16. **Hooks patterns** - Hook events, decision control, MCP matchers, async hooks

**Wait for response before proceeding.**


## Reference Routing

| Response | Action |
|----------|--------|
| 1, "design", "architecture", "plan" | Read [architecture-patterns.md](./references/architecture-patterns.md), then apply [architecture-review-checklist.md](./references/architecture-review-checklist.md) |
| 2, "files", "workspace", "filesystem" | Read [files-universal-interface.md](./references/files-universal-interface.md) and [shared-workspace-architecture.md](./references/shared-workspace-architecture.md) |
| 3, "tool", "mcp", "primitive", "crud" | Read [mcp-tool-design.md](./references/mcp-tool-design.md) |
| 4, "domain tool", "when to add" | Read [from-primitives-to-domain-tools.md](./references/from-primitives-to-domain-tools.md) |
| 5, "execution", "completion", "loop" | Read [agent-execution-patterns.md](./references/agent-execution-patterns.md) |
| 6, "prompt", "system prompt", "behavior" | Read [system-prompt-design.md](./references/system-prompt-design.md) |
| 7, "context", "inject", "runtime", "dynamic" | Read [dynamic-context-injection.md](./references/dynamic-context-injection.md) |
| 8, "parity", "ui action", "capability map" | Read [action-parity-discipline.md](./references/action-parity-discipline.md) |
| 9, "self-modify", "evolve", "git" | Read [self-modification.md](./references/self-modification.md) |
| 10, "product", "progressive", "approval", "latent demand" | Read [product-implications.md](./references/product-implications.md) |
| 11, "mobile", "ios", "android", "background", "checkpoint" | Read [mobile-patterns.md](./references/mobile-patterns.md) |
| 11a, "icloud", "storage", "documents", "file state", "entitlement" | Read [mobile-storage.md](./references/mobile-storage.md) |
| 11b, "background task", "battery", "on-device", "cloud routing" | Read [mobile-execution.md](./references/mobile-execution.md) |
| 11c, "model tier", "token budget", "cost-aware", "batch", "caching" | Read [mobile-cost.md](./references/mobile-cost.md) |
| 12, "test", "testing", "verify", "validate" | Read [agent-native-testing.md](./references/agent-native-testing.md) |
| 13, "review", "refactor", "existing" | Read [refactoring-to-prompt-native.md](./references/refactoring-to-prompt-native.md) |
| 14, "anti-pattern", "mistake", "wrong" | Read [anti-patterns.md](./references/anti-patterns.md) |
| 15, "success", "criteria", "verify", "checklist" | Read [success-criteria.md](./references/success-criteria.md) |
| 16, "hook", "hooks", "PreToolUse", "decision control", "async hook", "permissionDecision" | Read [hooks-patterns.md](./references/hooks-patterns.md) |
| 0, "quick start", "getting started", "overview", "introduction" | Read [quick-start.md](./references/quick-start.md) |

**After reading the reference, apply those patterns to the user's specific context.**


## Task-specific references

Read the relevant reference before implementing or reviewing the matching behavior:

- Before implementing an agent-native architecture, address every applicable architecture checklist item: [architecture-review-checklist.md](./references/architecture-review-checklist.md).

Existing specialized references, when the corresponding topic applies:

- [durability-and-attestation.md](./references/durability-and-attestation.md).
