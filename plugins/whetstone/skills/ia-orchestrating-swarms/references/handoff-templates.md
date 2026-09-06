# Handoff Templates

> When to read: when one agent is handing work back or forward (QA fail, implementation complete, blocked, escalation) and a structured template is wanted instead of free-form prose.

## QA FAIL

Use when returning failed QA results to an implementer agent.

```
**QA Result: FAIL** (Round N of 5)

**Expected:** [what the spec/test requires]
**Actual:** [what the implementation does]
**Evidence:** [screenshot, test output, or log excerpt]
**Fix instruction:** [specific change needed]
**File(s) to modify:** [exact paths]

Fix ONLY the issues listed. Do NOT introduce new features, refactor unrelated code, or restructure the implementation.
```

## Review Dispatch

Use when dispatching a review subagent after a task completes. Two sequential dispatches: spec compliance first, then code quality. Each gets fresh context (no session history from the implementer).

### Stage 1: Spec Compliance

```
Review this implementation for spec compliance ONLY. Do not review code quality.

**Task spec:**
[paste the exact task description/requirements]

**Files changed:**
[paste the diff or list of changed files with relevant content]

**Check each requirement:**
1. Is every requirement implemented? List any gaps.
2. Is anything implemented that was NOT in the spec? List additions.
3. Does the implementation match the spec's intent, not just its letter?

**Return format:**
- PASS: all requirements met, no extras
- FAIL: [list gaps or unwanted additions]
```

### Stage 2: Code Quality

Only dispatch after Stage 1 passes.

```
Review this implementation for code quality. Spec compliance already verified.

**Files changed:**
[paste the diff or list of changed files with relevant content]

**Review for:**
- Correctness (edge cases, error handling, type safety)
- Security (input validation, auth, injection vectors)
- Performance (N+1 queries, unbounded collections, missing indexes)
- Maintainability (naming, complexity, duplication)

**Return format:**
- Strengths: [specific positive observations]
- Issues: [ranked by severity -- Critical/Important/Medium/Minor]
- Verdict: Ready / Needs fixes
```

## Escalation Report

Use at the round-5 cap, or earlier on non-convergence -- a finding that oscillates rather than narrows after its second attempt. Rounds 1-3 resume the same implementer; rounds 4-5 hand the task to a fresh implementer on a stronger model. Round mechanics: [wave-contract.md](./wave-contract.md).

```
**Escalation: Task [N] blocked after [N] rounds** ([cap reached | non-convergence after round 2])

**Failure history:**
- Round 1 (same implementer): [what was tried, what failed]
- Round 2 (same implementer): [what was tried, what failed]
- Round 3 (same implementer): [what was tried, what failed]
- Round 4 (fresh implementer, stronger model): [what was tried, what failed]
- Round 5 (fresh implementer, stronger model): [what was tried, what failed]

**Root cause analysis:** [Why does this task keep failing? Systemic issue vs. one-off?]

**Forced disposition per open finding** (exactly one each, recorded before the run advances):
1. Fixed now under an orchestrator ruling
2. Recorded in the plan or ledger with a named owner
3. Parked with a stated reason

**Escalate to the user instead** when the block is a spec contradiction, a destructive action, or a decision only the user can make.
```
