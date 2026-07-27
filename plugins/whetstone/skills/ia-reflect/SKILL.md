---
name: ia-reflect
class: tool
description: >-
  Session retrospective and skill audit. Use when asked to reflect, do a
  retrospective, review lessons learned, audit what went well or wrong, or
  review session effectiveness.
---

# Reflect

## Success Criteria

- Every mistake/friction point cites the specific moment and its impact
- Improvements are actionable and prioritized (cap defined in step 4)
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

Before listing improvements, scan the session for operational insights worth preserving. Apply the 5-minute filter: would knowing this save 5+ minutes in a future session? If yes, include it. Examples: a project-specific quirk, a project command that failed for a project-specific reason, an approach that worked better than expected.

Exclude harness-level noise — "File has not been read yet", token-limit truncations, bash-quoting slips, and other tooling artifacts. Those aren't project learnings; capture the *project's* behavior, not the agent's mechanics.

### 4. Improvements

Numbered list of **concrete improvements**, ranked by impact. Each item: one sentence, imperative, actionable. Cap at 10 items: if more surface, the bottom items are noise -- drop them rather than batching or splitting.

Ask: *"Which of these should I remember for future chats?"*

Save approved items to memory files at `~/.claude/projects/<project-slug>/memory/` (replace `<project-slug>` with the slug matching the current working directory, e.g., `-home-ilia-ai-whetstone`) using the Write tool with proper frontmatter (see MEMORY.md index).

Before writing, grep the existing memory directory for the item's key terms. On a near-duplicate, update that file instead of adding a second. On a direct contradiction with an entry already on file ("use tabs" when "use spaces" is recorded), do not blind-append — surface both and let the user choose merge, replace, or keep-both. Silent duplicate and contradiction accumulation is the main way a curated memory index rots.

### 5. Skill Audit (if skills were used)

For each skill invoked during the session:

**A. Self-check gate** -- If the skill lacks success criteria + verification loop:
- Add `## Success Criteria` at top (3-5 measurable checks)
- Add `## Self-Check` at bottom: "Verify all success criteria are met before presenting output. If not, iterate (max 5 times)."

**B. Token efficiency** -- Flag: redundant phrasing, mergeable sections, oversized examples, "Claude already knows this" content, inert frontmatter metadata.

**C. Other** -- Missing edge cases, vague directives (rewrite as measurable criteria or remove), naked negations (add "do Y instead" or remove).

**D. Guidance mismatch** -- fires when a skill was invoked and its advice turned out wrong, stale, or inapplicable *here*. A, B, and C all judge a skill standing alone; this one anchors the finding to the line that actually misfired. Record four fields, all required:
- the **verbatim excerpt** from SKILL.md or its reference that produced the wrong behavior
- the **project context** that made it not apply (language, runner, framework version, house convention)
- **what happened** when it was followed
- **what was done instead**

A skill invoked with no mismatch gets an explicit "no mismatch" line, same discipline as "no harvestable items is a valid outcome". "Line X is wrong in context Y, here's the workaround" is an actionable edit; "this skill has vague directives" is a research task.

Present proposed changes as diffs. Ask: *"Apply these? (all / pick / skip)"*

### 6. Capture Markers

**The `remember:` prefix** is the highest-confidence capture signal. When the user writes a message beginning with `remember:`, treat everything after the colon as a memory candidate — no interpretation required. Save directly to the appropriate memory file with a one-line summary and the user's exact phrasing. "Directly" waives interpretation, not the step-4 pre-write check: still grep existing memory for duplicates and contradictions before writing (a `remember:` that contradicts a recorded entry gets the same merge/replace/keep-both handling). Example: `remember: we never use Pest, always PHPUnit` → save to `feedback_phpunit_over_pest.md`.

**Correction patterns to watch for** (lower-confidence, batch these for review at `/ia-reflect` time):
- "no, use X" / "actually, X" / "don't use Y, use X"
- "stop doing X" / "never X"
- "that's wrong — the right way is..."
- repeated clarifications of the same thing within a session

**Optional capture hook**: a `UserPromptSubmit` hook can pattern-match the markers above into `~/.claude/learnings-queue.json` as the user types, so `/ia-reflect` processes the queue deterministically instead of re-scanning the full transcript. Not shipped with this skill; document the convention and leave implementation to users who need it.

### 7. Pattern Detection

If 2+ similar tasks appear that no existing skill covers, suggest a new skill (1-2 sentence description). Create only after confirmation.

**Proactive trigger:** When the user corrects you, clarifies the same thing twice, or shows frustration, offer a retrospective when they're ready -- "I'll review what we can improve." Name the invocation the active harness actually supports (`/ia-reflect` in Claude Code, this skill by name elsewhere); never print a slash command on a harness that has none.

## Self-Check

Before presenting output, verify all success criteria are met. If any fail, revise (max 5 iterations).
