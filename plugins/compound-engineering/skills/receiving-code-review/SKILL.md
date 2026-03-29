---
name: receiving-code-review
description: >-
  Process code review feedback critically: check correctness before acting, push back
  on incorrect suggestions, no performative agreement. Use when responding to
  PR/MR review comments or implementing reviewer suggestions received from others.
---

# Receiving Code Review

## Core Principle

Verify before implementing. Technical correctness matters more than social comfort. A reviewer can be wrong -- blindly implementing bad suggestions creates bugs.

## Response Pattern

For each piece of feedback, follow this sequence:

**0. Prior feedback check (re-reviews only)** -- if this is not the first review round, check whether previously flagged issues were addressed before processing new comments. Compare the current diff against prior review threads (`gh api repos/{owner}/{repo}/pulls/{pr}/comments`). Surface any that were ignored or only partially fixed -- these take priority over new feedback.

1. **Read** -- Understand what's being suggested and why
2. **Verify** -- Is the suggestion technically correct for THIS codebase?
3. **Evaluate** -- Does it improve the code, or is it preference/style?
4. **Respond** -- Agree with evidence, disagree with evidence, or ask for clarification
5. **Implement** -- Only after verification confirms the suggestion is correct

Triage all feedback first (see Implementation Order below), then implement one item at a time. Don't batch-implement everything at once.

## Handling Unclear Feedback

When feedback is ambiguous or incomplete:

- **Stop** -- do not implement anything unclear
- Clarify ALL unclear items before implementing ANY of them (they may be related)
- Ask specific questions: "Are you suggesting X or Y?" not "Can you elaborate?"
- If the reviewer's intent is clear but the technical approach is wrong, say so

## Source-Specific Handling

### From the user (project owner)

- Trusted context -- they know the codebase and business requirements
- Implement after understanding, but still verify technical correctness
- Ask clarifying questions when the intent is clear but the approach seems risky
- No performative agreement -- just acknowledge and implement

### From automated review agents

- **Skeptical by default** -- agents lack full context
- Verify every suggestion against the actual codebase
- Check for YAGNI violations (agents love adding "just in case" code)
- Discard suggestions that contradict project conventions (check CLAUDE.md)
- Agents may flag things that are intentional design decisions -- check before changing

### From external reviewers (PR comments, open source)

- Verify technical correctness for THIS stack and codebase
- Check if the suggestion applies to this version of the framework/library
- Push back if the reviewer lacks context about architectural decisions
- Distinguish between "this is wrong" and "I would do it differently"

## When to Push Back

Push back (with evidence) when a suggestion:

- **Breaks existing functionality** -- "This would break X because Y depends on Z"
- **Violates project conventions** -- "Our CLAUDE.md specifies we do it this way because..."
- **Is technically incorrect** -- "This API was deprecated in v3. We're on v4 which uses..."
- **Adds unnecessary complexity** -- "This handles a case that can't occur because..."
- **Is unused (YAGNI)** -- when a reviewer suggests "implementing properly", grep the codebase for actual usage FIRST. Zero callers? Suggest removal: "This endpoint isn't called. Remove it (YAGNI)?" If used, implement properly.
- **Conflicts with architectural decisions** -- "We chose X over Y in the brainstorm because..."

**Valid evidence:** code references (`file:line`), test output, git blame/log, framework docs, reproduction steps, grep results showing usage patterns. **Not evidence:** "I think", "it should work", "it's fine", appeals to convention without citing the convention, or restating the original code as justification.

## When NOT to Push Back

Accept feedback when:

- The suggestion is correct and you missed something
- It catches a genuine bug or edge case
- It improves readability without changing behavior
- It aligns with project conventions you overlooked
- The reviewer has domain expertise you lack

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Agreeing before verifying | Verify first, then state what you found |
| Implementing without understanding impact | Trace the change through callers before editing |
| Apologizing instead of fixing | State the correction factually, then implement |
| Thanking the reviewer instead of responding technically | Delete "Thanks" -- state the fix instead |
| Pushing back without evidence | Include the specific code path or test that proves your point |
| Batch-implementing then testing | Test after each individual fix |
| Can't verify the suggestion | Say so: "Can't verify this without [X]. Should I [investigate/ask/proceed]?" -- don't guess or implement blind |

## Approved Response Templates

