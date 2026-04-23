# Headless Mode

When invoked programmatically (by another skill or command with `mode:headless`), skip interactive prompts and return structured triage results.

## Triage Process

1. **Collect** -- gather all unresolved review comments from the PR
2. **Check prior feedback** -- if prior review comments exist (re-review), flag previously ignored or partially addressed items. Skip on first-time reviews.
3. **Classify each comment** using the same verification logic as interactive mode:

| Classification | Criteria | Action |
|---------------|----------|--------|
| **AUTO-FIX** | Clearly correct, matches project conventions, mechanical change (<10 lines), passes source-specific checks | Classify for `ia-pr-comment-resolver` dispatch |
| **AUTO-DECLINE** | Technically incorrect (provable with code evidence), contradicts project conventions, YAGNI (zero callers via grep) | Draft push-back response with evidence |
| **ESCALATE** | Ambiguous intent, architectural decision, reasonable engineers could disagree, changes user-visible behavior | Surface to user with context summary |

4. **Return** structured output:

```
TRIAGE RESULTS:
- AUTO-FIX (N items): [list with one-line summaries]
- AUTO-DECLINE (N items): [list with evidence for each]
- ESCALATE (N items): [list with why each needs human judgment]
- PRIOR FEEDBACK: [addressed|partially addressed|ignored] with specifics
```

## Constraints

- Never auto-fix security-related suggestions -- always escalate
- Never auto-decline feedback from the project owner -- escalate instead
- Apply the same skepticism levels from Source-Specific Handling (agents: skeptical, external: verify, owner: trusted)
- If >50% of comments classify as ESCALATE, abort headless mode and recommend interactive review
