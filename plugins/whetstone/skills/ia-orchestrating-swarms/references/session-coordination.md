# session coordination

## Integration Rules

**Post-integration verification**: after all agents return, check overlapping file edits, review for conflicting approaches, run full test suite.

**Spawned-session behavior**: when a skill runs inside an orchestrated pipeline (as a subagent, not user-invoked), suppress interactive prompts, auto-choose the conservative/safe default, and skip upgrade checks and telemetry (also called headless mode in sibling skills). Focus on completing the task and report what shipped, verification evidence, and any material uncertainty without padding the response with empty sections.

**Decision presentation: never silently drop options.** Use the active harness's structured question tool when available, otherwise ask in chat. If its option cap cannot represent every viable choice, split the choice into sequential rounds (`D1.1`, `D1.2`, ...) instead of truncating it. Surface cross-option dependencies in the round that introduces them. In spawned sessions, the rule above takes precedence: do not ask; choose the safe default and report it. When no safe default exists (the ambiguity involves a destructive action, an external audience, or an approval only the user can give), leave that item undone and record it as a finding in the completion report (evidence, the safe disposition taken instead, impact, decision needed), not as a question the run blocks on.

---

## Context Carry-Forward

Choose context carry-forward through capabilities the active harness exposes. Claude Code can use Continue, Rewind, `/compact`, Subagent, or `/clear`+brief; see [context-carry-forward.md](./context-carry-forward.md). In Codex, continue the same implementer's own unit with a follow-up task, or use a fresh agent with a focused handoff, automatic compaction, or a new thread with a brief. Independent reviewers always start fresh without inherited history on every round. Do not emit Claude slash commands in Codex.

## Coordination Models

Choose by work pattern. **Stateless** (the leader copies full outputs between prompts) fits short pipelines of 2-3 agents with sequential handoffs; it fails by context growing linearly with agent count, mitigated by summarizing before passing. **Stateful** (agents read and write shared task files and claim ownership) fits parallel work, 4+ agents, and complex dependency graphs; it fails by concurrent modification, mitigated by worktrees or exclusive file ownership per agent. Start stateless; graduate to stateful only when parallelism buys a real speedup and either worktree isolation or every shared-tree wave condition is satisfied. Comparison table: [orchestration-patterns.md](./orchestration-patterns.md) (Coordination models).

**Serialize a shared resource with a TTL lease file, not a coordination daemon.** Applies to one-shot subprocesses and short-lived subagents contending on one checkout or one test database. The four design points that decide whether the lease works: [cross-run-coordination.md](./cross-run-coordination.md) (TTL lease file section).

---

## Dispatch Anti-Patterns

Before designing any multi-agent workflow, check it against the five named failure modes in [dispatch-anti-patterns.md](./dispatch-anti-patterns.md): router persona, persona calls persona, sequential paraphraser, deep persona trees, dispatcher pre-judges the reviewer. Rule of thumb: if the proposed swarm has more coordinator roles than worker roles, collapse it.

## Anti-Sycophancy and Resilience

When dispatching judge panels, running parallel reviewers, or iterating on subjective evaluations, load [anti-sycophancy.md](./anti-sycophancy.md).

When designing multi-agent workflows that must survive partial failure, load [resilience-patterns.md](./resilience-patterns.md).

## Verify

- All tasks in terminal state (completed or blocked)
- Account for every spawned worker using the active harness's lifecycle/status APIs and returned completion or shutdown evidence; report any worker whose state cannot be established.
- Separately inspect `git worktree list` for worktrees owned by this task; preserve unrelated or dirty worktrees and clean up only with applicable authority. Worktree state does not prove worker termination.
- Overlapping file edits reviewed and merged
- Full test suite passes post-integration

## References

| Document | When to load | What it covers |
|----------|-------------|----------------|
| [team-compositions.md](./team-compositions.md) | Sizing a team or choosing a preset | 7 preset compositions, subagent_type cardinal rule, custom-team guidelines |
| [agent-types.md](./agent-types.md) | Claude Code agent types | Built-in and plugin `subagent_type` examples |
| [teammate-operations.md](./teammate-operations.md) | Claude Code persistent teammates | Agent/SendMessage operations, automatic lifecycle, and explicit review gates |
| [task-system.md](./task-system.md) | Claude Code work items and dependencies | TaskCreate, TaskList, TaskGet, TaskUpdate, file structure |
| [quick-reference.md](./quick-reference.md) | Claude Code spawn/message/task/shutdown syntax | Subagent, fan-out, team, task, and shutdown snippets |
| [codex-quick-reference.md](./codex-quick-reference.md) | Codex collaboration calls | Spawn, message, follow up, wait, and worktree guidance |
| [message-formats.md](./message-formats.md) | Sending structured messages between agents | All JSON message examples (regular, shutdown, idle, plan approval) |
| [orchestration-patterns.md](./orchestration-patterns.md) | Designing a multi-agent workflow | 6 patterns + 3 complete workflow examples |
| [spawn-backends.md](./spawn-backends.md) | Troubleshooting agent spawn issues | Backend comparison, auto-detection, in-process/tmux/iterm2 |
| [environment-config.md](./environment-config.md) | Configuring team environment | Environment variables and team config structure |
| [handoff-templates.md](./handoff-templates.md) | Passing work between agents | QA FAIL and Escalation Report formats |
| [context-carry-forward.md](./context-carry-forward.md) | Claude Code context controls | Continue / Rewind / compact / Subagent / clear+brief decision table |
| [anti-sycophancy.md](./anti-sycophancy.md) | Judge panels, parallel reviewers, subjective evals | Cold-start isolation, fresh instances per round, label randomization, convergence detection |
| [resilience-patterns.md](./resilience-patterns.md) | Designing workflows that survive partial failure | Cascade prevention, failure classification, mid-pipeline compensation, post-failure synthesis |
| [wave-contract.md](./wave-contract.md) | Parallel implementation in one shared tree, or a QA loop past its second round | Five wave conditions, worktree base-SHA pre-check, QA round escalation, forced disposition, non-convergence stop |
| [cross-run-coordination.md](./cross-run-coordination.md) | Deduping items across reruns, or serializing a shared resource | Orchestrator-mints-identifiers rule, TTL lease file design points |