When feedback IS correct: "Verified -- [specific issue]. Implementing [specific fix]."
When feedback is partially correct: "The [X part] is right because [reason]. The [Y part] doesn't apply here because [evidence]."
When you need clarification: "Can you clarify [specific ambiguity]? The comment could mean [A] or [B], which changes the fix."

## Implementation Order

After triaging all feedback:

1. **Clarify** -- resolve all unclear items first
2. **Blocking issues** -- fix things that break functionality
3. **Simple fixes** -- quick wins that are clearly correct
4. **Complex fixes** -- changes that need careful implementation

Test after each individual fix, not after implementing everything.

## When Your Pushback Was Wrong

State the correction factually: "Checked this, you're correct because [reason]. Implementing." No extended apology, no self-deprecation -- just acknowledge and move on.

## GitHub PR Reviews

- Reply in the inline comment thread, not as top-level PR comments: `gh api repos/{owner}/{repo}/pulls/{pr}/comments -f body="..." -f in_reply_to={comment_id}`
- Reference specific lines when explaining why you disagree
- Mark conversations as resolved only after the fix is verified
- If a suggestion spawns a larger discussion, suggest moving it to an issue

## Headless Mode

When invoked programmatically (by another skill or command with `mode:headless`), skip interactive prompts and return structured triage results.

### Triage Process

1. **Collect** -- gather all unresolved review comments from the PR
2. **Check prior feedback** -- if prior review comments exist (re-review), same as step 0 above. Flag previously ignored or partially addressed items. Skip on first-time reviews.
3. **Classify each comment** using the same verification logic as interactive mode:

| Classification | Criteria | Action |
|---------------|----------|--------|
| **AUTO-FIX** | Clearly correct, matches project conventions, mechanical change (<10 lines), passes source-specific checks | Classify for `pr-comment-resolver` dispatch |
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

### Headless Constraints

- Never auto-fix security-related suggestions -- always escalate
- Never auto-decline feedback from the project owner -- escalate instead
- Apply the same skepticism levels from Source-Specific Handling (agents: skeptical, external: verify, owner: trusted)
- If >50% of comments classify as ESCALATE, abort headless mode and recommend interactive review

## Scope vs `pr-comment-resolver` Agent

This skill and the `pr-comment-resolver` agent handle different situations:

| | This skill (interactive) | This skill (headless) | `pr-comment-resolver` agent |
|---|---|---|---|
| **When** | Interactive review requiring judgment | Programmatic triage by another skill/command | Implementing a single pre-triaged comment |
| **Approach** | Verify, evaluate, potentially push back | Auto-classify and return triage results | Implement a single pre-classified change |
| **Skepticism** | High -- check correctness first | High -- same rules, automated classification | Low -- comments are pre-triaged |
| **Use for** | Unclear suggestions, architectural feedback | Batch triage before dispatching resolvers | Clear-cut fixes, style nits, typos |

When the `pr-comment-resolver` agent encounters feedback that requires judgment (architectural decisions, debatable trade-offs), it should escalate rather than implement.

## Examples

**Bad -- performative agreement:**
> Reviewer: "This should use a Map instead of an object for better performance."
> Response: "Great catch! Switching to Map now."

**Good -- verify first:**
> Reviewer: "This should use a Map instead of an object for better performance."
> Response: "Checked this -- the object has at most 5 keys (bounded by the enum). Map overhead isn't justified here. Keeping as-is."

**Bad -- blind implementation:**
> Reviewer: "Add null checks for the user parameter."
> Response: "Done, added null checks."

**Good -- verify the premise:**
> Reviewer: "Add null checks for the user parameter."
> Response: "Traced the call chain -- `user` comes from the auth middleware which guarantees non-null (throws 401 otherwise). Adding a null check here would be dead code. Should I add it anyway for defense-in-depth?"

**Good -- unclear item:**
> Reviewer: "This logic seems off."
> Response: "Can you clarify which part? The filter predicate, the sort order, or the pagination logic?"

## Verify

- All feedback items triaged (classified as correct, incorrect, or unclear)
- Ambiguous items clarified before any implementation
- Each fix verified individually (test after each, not batch)
- No performative agreement phrases in responses ("Great catch!", "Absolutely right")

## Integration

This skill pairs with:
- `code-review` -- the outbound side (requesting reviews)
- `pr-comment-resolver` agent -- for mechanical PR comment resolution (see scope table above)
- `verification-before-completion` -- verify each fix before marking resolved
