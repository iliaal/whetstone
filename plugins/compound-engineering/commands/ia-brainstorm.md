---
name: ia-brainstorm
description: Explore requirements and approaches through collaborative dialogue before planning implementation
argument-hint: "[feature idea or problem to explore]"
---

# Brainstorm a Feature or Improvement

**Process knowledge:** Follow the `ia-brainstorming` skill for all process details -- clarity assessment, question techniques, approach exploration, YAGNI principles, scope decomposition, and spec review.

## Feature Description

<feature_description> #$ARGUMENTS </feature_description>

**If the feature description above is empty, ask the user:** "What would you like to explore? Please describe the feature, problem, or improvement you're thinking about."

Do not proceed until you have a feature description from the user.

## Execution Flow

### Phase 0: Assess Requirements Clarity

Per the `ia-brainstorming` skill Phase 0 -- evaluate whether brainstorming is needed.

**If requirements are already clear:**
Use **AskUserQuestion tool** to suggest: "Your requirements seem detailed enough to proceed directly to planning. Should I run `/ia-plan` instead, or would you like to explore the idea further?"

### Phase 1: Understand the Idea

**1.1 Repository Research (Lightweight)**

- Task ia-repo-research-analyst("Understand existing patterns related to: <feature_description>")

Focus on: similar features, established patterns, CLAUDE.md guidance.

**1.2 Collaborative Dialogue**

Use the **AskUserQuestion tool** to ask questions one at a time per the `ia-brainstorming` skill Phase 1.

### Phase 2-3: Explore and Capture

Per `ia-brainstorming` skill Phases 2-3. Use AskUserQuestion for approach selection. Write the design to `docs/brainstorms/YYYY-MM-DD-<topic>-brainstorm.md` (ensure directory exists). Before moving to Phase 4, resolve any Open Questions via AskUserQuestion and move them to a "Resolved Questions" section.

### Phase 4: Spec Review

Per the `ia-brainstorming` skill Phase 4 -- dispatch `ia-spec-flow-analyzer` agent, iterate up to 3 times, then present to user for approval.

### Phase 5: Handoff

Use **AskUserQuestion tool**: "Brainstorm captured. What would you like to do next?"

**Options:**
1. **Review and refine** -- Load the `ia-document-review` skill and apply it to the brainstorm document
2. **Proceed to planning** -- Run `/ia-plan` (will auto-detect this brainstorm)
3. **Ask more questions** -- Return to Phase 1.2 and probe deeper
4. **Done for now** -- Return later

**If "Review and refine":** After document-review completes, offer: Move to planning / Done for now.

## Output Summary

When complete, display:

```
Brainstorm complete!

Document: docs/brainstorms/YYYY-MM-DD-<topic>-brainstorm.md

Key decisions:
- [Decision 1]
- [Decision 2]

Next: Run `/ia-plan` when ready to implement.
```

The `ia-brainstorming` skill's Hard Gate prohibits code writing during this workflow — the skill enforces this, don't restate it here.
