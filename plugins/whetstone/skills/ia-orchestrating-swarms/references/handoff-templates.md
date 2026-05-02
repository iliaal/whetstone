# Handoff Templates

## QA FAIL

Use when returning failed QA results to an implementer agent.

```
**QA Result: FAIL** (Attempt N of 3)

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

Use after 3 failed attempts on the same task to escalate to the orchestrator.

```
**Escalation: Task [N] blocked after 3 attempts**

**Failure history:**
- Attempt 1: [what was tried, what failed]
- Attempt 2: [what was tried, what failed]
- Attempt 3: [what was tried, what failed]

**Root cause analysis:** [Why does this task keep failing? Systemic issue vs. one-off?]

**Resolution options:**
1. Reassign to a different agent (fresh context)
2. Decompose into smaller subtasks
3. Revise the approach entirely
4. Accept current state with known limitations
5. Defer to user for guidance
```
