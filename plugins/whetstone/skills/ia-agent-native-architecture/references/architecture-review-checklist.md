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
- [ ] **Per-session state cost:** a stdio MCP server is a child of the client (one process per session and per subagent), so every expensive resource it holds (model weights, GPU context, index handles) is duplicated that many times. Keep the registration stdio and make the command a thin proxy to a user-private socket served by a shared daemon started on first use. Key the socket on the binary's version so a rebuilt binary cannot talk to a stale daemon, and have the new daemon reap the orphan.

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
- [ ] **Trust levels for loaded content:** System prompt distinguishes trusted (developer-authored) from untrusted (user input, retrieved docs, tool outputs); untrusted text is data, never instructions. See [dynamic-context-injection.md](./dynamic-context-injection.md) Trust Levels section for the prompt-injection defense details.
- [ ] **Delimiter authentication:** a writer-side property, never a repair applied to a finished document. Parsing a finished document into sections and re-emitting with generator-written delimiters *splits at the forged delimiter*, which places the forgery outside every fence the generator then writes, so it comes out renumbered and more authoritative than before. Three further requirements on the stamped-delimiter design in [dynamic-context-injection.md](./dynamic-context-injection.md): the token must be per-run (one that outlives its run authenticates a stale delimiter) and must be stripped before the content is forwarded, since it is authentication and not evidence; the round where the reader requires a token but the writer emitted none is undecidable, so **refuse** and name the token in the error rather than scoring it either way; and if the writer is a model, the reader's requirement is inert until the writer's own instructions tell it to stamp, so a gate whose writer never learned about it never arms. Verify two things by fixture instead of reasoning: that the token survives any redaction or normalization pass between writer and reader (a run of hex is exactly what an entropy rule rewrites), and that the untrusted payload still *arrives*, asserting that each forged delimiter sits inside the generator's fence rather than asserting it is absent.

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
- [ ] **Two-Tier Config:** Shared policy committed, personal overrides git-ignored, per-hook disable toggles
- [ ] **Cold-start budget:** every hook invocation is a fresh process, so the runtime is chosen by cold-start latency against the hook timeout, not by warm throughput; a framework whose accelerator initialises lazily pays that cost on every invocation. Measure first-run latency.

### Mobile (if applicable)
- [ ] **Checkpoint/Resume:** Handle iOS app suspension gracefully
- [ ] **iCloud Storage:** iCloud-first with local fallback for multi-device sync
- [ ] **Cost Awareness:** Model tier selection (Haiku/Sonnet/Opus)

**When designing architecture, explicitly address each checkbox in the plan.**
