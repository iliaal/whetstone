---
name: document-review
description: >-
  Structural quality review of existing documents -- checks for gaps, clarity,
  completeness, and organization. Use when a brainstorm or plan doc needs polish
  before the next workflow step. For exploring new ideas from scratch, use
  brainstorming instead.
---

# Document Review

Improve brainstorm or plan documents through structured review.

## Step 1: Get the Document

**If a document path is provided:** Read it, then proceed to Step 2.

**If no document is specified:** Ask which document to review, or look for the most recent brainstorm/plan in `docs/brainstorms/` or `docs/plans/`.

## Step 2: Assess

Read through the document and ask:

- What is unclear?
- What is unnecessary?
- What decision is being avoided?
- What assumptions are unstated?
- Where could scope accidentally expand?
- Is this technically feasible with the current architecture?
- Are there security implications in what's proposed?

These questions surface issues. Don't fix yet--just note what you find.

## Step 3: Evaluate

Score the document against these criteria:

| Criterion | What to Check |
|-----------|---------------|
| **Clarity** | Problem statement is clear, no vague language ("probably," "consider," "try to") |
| **Completeness** | Required sections present, constraints stated, open questions flagged |
| **Specificity** | Concrete enough for next step (brainstorm → can plan, plan → can implement) |
| **YAGNI** | No hypothetical features, simplest approach chosen |

If invoked within a workflow (after `/workflows:brainstorm` or `/workflows:plan`), also check:
- **User intent fidelity** -- Document reflects what was discussed, assumptions validated

## Step 4: Identify the Critical Improvement

Among everything found in Steps 2-3, does one issue stand out? If something would significantly improve the document's quality, this is the "must address" item. Highlight it prominently.

## Step 5: Make Changes

Present your findings, then:

1. **Auto-fix** minor issues (vague language, formatting) without asking
2. **Ask approval** before substantive changes (restructuring, removing sections, changing meaning)
3. **Update** the document inline--no separate files, no metadata sections

### Simplification Guidance

Simplification is purposeful removal of unnecessary complexity, not shortening for its own sake.

**Simplify when:**
- Content serves hypothetical future needs, not current ones
- Sections repeat information already covered elsewhere
- Detail exceeds what's needed to take the next step
- Abstractions or structure add overhead without clarity

**Don't simplify:**
- Constraints or edge cases that affect implementation
- Rationale that explains why alternatives were rejected
- Open questions that need resolution

## Step 5b: Reader Test (Optional)

For standalone documents that must be self-contained (onboarding guides, ADRs, external-facing docs), optionally dispatch a zero-context sub-agent with only the document and 5 reader questions. The sub-agent has no conversation history -- it sees only what a future reader would see.

If the sub-agent can answer the questions correctly, the document is self-contained. If it can't, the document has gaps that need filling. This is the "fresh eyes" test automated.

Skip for context-dependent docs (brainstorm notes, plan files, internal working docs) where the reader will have prior context.

## Step 6: Offer Next Action

After changes are complete, ask:

1. **Refine again** - Another review pass
2. **Review complete** - Document is ready

### Iteration Guidance

After 2 refinement passes, recommend completion--diminishing returns are likely. But if the user wants to continue, allow it.

Return control to the caller (workflow or user) after selection.

## Constraints

- Fix targeted sections, don't rewrite the whole document. If the structure is fundamentally broken, surface the structural problem and ask for permission to restructure.
- Flag missing sections in your review, but don't add them. The user decides what to include.
- Keep changes minimal. If a paragraph needs tightening, tighten it. Don't expand scope.
- Review inline. No separate review files or metadata sections.
