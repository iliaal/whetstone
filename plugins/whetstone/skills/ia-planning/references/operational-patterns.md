# Operational Patterns

## Context Management Rules

| Situation | Action |
|-----------|--------|
| Starting new phase | Read .plan/task_plan.md (refresh goals in attention window) |
| Discovery changes the plan | Record it under the affected phase or decision in .plan/task_plan.md |
| After completing phase | Update status, verification result, and `## Next Step` in .plan/task_plan.md |
| Image/PDF evidence must survive the turn | Record only the deciding observation under the affected phase |
| Resuming after gap | Read .plan/task_plan.md, run `git diff --stat`, and reconcile actual vs planned state |
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

For high-risk or genuinely ambiguous plans, run one independent review against the original request and the plan. Revise only findings that expose a concrete gap. Run another review only after a material redesign. Seek approval only for unresolved choices that belong to the user.

## 5-Question Context Check

If you can answer these, your planning is solid:

| Question | Source |
|----------|--------|
| Where am I? | `## Next Step` in .plan/task_plan.md, confirmed against per-phase `Status:` |
| Where am I going? | Remaining phases |
| What's the goal? | Approach section |
| What have I learned? | Decisions and affected phase notes in .plan/task_plan.md |
| What have I done? | Phase status and verification results in .plan/task_plan.md |

## Session Continuity & Traceability

**Intermediate outputs for long sessions.** Add a numbered file under `.plan/` only when a phase produces recovery state that does not fit clearly in `task_plan.md` or the working-tree diff. Read durable state, not conversation memory, when resuming after compaction or across sessions.

**Session continuity.** At session start or after compaction: read `## Next Step` at the head of `.plan/task_plan.md`, confirm it against the per-phase `Status:` fields and the working-tree diff, then resume there. Refresh `Next Step` whenever a phase `Status` changes. Before an interruption, record the stopping point, completed verification, and any blocker that changes the next action.

**SHA recording.** When an external tracker, review boundary, or multi-session handoff needs commit traceability, note the commit SHA inline: `- [x] Task 1.1 \`abc1234\``. Skip it when version control already makes the relationship obvious.

**Deviation documentation.** Record a deviation only when it changes a preserved decision, acceptance criterion, dependency, or next action. Do not log harmless implementation discoveries that the current diff already explains.
