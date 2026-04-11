---
name: reflect
description: >-
  Session retrospective and skill audit. Use when asked to reflect, do a
  retrospective, review lessons learned, audit what went well or wrong, or
  review session effectiveness.
---

# Reflect

## Success Criteria

- Every mistake/friction point cites the specific moment and its impact
- Improvements are actionable, prioritized, and <= 10 items
- Each skill audit proposes measurable changes (not vague suggestions)
- User is asked which items to persist to memory
- If review activity occurred, review-trap patterns are captured to persistent memory, or explicitly marked as "none"

## Process

### 1. Session Review

Scan the full conversation. For each finding, cite the specific exchange (quote or paraphrase) and its impact.

| Category | Signal |
|----------|--------|
| **Mistakes** | Wrong outputs, incorrect assumptions, hallucinated facts |
| **Friction** | Repeated clarifications, verbose responses, misread intent |
| **Wasted effort** | Work discarded, wrong approaches tried first |
| **Wins** | Approaches worth repeating, smooth interactions |

Skip one-time typos, external tool failures, and issues outside agent control.

### 2. Review Activity Scan (if applicable)

If the session included PR or MR review activity in either direction, run this scan before moving on. Skip only if no reviews happened.

**Inbound (my code was reviewed):** For each review comment received:
- Did I accept it? If yes, what pattern did the reviewer catch that I missed? Is it a recurring blind spot? Capture the one-liner to persistent memory.
- Did I push back? If I was right and the reviewer was wrong, nothing to capture. If I was wrong and had to retract mid-thread, capture what I learned.

**Outbound (I reviewed someone else's code):** For each comment I authored:
- Was it accepted? Nothing to capture -- good call.
- Was it rejected with a valid counter? That's a review trap. Capture the pattern: what heuristic did I apply that produced a wrong comment?

"No harvestable items" is a valid outcome -- say so explicitly. Don't let the step quietly drop off.

### 3. Operational Learnings

Before listing improvements, scan the session for operational insights worth preserving. Apply the 5-minute filter: would knowing this save 5+ minutes in a future session? If yes, include it. Examples: a project-specific quirk, a command that failed unexpectedly, an approach that worked better than expected.

### 4. Improvements

Numbered list of **concrete improvements**, ranked by impact. Each item: one sentence, imperative, actionable. Cap at 10.

Ask: *"Which of these should I remember for future chats?"*

Save approved items to memory files at `~/.claude/projects/<project-slug>/memory/` (replace `<project-slug>` with the slug matching the current working directory, e.g., `-home-ilia-ai-compound-engineering-plugin`) using the Write tool with proper frontmatter (see MEMORY.md index).

### 5. Skill Audit (if skills were used)

For each skill invoked during the session:

**A. Self-check gate** -- If the skill lacks success criteria + verification loop:
- Add `## Success Criteria` at top (3-5 measurable checks)
- Add `## Self-Check` at bottom: "Verify all success criteria are met before presenting output. If not, iterate (max 5 times)."

**B. Token efficiency** -- Flag: redundant phrasing, mergeable sections, oversized examples, "Claude already knows this" content, inert frontmatter metadata.

**C. Other** -- Missing edge cases, vague directives (rewrite as measurable criteria or remove), naked negations (add "do Y instead" or remove).

Present proposed changes as diffs. Ask: *"Apply these? (all / pick / skip)"*

### 6. Pattern Detection

If 2+ similar tasks appear that no existing skill covers, suggest a new skill (1-2 sentence description). Create only after confirmation.

**Proactive trigger:** When the user corrects you, clarifies the same thing twice, or shows frustration, append: "Tip: Type `/reflect` when you're ready -- I'll review what we can improve."

## Self-Check

Before presenting output, verify all success criteria are met. If any fail, revise (max 5 iterations).
