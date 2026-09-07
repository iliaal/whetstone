# evidence and disagreement

## When to Push Back

Push back (with evidence) when a suggestion:

- **Breaks existing functionality** -- "This would break X because Y depends on Z"
- **Violates project conventions** -- "Our CLAUDE.md specifies we do it this way because..."
- **Is technically incorrect** -- "This API was deprecated in v3. We're on v4 which uses..."
- **Adds unnecessary complexity** -- "This handles a case that can't occur because..."
- **Is unused (YAGNI)** -- when a reviewer suggests "implementing properly", grep the codebase for actual usage FIRST. Zero callers? Suggest removal: "This endpoint isn't called. Remove it (YAGNI)?" If used, implement properly.
- **Conflicts with architectural decisions** -- "We chose X over Y in the brainstorm because..."

**Valid evidence:** code references (`file:line`), test output, git blame/log, framework docs, reproduction steps, grep results showing usage patterns. **Not evidence:** "I think", "it should work", "it's fine", appeals to convention without citing the convention, or restating the original code as justification.

### False-Positive Taxonomy (for dismissed suggestions)

When dismissing a suggestion (AUTO-DECLINE, manual push-back), tag the dismissal with one of four categories so the reviewer sees structured reasoning, not a bare "no":

| Category | Reviewer's response cited | Evidence required | Maps to "When to Push Back" |
|----------|--------------------------|-------------------|------------------------------|
| **FP-ASSUMPTION** | Reviewer assumed behavior that doesn't match the code | Quote the specific line that contradicts the assumption | "Is technically incorrect" |
| **FP-CONVENTION** | Suggestion conflicts with this project's conventions | Cite the CLAUDE.md rule, ADR, or the established pattern in `file:line` | "Violates project conventions" |
| **FP-ALREADY-HANDLED** | The concern is handled elsewhere (parent function, middleware, framework) | Show the existing handler in `file:line`. When the dismissal is "subsumed by the other fix", showing the handler is not enough -- check the covering fix against every precondition the dismissed finding needs, because two findings bundled together almost always fail under different conditions and the covering fix closes only one | "Adds unnecessary complexity" |
| **FP-OUT-OF-SCOPE** | Valid concern but belongs in a separate change | State where it will be tracked (issue, todo, next PR) | YAGNI / scope creep |

Use the tag in the reply: "FP-ALREADY-HANDLED: null check happens in `auth/middleware.ts:42` before this handler runs. Keeping as-is." Structured tags prevent the "you're wrong because reasons" reply pattern and make future triage faster (if the same comment class keeps hitting `FP-CONVENTION`, the convention needs better documentation).

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
| Apologizing instead of fixing | [When pushback was wrong](./fix-and-handoff.md#when-your-pushback-was-wrong) |
| Thanking the reviewer instead of responding technically | Delete "Thanks" -- state the fix instead |
| Pushing back without evidence | Include the specific code path or test that proves your point |
| Batch-implementing then testing | Test after each individual fix |
| Can't verify the suggestion | Say so: "Can't verify this without [X]. Should I [investigate/ask/proceed]?" -- don't guess or implement blind |
| Treating your own fix as already-correct | A fix is new code -- re-review it adversarially, not just "does it address the finding?". Three shapes recur and the suite usually misses all three: a shared-helper default that violates an invariant you set elsewhere in the batch; a loosened guard now admitting bad input; a tightened matcher now dropping good values. Name one concrete bad/missed case for each shape the fix touches before claiming done |
| Refuting a finding from a subject it did not name | Reproduce on the exact method, input, and path the finding names. A reviewer often senses a class before pinning the minimal case, so if your fix handles their example, test two neighbours -- the sibling function, the mid-buffer variant -- before replying "mistaken". Probing an adjacent method is worse than useless: siblings are frequently protected by different layers. "Needs a resource failure, not reproducible" is not a dismissal until you have checked for a deterministic hard cap. Reply by separating the parts: confirm the example with evidence, then name the residual |

## Approved Response Templates

When feedback IS correct: "Verified -- [specific issue]. Implementing [specific fix]."
When feedback is partially correct: "The [X part] is right because [reason]. The [Y part] doesn't apply here because [evidence]."
When you need clarification: "Can you clarify [specific ambiguity]? The comment could mean [A] or [B], which changes the fix."
