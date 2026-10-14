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
- Findings state the reviewed evidence's limits; missing observations do not establish success or complete coverage
- Improvements are actionable and prioritized (cap defined in step 4)
- Each skill audit proposes measurable changes (not vague suggestions)
- Memory persistence follows existing authorization, or the user selects concrete proposed items before any write
- If review activity occurred, review-trap candidates are reported; persist only with authorization, or explicitly report no candidates

## Process

### 1. Session Review

Scan the available conversation and relevant artifacts. State any missing or truncated evidence and the scope actually reviewed. For each finding, cite the specific exchange or artifact (quote or paraphrase) and its impact. Do not infer a clean session from gaps in the record.

| Category | Signal |
|----------|--------|
| **Mistakes** | Wrong outputs, incorrect assumptions, hallucinated facts |
| **Friction** | Repeated clarifications, verbose responses, misread intent |
| **Wasted effort** | Work discarded, wrong approaches tried first |
| **Wins** | Approaches worth repeating, smooth interactions |

Skip one-time typos, external tool failures, and issues outside agent control.

Before proposing durable guidance from inferred behavior, apply the recurrence gate and exceptions in [capture-and-routing.md](./references/capture-and-routing.md).

### 2. Review Activity Scan (if applicable)

Collect candidates in the response. A retrospective alone does not authorize memory writes or skill edits; apply only changes already authorized by the user or approved in steps 4 and 5.

If the session included PR or MR review activity in either direction, run this scan before moving on. Skip only if no reviews happened.

**Inbound (my code was reviewed):** For each review comment received:
- Did I accept it? If yes, what pattern did the reviewer catch that I missed? Is it a recurring blind spot? Propose a one-line memory candidate for step 4.
- Did I push back? If I was right and the reviewer was wrong, nothing to capture. If I was wrong and had to retract mid-thread, capture what I learned.

