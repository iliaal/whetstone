# Operational Patterns

## Context Management Rules

| Situation | Action |
|-----------|--------|
| Starting new phase | Read .plan/task_plan.md (refresh goals in attention window) |
| After any discovery | Write to .plan/findings.md immediately |
| After completing phase | Update .plan/task_plan.md status, log to .plan/progress.md |
| After viewing image/PDF | Write findings NOW (multimodal content doesn't persist) |
| Resuming after gap | Read all planning files, run `git diff --stat` to reconcile actual vs planned state |
| Just wrote a file | Don't re-read it (still in context) |
| Error occurred | Log to .plan/task_plan.md, read relevant files for state |

## Error Protocol

```
ATTEMPT 1: Diagnose root cause -> targeted fix
ATTEMPT 2: Different approach (different tool, library, method)
ATTEMPT 3: Question assumptions -> search for solutions -> update plan
AFTER 3 FAILURES: Escalate to user with what you tried
```

Never repeat the exact same failing action. Track attempts, mutate approach.

## Iterative Refinement

For complex projects, iterate on the plan before implementing:
1. Draft initial plan
2. Dispatch a plan-reviewer subagent with the plan document and original spec (not session history) to evaluate completeness, feasibility, and gaps
3. Fix issues found, re-dispatch reviewer if needed (max 3 iterations)
4. Present to user for final approval before implementation

## 5-Question Context Check

If you can answer these, your planning is solid:

| Question | Source |
|----------|--------|
| Where am I? | Current phase in .plan/task_plan.md |
| Where am I going? | Remaining phases |
| What's the goal? | Approach section |
| What have I learned? | .plan/findings.md |
| What have I done? | .plan/progress.md |
