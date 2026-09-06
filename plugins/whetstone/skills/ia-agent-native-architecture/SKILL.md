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
| 1, "design", "architecture", "plan" | Read [architecture-patterns.md](./references/architecture-patterns.md), then apply Architecture Checklist below |
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

## Architecture Review Checklist

When designing an agent-native system, verify these **before implementation**:

### Core Principles
- [ ] **Parity:** Every UI action has a corresponding agent capability
- [ ] **Granularity:** Tools are primitives; features are prompt-defined outcomes
- [ ] **Composability:** New features can be added via prompts alone
- [ ] **Emergent Capability:** Agent can handle open-ended requests in its domain

### Tool Design
- [ ] **Dynamic vs Static:** For external APIs where agent should have full access, use Dynamic Capability Discovery
- [ ] **CRUD Completeness:** Every entity has create, read, update, AND delete
- [ ] **Primitives over Workflows:** Tools expose atomic capabilities; compose workflows in prompts
- [ ] **API as Validator:** Use `z.string()` inputs when the API validates, not `z.enum()`
- [ ] **Eval Gate:** 10 Q/A pairs in CI (read-only, multi-hop, closed-data), 9/10 pass threshold. See [mcp-tool-design.md](./references/mcp-tool-design.md) Evaluation section.

### Files & Workspace
- [ ] **Shared Workspace:** Agent and user work in same data space
- [ ] **context.md Pattern:** Agent reads/updates context file for accumulated knowledge
- [ ] **File Organization:** Entity-scoped directories with consistent naming
- [ ] **Context Durability:** Incremental progress writes (WAL pattern) so interrupted tasks resume from last checkpoint, not from scratch. See [durability-and-attestation.md](./references/durability-and-attestation.md) Context Durability section for the atomic-rename and write-ahead-record design.

### Agent Execution
- [ ] **Completion Signals:** Agent has explicit `complete_task` tool (not heuristic detection)
- [ ] **Partial Completion:** Multi-step tasks track progress for resume
- [ ] **Context Limits:** Designed for bounded context from the start
- [ ] **Validate-Before-Run:** Agent previews planned actions before executing destructive operations

### Context Injection
- [ ] **Available Resources:** System prompt includes what exists (files, data, types)
- [ ] **Available Capabilities:** System prompt documents tools with user vocabulary
- [ ] **Dynamic Context:** Context refreshes for long sessions (or provide `refresh_context` tool)
- [ ] **Trust levels for loaded content:** System prompt distinguishes trusted (developer-authored) from untrusted (user input, retrieved docs, tool outputs); untrusted text is data, never instructions. See [dynamic-context-injection.md](./references/dynamic-context-injection.md) Trust Levels section for the prompt-injection defense details.
- [ ] **Delimiter authentication:** a writer-side property, never a repair applied to a finished document. Parsing a finished document into sections and re-emitting with generator-written delimiters *splits at the forged delimiter*, which places the forgery outside every fence the generator then writes, so it comes out renumbered and more authoritative than before. Three further requirements on the stamped-delimiter design in [dynamic-context-injection.md](./references/dynamic-context-injection.md): the token must be per-run (one that outlives its run authenticates a stale delimiter) and must be stripped before the content is forwarded, since it is authentication and not evidence; the round where the reader requires a token but the writer emitted none is undecidable, so **refuse** and name the token in the error rather than scoring it either way; and if the writer is a model, the reader's requirement is inert until the writer's own instructions tell it to stamp, so a gate whose writer never learned about it never arms. Verify two things by fixture instead of reasoning: that the token survives any redaction or normalization pass between writer and reader (a run of hex is exactly what an entropy rule rewrites), and that the untrusted payload still *arrives*, asserting that each forged delimiter sits inside the generator's fence rather than asserting it is absent.

### UI Integration
- [ ] **Agent -> UI:** Agent changes reflect in UI (shared service, file watching, or event bus)
- [ ] **No Silent Actions:** Agent writes trigger UI updates immediately
- [ ] **Capability Discovery:** Users can learn what agent can do

### Governance
- [ ] **Approval Gates:** Destructive or irreversible actions require user confirmation
- [ ] **Audit Trail:** Agent actions logged with timestamp, tool, and outcome, keeping absent/partial/complete/measured-zero/unavailable distinct. See [durability-and-attestation.md](./references/durability-and-attestation.md) Audit Trail section for the attempt-record provenance design.
- [ ] **Scope Boundaries:** Agent cannot access resources outside its designated workspace
- [ ] **Content-Bound Attestation:** use one when the enforcement boundary cannot spawn the agent. See [durability-and-attestation.md](./references/durability-and-attestation.md) Content-Bound Attestation section for the judge/gate split and content-binding design.

### Hooks & Governance Automation
- [ ] **Event Coverage:** All 33 hook events are declarable in agent frontmatter; PreToolUse, PostToolUse, and Stop/SubagentStop are the ones agent-native architectures lean on for tool-execution and completion gating
- [ ] **Decision Gates:** PreToolUse hooks enforce tool-level policy (allow/deny/ask/defer) instead of hardcoded checks
- [ ] **Completion Gating:** SubagentStop hooks block premature completion when verification steps remain
- [ ] **MCP Matchers:** Regex patterns target tools by server and operation for capability-based security
- [ ] **Two-Tier Config:** Shared policy committed, personal overrides git-ignored, per-hook disable toggles

### Mobile (if applicable)
- [ ] **Checkpoint/Resume:** Handle iOS app suspension gracefully
- [ ] **iCloud Storage:** iCloud-first with local fallback for multi-device sync
- [ ] **Cost Awareness:** Model tier selection (Haiku/Sonnet/Opus)

**When designing architecture, explicitly address each checkbox in the plan.**
