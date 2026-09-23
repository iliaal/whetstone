# Swarm Resilience Patterns

Load this reference when designing a multi-agent workflow that must survive partial failure. Swarm failures are inevitable: contain blast radius and recover partial value rather than discarding everything.

## Cascade prevention

Set timeout boundaries per agent. If one agent fails or hangs, do not let it cascade into abandoning the entire swarm's work. The orchestrator treats each agent as independently failable; other agents continue their work unaffected. Terminate unresponsive agents after the timeout rather than waiting indefinitely.

Apply circuit-breaker logic to agent types: after N consecutive failures from the same agent type, stop dispatching to it and route to an alternative (different model, different decomposition). Apply bulkhead isolation: a failing agent type cannot exhaust the shared task queue or block other agent types from proceeding.

## Dispatch backpressure

When the harness accepts a dispatch but caps active execution, the overflow queues rather than fails. Treat transient capacity-related spawn errors as backpressure: any retryable error indicating the limiter rejected the dispatch. Exact wording varies across harness versions and platforms, so do not pattern-match on a fixed string list. Re-dispatch queued agents as active ones complete. Record an agent as failed only after a successful dispatch times out or returns an error, or when dispatch fails for a non-capacity reason (bad tool name, malformed prompt, missing permission). A rate-capped fan-out is still parallel; it is just limited to what the harness can run concurrently.

## Recovery strategy

When an agent fails, classify the failure before acting:

- **Retry**: transient errors (network timeout, rate limit). Re-dispatch the same task; if the task declares a file artifact, retry onto a fresh output path (see below).
- **Reassign**: agent-specific issue (context pollution, wrong model for task complexity). Dispatch a fresh agent, optionally with a different model.
- **Escalate**: systemic problem (bad spec, missing dependency, impossible constraint). Surface to the orchestrator or user with an [Escalation Report](./handoff-templates.md).

For agent-reported `BLOCKED` status specifically (as opposed to crashes or timeouts), use the BLOCKED triage decision tree in the main skill under "Dispatch Discipline". It maps the four BLOCKED root causes (missing context / reasoning ceiling / task too large / spec wrong) to concrete responses.

Never retry blindly. Repeating the same prompt in the same conditions produces the same failure.

**A worker still inside its timeout is not a failure.** The terminate rule under Cascade prevention fires on one condition only: an agent past its own timeout boundary. Silence, an absent message channel, or the orchestrator reaching a wrap-up point are none of them, and none licenses a stop, kill, or interrupt. While such a worker can still write, treat its scope as unsettled: its on-disk edits and any messages it sent are provisional, so do not reconstruct its result, do not dispatch replacement work into its scope, and do not report that scope complete. Exclude its owned paths from validation, staging, and commits until it returns or its timeout actually expires, at which point it becomes a crash and takes the working-tree inspection path in the main skill.

When agents hand off through files rather than return values, the artifact is part of the failure classification. A missing, malformed, wrong-version, or wrong-shape artifact is a failed dispatch, not a partial success: validate the declared output against its expected shape before advancing the phase, and never substitute a command that produces no artifact for an unavailable backend. On artifact-validation failure, give the retry a fresh output path and preserve the failed attempt for diagnosis. Retrying onto the same path means a crashed retry leaves the previous attempt's file sitting there looking like a success, and the orchestrator has no way to tell the two apart. This governs declared handoff artifacts only. An agent that crashed while making in-place edits to its owned source files takes the working-tree inspection and verify-and-continue relaunch in the main skill instead; a fresh path is meaningless for an in-place edit, and redoing the work double-applies it.

## Bounded collection

Collecting a worker's result on a bounded budget means repeating the host's blocking wait back to back until the result artifact or a terminal outcome lands or an aggregate wall-clock limit passes. A host whose single wait returns quickly reaches the limit by repeating it; one short return is not "done waiting". Classify the end state three ways: a terminal outcome was collected; a receipt exists (the dispatch was accepted, a status or completion signal arrived) but the result was not collected; or this host offers no reliable collector at all. On some hosts the task-tagged completion message is itself the terminal result while the dedicated wait tool reports status only, so key collection to whatever channel the active host uses to deliver the final answer rather than to one collector shape.

## Orchestrator context exhaustion mid-pipeline

A multi-stage synthesis pipeline can exhaust the dispatching context before the final stages run; the symptom is subagent launches starting to fail after several dispatch and collect rounds. Once every worker result is collected, write a complete, self-sufficient handoff contract to disk with every field present (`null` for a field that does not apply, never omitted) and hand the remaining stages to fresh leaf subagents. Each leaf's brief names the exact handoff file path and the stage to run; the leaf reads that file and the run directory (the per-run folder holding the collected worker artifacts and the handoff file) and nothing else. This is the one sanctioned case of a worker reading its assignment from disk; the general rule that the brief carries the task text is in [worker-lifecycle.md](./worker-lifecycle.md). A fact in neither place does not exist to a leaf. Leaves launch nothing themselves; a leaf that dispatches further agents recreates the exhaustion one level down.

## Mid-pipeline compensation

When an agent fails mid-pipeline after earlier agents have already written files or made changes, classify whether those earlier effects are reversible before deciding the recovery path. If reversible (file writes, uncommitted changes), revert and retry the pipeline segment. If irreversible (committed code, external API calls, database writes), compensate rather than retry: apply a corrective action that accounts for the partial state. Never retry blindly when earlier stages have produced side effects.

## Post-failure synthesis

Even partial results from a failed swarm run have value. When some agents succeed and others fail, collect and present the successful outputs rather than discarding everything. Mark failed tasks as incomplete in the synthesis so downstream consumers know which areas lack coverage.

**Uniform failure across every unit is an infrastructure result, not a clean verdict.** A pipeline that emits "no findings" when every unit errored the same way is indistinguishable from a clean run. When the failure count equals the unit count and the failures share a cause, report the provider, auth, or model failure and suppress the verdict.
