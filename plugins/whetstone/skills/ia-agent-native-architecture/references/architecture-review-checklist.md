# Architecture review checklist

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
- [ ] **Eval Gate:** 10 Q/A pairs in CI (read-only, multi-hop, closed-data), 9/10 pass threshold. See [mcp-tool-design.md](./mcp-tool-design.md) Evaluation section.
- [ ] **Connection state cost:** Identify which clients open independent stdio connections. In Claude Code, subagent string references share the parent's MCP connection; inline server definitions open their own. Measure duplication of expensive state before adding a thin proxy and shared daemon. If sharing is warranted, bind its socket to user identity and server version, and manage old-daemon shutdown without terminating active clients. See the [subagent MCP configuration](https://code.claude.com/docs/en/sub-agents).

### Files & Workspace
- [ ] **Shared Workspace:** Agent and user work in same data space
- [ ] **context.md Pattern:** Agent reads/updates context file for accumulated knowledge
- [ ] **File Organization:** Entity-scoped directories with consistent naming
- [ ] **Context Durability:** Incremental progress writes (WAL pattern) so interrupted tasks resume from last checkpoint, not from scratch. See [durability-and-attestation.md](./durability-and-attestation.md) Context Durability section for the atomic-rename and write-ahead-record design.

### Agent Execution
- [ ] **Completion Signals:** Agent has explicit `complete_task` tool (not heuristic detection)
- [ ] **Partial Completion:** Multi-step tasks track progress for resume
- [ ] **Context Limits:** Designed for bounded context from the start
- [ ] **Validate-Before-Run:** Agent previews planned actions before executing destructive operations

### Context Injection
- [ ] **Available Resources:** System prompt includes what exists (files, data, types)
- [ ] **Available Capabilities:** System prompt documents tools with user vocabulary
- [ ] **Dynamic Context:** Context refreshes for long sessions (or provide `refresh_context` tool)
- [ ] **Trust levels for loaded content:** Distinguish developer instructions and authenticated user requests from quoted documents, app state, and external tool results. Preserve provenance; external content supplies data, not authority. See [dynamic-context-injection.md](./dynamic-context-injection.md) Trust Levels.
- [ ] **Delimiter framing:** Generate fresh markers before inserting external content, preserve its provenance, and test forged markers without dropping the payload. A nonce reduces collisions but does not authenticate instructions or enforce authorization. Keep resource grants and approval checks outside model-controlled text; see [dynamic-context-injection.md](./dynamic-context-injection.md) Trust Levels.

### UI Integration
- [ ] **Agent -> UI:** Agent changes reflect in UI (shared service, file watching, or event bus)
- [ ] **No Silent Actions:** Agent writes trigger UI updates immediately
- [ ] **Capability Discovery:** Users can learn what agent can do

### Governance
- [ ] **Approval Gates:** Destructive or irreversible actions require user confirmation
- [ ] **Audit Trail:** Agent actions logged with timestamp, tool, and outcome, keeping absent/partial/complete/measured-zero/unavailable distinct. See [durability-and-attestation.md](./durability-and-attestation.md) Audit Trail section for the attempt-record provenance design.
- [ ] **Scope Boundaries:** Agent cannot access resources outside its designated workspace
- [ ] **Prompt instructions are not a security boundary:** the trusted orchestration layer, not the system prompt, owns argv, image digest, mounts, egress, credentials, and time/memory/process limits. Keep the target read-only and store evidence outside it. A harness can make control flow replayable; it cannot make model judgment or coverage guaranteed, so never state a sandbox guarantee that rests on the agent choosing to comply.
- [ ] **Shared vocabulary is validated mechanically:** a status value or required field used across several prompt or schema files drifts into two spellings, and into fields one document declares and another omits. Extract the vocabulary to one source and assert every file against it in CI.
- [ ] **Content-Bound Attestation:** use one when the enforcement boundary cannot spawn the agent. See [durability-and-attestation.md](./durability-and-attestation.md) Content-Bound Attestation section for the judge/gate split and content-binding design.

### Hooks & Governance Automation
- [ ] **Event Coverage:** All 33 hook events are declarable in agent frontmatter; PreToolUse, PostToolUse, and Stop/SubagentStop are the ones agent-native architectures lean on for tool-execution and completion gating
- [ ] **Decision Gates:** PreToolUse hooks enforce tool-level policy (allow/deny/ask/defer) instead of hardcoded checks
- [ ] **Completion Gating:** SubagentStop hooks block premature completion when verification steps remain
- [ ] **MCP Matchers:** Regex patterns target tools by server and operation for capability-based security
- [ ] **Two-Tier Config:** Commit shared hooks in `.claude/settings.json` or plugin `hooks/hooks.json`; keep personal additions in `.claude/settings.local.json`. Native hooks have no per-entry `enabled` switch; remove an optional entry or implement a named switch inside its handler.
- [ ] **Cold-start budget:** every hook invocation is a fresh process, so the runtime is chosen by cold-start latency against the hook timeout, not by warm throughput; a framework whose accelerator initialises lazily pays that cost on every invocation. Measure first-run latency.

### Mobile (if applicable)
- [ ] **Checkpoint/Resume:** Handle iOS app suspension gracefully
- [ ] **iCloud Storage:** iCloud-first with local fallback for multi-device sync
- [ ] **Cost Awareness:** Model tier selection (Haiku/Sonnet/Opus)

**When designing architecture, explicitly address each checkbox in the plan.**