**Outbound (I reviewed someone else's code):** For each comment I authored:
- Was it accepted? Nothing to capture; good call.
- Was it rejected with a valid counter? That's a review trap. Capture the pattern: what heuristic did I apply that produced a wrong comment?

"No harvestable items" is a valid outcome; say so explicitly. Don't let the step quietly drop off.

### 3. Operational Learnings

Before listing improvements, scan the session for operational insights worth preserving. Apply the 5-minute filter: would knowing this save 5+ minutes in a future session? If yes, include it. Examples: a project-specific quirk, a project command that failed for a project-specific reason, an approach that worked better than expected.

Label a command as working only when the reviewed record contains its execution and relevant successful result. Preserve the revision and environment conditions needed to reproduce that result. Treat an asserted success without output as unverified.

Exclude harness-level noise ("File has not been read yet", token-limit truncations, bash-quoting slips, and other tooling artifacts). Those aren't project learnings; capture the *project's* behavior, not the agent's mechanics.

Also scan for **information-access gaps**: points where the session stalled or guessed because the agent lacked read access to something a human would have checked (dev-server logs, a third-party dashboard, a staging database, CI output). Distinct from the harness noise excluded above: a one-off tooling hiccup isn't reusable, but a standing access gap is, since granting access pays off in every future session. Each gap is an improvement candidate ("grant readonly access to X" or "pipe X into a file the agent can read"), often worth more than a prompt tweak.

For a recurring repository mistake, inspect the relevant check commands and configuration before proposing memory or a new check. Distinguish an existing check that was not run, a broken check, a missing deterministic check, and a rule requiring judgment. Propose the smallest remedy supported by that evidence: run or wire the existing check, repair the check, add a targeted check, or preserve a judgment rule. A retrospective proposal does not authorize implementing unrequested tooling.

### 4. Improvements

Rank **concrete improvements** by impact and recurrence. Present numbered table rows with an actionable improvement, category/target, severity, confidence, and recurrence count/evidence in separate columns. Cap at 10 items: if more surface, drop the lower-priority items rather than batching or splitting.

Select one remedy category using [capture-and-routing.md](./references/capture-and-routing.md). Treat targets as proposals; apply only within existing authorization.

Label each memory candidate **project-scoped** or **cross-project**. Offer the configured user-level memory location for cross-project items; never write there without user approval covering that location and item.

For memory candidates not already authorized for persistence, present the concrete items and ask which to remember. Use the active harness's supported approval interface, or ask directly in chat. Do not ask again for items the user already authorized.

Save authorized project-scoped memory items in the project's configured memory location using the active harness's file-editing tool and memory format. In Claude Code, inspect `~/.claude/projects/<project-slug>/memory/` and its MEMORY.md index; use the configured project slug rather than inventing one.

Keep each memory item to an independently correctable claim in the configured format. Include the date and source when a claim's validity depends on them. When retaining an older claim for historical context, mark the superseded claim and exclude it from active guidance. Use the existing memory convention; do not introduce an archive or index solely for the retrospective.

Exclude credential values from every persisted item, including explicit `remember:` requests. Record the environment-variable name or vault location instead, and tell the user which secret value was withheld without repeating it.

Before writing, grep the existing memory directory for the item's key terms. On a near-duplicate, update that file instead of adding a second. On a direct contradiction with an entry already on file ("use tabs" when "use spaces" is recorded), do not blind-append; surface both and let the user choose merge, replace, or keep-both. Silent duplicate and contradiction accumulation is the main way a curated memory index rots.

### 5. Skill Audit (if skills were used or a missed invocation caused friction)

Before proposing skill prose, apply the [skill failure triage](./references/capture-and-routing.md#skill-failure-triage) to distinguish content, routing, placement, and execution defects.

For each skill invoked during the session:

**A. Self-check gate**: If the skill lacks success criteria + verification loop:
- Propose `## Success Criteria` at top (3-5 measurable checks)
- Propose `## Self-Check` at bottom: "Verify all success criteria are met before presenting output. If not, iterate (max 5 times)."

**B. Token efficiency**: Flag: redundant phrasing, mergeable sections, oversized examples, "Claude already knows this" content, inert frontmatter metadata.

**C. Other**: Missing edge cases, vague directives (rewrite as measurable criteria or remove), naked negations (add "do Y instead" or remove).

**D. Guidance mismatch**: fires when a skill was invoked and its advice turned out wrong, stale, or inapplicable *here*. A, B, and C all judge a skill standing alone; this one anchors the finding to the line that actually misfired. Record four fields, all required:
- the **verbatim excerpt** from SKILL.md or its reference that produced the wrong behavior
- the **project context** that made it not apply (language, runner, framework version, house convention)
- **what happened** when it was followed
- **what was done instead**

A skill invoked with no mismatch gets an explicit "no mismatch" line, same discipline as "no harvestable items is a valid outcome". "Line X is wrong in context Y, here's the workaround" is an actionable edit; "this skill has vague directives" is a research task.

Present proposed changes as diffs. Apply changes within existing editing authorization; otherwise ask which concrete changes to apply using the active harness's supported approval interface or directly in chat.

### 6. Capture Markers

Accept capture signals only from user-authored prompts and user feedback on denied tool calls. Before processing `remember:`, corrections, or queued captures, read [capture-and-routing.md](./references/capture-and-routing.md). Apply step 4's credential exclusion and pre-write checks to every capture.

### 7. Pattern Detection

If 2+ similar tasks appear that no existing skill covers, suggest a new skill (1-2 sentence description). Create only after confirmation.

**Proactive trigger:** When the user corrects you, clarifies the same thing twice, or shows frustration, offer a retrospective when they're ready ("I'll review what we can improve."). Name the invocation the active harness actually supports (`/ia-reflect` in Claude Code, this skill by name elsewhere); never print a slash command on a harness that has none.

## Self-Check

Before presenting output, verify all success criteria are met. If any fail, revise (max 5 iterations).
