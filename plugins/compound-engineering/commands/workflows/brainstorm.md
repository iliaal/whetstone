---
name: workflows:brainstorm
description: Explore requirements and approaches through collaborative dialogue before planning implementation
argument-hint: "[feature idea or problem to explore]"
---

# Brainstorm a Feature or Improvement

**Note: The current year is 2026.** Use this when dating brainstorm documents.

**Process knowledge:** Follow the `brainstorming` skill for all process details -- clarity assessment, question techniques, approach exploration, YAGNI principles, scope decomposition, and spec review.

## Feature Description

<feature_description> #$ARGUMENTS </feature_description>

**If the feature description above is empty, ask the user:** "What would you like to explore? Please describe the feature, problem, or improvement you're thinking about."

Do not proceed until you have a feature description from the user.

## Execution Flow

### Phase 0: Assess Requirements Clarity

Per the `brainstorming` skill Phase 0 -- evaluate whether brainstorming is needed.

**If requirements are already clear:**
Use **AskUserQuestion tool** to suggest: "Your requirements seem detailed enough to proceed directly to planning. Should I run `/workflows:plan` instead, or would you like to explore the idea further?"

### Phase 1: Understand the Idea

**1.1 Repository Research (Lightweight)**

- Task repo-research-analyst("Understand existing patterns related to: <feature_description>")

Focus on: similar features, established patterns, CLAUDE.md guidance.

**1.2 Collaborative Dialogue**

Use the **AskUserQuestion tool** to ask questions **one at a time**. Follow the `brainstorming` skill Phase 1 for question techniques and topic coverage.

**Exit condition:** Continue until the idea is clear OR user says "proceed."

### Phase 2: Explore Approaches

Per the `brainstorming` skill Phase 2. Use **AskUserQuestion tool** to ask which approach the user prefers.

### Phase 3: Capture the Design

Write to `docs/brainstorms/YYYY-MM-DD-<topic>-brainstorm.md` using the template from the `brainstorming` skill Phase 3. Ensure directory exists before writing.

**IMPORTANT:** Before proceeding, check for Open Questions. If any exist, ask the user about each one using AskUserQuestion. Move resolved questions to a "Resolved Questions" section.

### Phase 4: Spec Review

Per the `brainstorming` skill Phase 4 -- dispatch spec-reviewer subagent, iterate up to 3 times, then present to user for approval.

### Phase 5: Handoff

Use **AskUserQuestion tool**: "Brainstorm captured. What would you like to do next?"

**Options:**
1. **Review and refine** -- Load the `document-review` skill and apply it to the brainstorm document
2. **Proceed to planning** -- Run `/workflows:plan` (will auto-detect this brainstorm)
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

Next: Run `/workflows:plan` when ready to implement.
```

NEVER CODE! Just explore and document decisions.
