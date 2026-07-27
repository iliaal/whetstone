---
name: ia-document-review
class: workflow
description: >-
  Structural review of documents for gaps, clarity, completeness, and
  organization. Use when a brainstorm, plan, spec, ADR, or any doc needs polish
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

These questions surface issues. Note findings without fixing yet.

## Step 3: Activate Review Lenses

Based on the document's content, activate specialized review perspectives. Scan for signals and apply matching lenses:

| Lens | Signals | What it checks |
|------|---------|----------------|
| **Product** | User-facing features, customer language, market claims, scope decisions | Problem framing, value proposition clarity, whether scope matches stated goals |
| **Design** | UI/UX references, user flows, wireframes, interaction descriptions | Flow completeness, interaction gaps, accessibility considerations |
| **Security** | Auth/authorization, API endpoints, PII, payments, tokens, encryption | Auth model gaps, data exposure risks, missing threat considerations |
| **Scope guardian** | Multiple priority tiers (P0/P1/P2), large requirement count (>8), stretch goals | Scope creep, premature abstractions, features disguised as requirements |
| **Adversarial** | >5 distinct requirements, explicit architectural decisions, high-stakes domains | Unstated assumptions, optimistic estimates, single points of failure, missing failure modes |

Activate a lens when ANY of its signals match. Most documents trigger 1-2 lenses; brainstorm notes may trigger none. When a lens is active, weave its checks into the assessment and evaluation steps rather than running it as a separate pass.

## Step 4: Evaluate

Score the document against these criteria:

| Criterion | What to Check |
|-----------|---------------|
| **Clarity** | Problem statement is clear, no vague language ("probably," "consider," "try to") |
| **Completeness** | Required sections present, constraints stated, open questions flagged |
| **Specificity** | Concrete enough for next step (brainstorm → can plan, plan → can implement) |
| **YAGNI** | No hypothetical features, simplest approach chosen |

If invoked within a workflow (after `/ia-brainstorm` or `/ia-plan`), also check:
- **User intent fidelity** -- Document reflects what was discussed, assumptions validated

## Step 5: Identify the Critical Improvement

Among everything found in Steps 2-4, does one issue stand out? If something would significantly improve the document's quality, this is the "must address" item. Highlight it prominently.

## Step 6: Make Changes

Present findings, then:

1. **Auto-fix** minor issues (vague language, formatting) without asking
2. **Ask approval** before substantive changes (restructuring, removing sections, changing meaning)
3. **Update** the document inline

### Rendering a finding for decision

The reader deciding on a finding does not have the document open and has not memorized its identifiers. This binds the approval track only (step 2 above) -- findings routed to auto-fix in step 1 skip it. Any finding presented for approval is rendered in this order:

1. **Consequence if unchanged** -- one sentence: what goes wrong, and for whom. No identifier the reader would have to look up.
2. **Recommended action**, marked unmistakably.
3. **Change intent** -- one sentence.
4. **Mechanism** -- at most two sentences, carrying at most two opaque anchors (defined below).

Anything deeper (file tracing, multi-hop call paths, competing call sites) is not printed; offer it in one closing line. Budget: two inline code spans per sentence, no diff blocks, raw code blocks only for genuinely additive content of five lines or less.

Classify opaque anchors by what they do, not by vocabulary:

- **Navigation anchors** (IDs the document itself defines) keep the ID and gain a short handle at first mention -- `R6 (suppress peer panels on low-stakes calls)`, never a bare `R6`.
- **Provenance anchors** (ticket IDs, PR numbers) get a role gloss only when the referenced event changes the decision; otherwise move them to the trace.
- **Mechanism anchors** (function, file, line names) translate to the role they play in the decision -- "the terminal-failure predicate" -- keeping the exact symbol only when precise scope is what the decision turns on.

A finding whose only route to a decision is "go read the section" has failed, however correct it is.

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

## Step 7: Reader Test (Optional)

For standalone documents that must be self-contained (onboarding guides, ADRs, external-facing docs), dispatch a zero-context sub-agent to simulate a first-time reader. The sub-agent has no conversation history — it sees only what a future reader would see.

**How to run the test:**

1. **Predict 5-10 reader questions** from the document's stated goals — one per major section or decision. Mix three kinds:
   - Concrete retrieval: "What command sets up the dev environment?"
   - Decision rationale: "Why did we pick X over Y?"
   - Ambiguity probe: "Could a reader interpret <specific phrase> in more than one way?"
2. **Dispatch a fresh sub-agent** with the document attached and the questions. No prior context, no session history.
3. **Compare the sub-agent's answers** against author intent. Also ask the sub-agent directly: "What feels ambiguous? What prior knowledge does this assume? Are there internal contradictions?"

**Interpret results:**

- Correct, confident answers → document is self-contained for that question.
- Wrong answer with high confidence → document actively misleads. Highest-priority fix.
- Hedged or "insufficient information" → the document has a gap the author didn't notice. Fill it.
- Sub-agent flags ambiguity the author didn't intend → reword for precision.

Skip for context-dependent docs (brainstorm notes, plan files, internal working docs) where the reader will always have prior context. The sub-agent test only adds value when the real reader has no other channel.

## Step 8: Offer Next Action

After changes are complete, ask:

1. **Refine again** - Another review pass
2. **Review complete** - Document is ready

### Iteration Guidance

After 2 refinement passes, recommend completion--diminishing returns are likely. If the user wants to continue, allow up to 4 passes total. After 4, stop and report "review converged -- further changes require new direction." Do not continue past 4 even on user request without a fresh framing.

**Withdraw what earlier answers already settled.** On pass 2 and later, judge each remaining finding against the decisions already made this session before presenting it. If an earlier answer resolves or contradicts it, do not re-raise it: say in one line what the finding was and which answer retired it, then move on, and record it as `withdrawn` in the summary with the retiring decision named. The distinction that matters -- a withdrawal caused by a **user decision** (a skip, a defer, an asserted fact) is durable and suppresses the finding on every later pass; a withdrawal caused by a **pending fix** is provisional, because the fix can fail or land in the wrong place, so a finding that regenerates on the next pass must resurface rather than stay suppressed. Evaluate lazily, at the moment the finding would have been presented; do not rescan after every answer. (Code review carries the same rule -- see `ia-code-review` on reconciling prior discussions.)

Return control to the caller (workflow or user) after selection.

## Constraints

- Fix targeted sections, don't rewrite the whole document. If the structure is fundamentally broken, surface the structural problem and ask for permission to restructure.
- Flag missing sections in the review, but don't add them. The user decides what to include.
- Keep changes minimal. If a paragraph needs tightening, tighten it. Don't expand scope.
- Review inline. No separate review files or metadata sections.

## Success Criteria

- Document read and scored on all four quality criteria
- Relevant review lenses activated and checks applied
- Critical improvements identified with specific suggestions
- User presented with clear next-action choice (refine or complete)
- Revised document saved if changes were approved
