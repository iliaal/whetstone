# Wave Contract and QA Escalation

> When to read: before dispatching parallel implementation agents into one shared working tree, or when a QA fix loop has failed twice on the same finding.

## Shared-workspace wave contract

A parallel wave of implementation agents in a single working tree is permitted only while all five conditions hold. A unit that cannot meet one runs serially or gets an isolated worktree.

1. **Clean committed baseline.** Dispatch the wave from a committed tree. Each worker's output stays attributable and revertible by its file set, and an aborted wave restores to a known point.
2. **Exclusive ownership of every write surface, including the hidden ones.** Disjoint declared file lists are not enough. Lockfiles, generated code, snapshots, package manifests, and formatter output are write surfaces too: exclude each from every worker, or assign it to exactly one.
3. **No worker git operations.** No `git add`, `git commit`, `git stash`, or `git checkout` from a worker. Every worker in a shared working tree writes the same index file, so concurrent staging corrupts it, and a commit or checkout mid-wave captures or discards a peer's half-finished edits. The orchestrator commits after the batch.
4. **Orchestrator-owned verification.** Tests, lint, and build run once, after the wave, on the integrated tree -- not per worker. A worker may run a single focused test only when that test writes no shared state. Duplicate suite runs burn wall-clock and race the test cache.
5. **Scoped abort.** A write outside every worker's owned set aborts the wave and disables further shared-workspace waves for the run. Roll back only changes attributable to a worker, by owned-path list. Never `git checkout -- .`: a change no worker accounts for may be the user's, so preserve it and stop for reconciliation.

The pre-dispatch file-intersection check in the main skill catches silent conflicts the controller misses at plan time; the verbatim no-git-no-suite constraint in every dispatch prompt catches them when a unit's declared file list was incomplete. Run both -- they fail at different moments.

## Worktree base-SHA pre-check

A harness-supplied worktree is not guaranteed to snapshot the intended commit. It may be cut from the primary checkout or from a default branch instead, and uncommitted state never survives isolation. Dispatch each isolated worker with the intended base commit SHA. Before editing anything, the worker runs `git -C <worktree-path> rev-parse HEAD`, compares it with that SHA, and stops and reports on mismatch rather than proceeding. The orchestrator then runs that unit on the shared workspace under the contract above, or serially.

## QA retry escalation

One fix round is one fix dispatch plus one scoped re-review. Five rounds maximum per task, escalating by round:

- **Rounds 1-3 -- resume the same implementer.** Send the open findings verbatim as structured QA feedback (see the [QA FAIL template](./handoff-templates.md)). The implementer's context is intact: it holds the task, the code, and its own choices. Where the harness cannot message a live subagent, dispatch a fresh implementer carrying the brief path, the report-file path, and the findings; the report file is the persistent memory either way. Resuming binds the implementer only -- the scoped re-review always uses a fresh reviewer instance (see [anti-sycophancy.md](./anti-sycophancy.md)).
- **Rounds 4-5 -- fresh implementer on a stronger model.** Hand over the brief, the full finding history, and the framing that prior implementers attempted this task N times and this one now owns it. A loop that survives three resumes usually means the implementer cannot see its own problem, so de-anchoring and a capability bump land in one move.
- **At the cap -- forced disposition per finding, never a silent drop.** Every finding still open after round 5 receives exactly one of three outcomes, recorded before the run advances: fixed now under an orchestrator ruling; recorded in the plan or ledger with a named owner; or parked with a stated reason. Adjudicate only at the cap -- adjudicating early to end a loop is pre-judging under another name.

A blocked task does not halt the pipeline. Continue the remaining tasks and let final integration catch what stays open.

## Non-convergence escalation

Before a third fix dispatch, check the direction of any finding still open after its second attempt:

- **Narrowing** -- the failure surface shrinks, each fix diff targets a smaller region, re-review verdicts move toward ADDRESSED. Continue the loop.
- **Oscillating** -- the same defect returns, a fix re-breaks what the previous fix repaired, or findings swap places round over round. Stop and ask. Report the finding history and the competing fixes to the user instead of dispatching a third mechanical patch.

Round count alone does not distinguish these. A cap catches a loop that runs too long; this check catches a loop that was never going to land.
