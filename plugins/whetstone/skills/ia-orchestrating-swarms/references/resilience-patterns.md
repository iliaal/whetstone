# Swarm Resilience Patterns

Load this reference when designing a multi-agent workflow that must survive partial failure. Swarm failures are inevitable — contain blast radius and recover partial value rather than discarding everything.

## Cascade prevention

Set timeout boundaries per agent. If one agent fails or hangs, do not let it cascade into abandoning the entire swarm's work. The orchestrator treats each agent as independently failable — other agents continue their work unaffected. Terminate unresponsive agents after the timeout rather than waiting indefinitely.

Apply circuit-breaker logic to agent types: after N consecutive failures from the same agent type, stop dispatching to it and route to an alternative (different model, different decomposition). Apply bulkhead isolation: a failing agent type cannot exhaust the shared task queue or block other agent types from proceeding.

## Recovery strategy

When an agent fails, classify the failure before acting:

- **Retry** — transient errors (network timeout, rate limit). Re-dispatch the same task; if the task declares a file artifact, retry onto a fresh output path (see below).
- **Reassign** — agent-specific issue (context pollution, wrong model for task complexity). Dispatch a fresh agent, optionally with a different model.
- **Escalate** — systemic problem (bad spec, missing dependency, impossible constraint). Surface to the orchestrator or user with an [Escalation Report](./handoff-templates.md).

For agent-reported `BLOCKED` status specifically (as opposed to crashes or timeouts), use the BLOCKED triage decision tree in the main skill under "Dispatch Discipline" — it maps the four BLOCKED root causes (missing context / reasoning ceiling / task too large / spec wrong) to concrete responses.

Never retry blindly. Repeating the same prompt in the same conditions produces the same failure.

**A worker still inside its timeout is not a failure.** The terminate rule under Cascade prevention fires on one condition only -- an agent past its own timeout boundary. Silence, an absent message channel, or the orchestrator reaching a wrap-up point are none of them, and none licenses a stop, kill, or interrupt. While such a worker can still write, treat its scope as unsettled: its on-disk edits and any messages it sent are provisional, so do not reconstruct its result, do not dispatch replacement work into its scope, and do not report that scope complete. Exclude its owned paths from validation, staging, and commits until it returns or its timeout actually expires -- at which point it becomes a crash and takes the working-tree inspection path in the main skill.

When agents hand off through files rather than return values, the artifact is part of the failure classification. A missing, malformed, wrong-version, or wrong-shape artifact is a failed dispatch, not a partial success -- validate the declared output against its expected shape before advancing the phase, and never substitute a command that produces no artifact for an unavailable backend. On artifact-validation failure, give the retry a fresh output path and preserve the failed attempt for diagnosis. Retrying onto the same path means a crashed retry leaves the previous attempt's file sitting there looking like a success, and the orchestrator has no way to tell the two apart. This governs declared handoff artifacts only. An agent that crashed while making in-place edits to its owned source files takes the working-tree inspection and verify-and-continue relaunch in the main skill instead -- a fresh path is meaningless for an in-place edit, and redoing the work double-applies it.

## Mid-pipeline compensation

When an agent fails mid-pipeline after earlier agents have already written files or made changes, classify whether those earlier effects are reversible before deciding the recovery path. If reversible (file writes, uncommitted changes), revert and retry the pipeline segment. If irreversible (committed code, external API calls, database writes), compensate rather than retry — apply a corrective action that accounts for the partial state. Never retry blindly when earlier stages have produced side effects.

## Post-failure synthesis

Even partial results from a failed swarm run have value. When some agents succeed and others fail, collect and present the successful outputs rather than discarding everything. Mark failed tasks as incomplete in the synthesis so downstream consumers know which areas lack coverage.
