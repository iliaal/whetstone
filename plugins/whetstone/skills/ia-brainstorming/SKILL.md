---
name: ia-brainstorming
class: workflow
description: >-
  Pre-implementation exploration: deep interview, approach comparison, design
  doc. Use when exploring a vague feature idea, clarifying ambiguous
  requirements, or comparing approaches before coding. For the full workflow,
  use `/ia-brainstorm`.
---

# Brainstorming

Clarify **WHAT** to build before **HOW** to build it.

## Hard Gate

**No implementation until the design is approved.** Brainstorming produces a design document, not code. Do not invoke implementation skills, write production code, or create files outside `docs/brainstorms/` until the user explicitly approves the design and moves to planning.

## Core Process

### Phase 0: Assess and Ground

Before diving into questions, do two things:

**Ground in the codebase (when applicable).** If the brainstorm relates to existing code, read the relevant modules, patterns, and constraints before generating options. This prevents suggesting approaches that conflict with the actual architecture. Skip for purely abstract brainstorms (tech choices, product direction) where no codebase context applies.

**Right-size the artifact.** Match ceremony to problem size. If the brainstorm resolves in 3 messages, don't force a formal design doc -- a summary comment is enough. If it spans multiple sessions and touches architecture, write the full Phase 3 doc. No ceremony tax.

**Assess whether brainstorming is needed.** Brainstorm when any of these fire: vague terms ("make it better", "add something like"), multiple reasonable interpretations, undiscussed trade-offs, user uncertainty, solution-framing instead of problem-framing ("build a dashboard"), or request spanning multiple independent subsystems (decompose first — see Scope Decomposition below). Otherwise, requirements are clear — suggest: "Your requirements seem clear. Consider proceeding directly to planning or implementation."

### Scope Decomposition Gate

If the request describes multiple independent subsystems (e.g., "build a platform with chat, file storage, billing, and analytics"), flag this immediately. Don't spend questions refining details of a project that needs decomposition first.

1. Identify the independent pieces and how they relate
2. Determine build order (dependencies, shared infrastructure first)
3. Brainstorm the first sub-project through the normal Phase 1-3 flow
4. Each sub-project gets its own spec -> plan -> implementation cycle

### Phase 1: Understand the Idea

**User context calibration (before diving into the idea):**

Read signals from the user's first message to calibrate communication register:
- **Vocabulary**: Are they using technical terms (API, schema, migration) or describing experiences (it's slow, it breaks when...)?
- **Framing**: Are they describing a solution ("build a dashboard") or a problem ("I can't see what's happening")?
- **References**: Are they pointing to code, files, and patterns, or to analogies and comparisons ("something like Notion")?

Adjust question style accordingly. Technical users get architecture-level probing. Non-technical users get experience-level probing. Don't ask about this calibration -- just do it. If signals are ambiguous, default to the vocabulary the user is already using.

**Explore project context first:** Before asking questions, read existing files, docs, and recent commits related to the idea. Understanding what exists prevents asking questions the codebase already answers and grounds the conversation in reality.

Ask questions **one at a time** by default. When probing a single dimension (e.g., data model, auth flow), clustering 2-3 related questions together is acceptable.

**Info-dump gate (when user offers rich context up-front):** if the user's first message is substantial (>200 words, or dumps requirements in stream-of-consciousness), resist the urge to ask questions one-at-a-time. Instead, respond with 5-10 **numbered clarifying questions** the user can answer in shorthand (`1: yes, 2: channel #ops, 3: no because backwards compat`). Pick questions that remove ambiguity, not questions that show you read the dump. Exit this batched mode when the user's answers show they can be asked about edge cases without basics being explained back to them.

Example after a spec dump:

```
Before I propose approaches, quick clarifications:

1. Auth — SSO (which provider?) or username/password?
2. Sync or async for the webhook delivery?
3. Which of the three integrations is P0?
4. "Fast enough" in the spec — what's the actual number?

Answer whichever you know; leave blanks for the rest.
```

**Question Techniques:**

1. **Prefer multiple choice when natural options exist.** Good: "Notification: (a) email, (b) in-app, (c) both?" Avoid: "How should users be notified?"
2. **Start broad, then narrow.** Core purpose → users → constraints.
3. **Validate assumptions and probe success early.** "I'm assuming users are logged in — correct?" / "How will you know this is working?"

**Key Topics to Explore:**

| Topic | Example Questions |
|-------|-------------------|
| Purpose | What problem does this solve? What's the motivation? |
| Users | Who uses this? What's their context? |
| Constraints | Any technical limitations? Timeline? Dependencies? |
| Success | How will you measure success? What's the happy path? |
| Edge Cases | What shouldn't happen? Any error states to consider? |
| Existing Patterns | Are there similar features in the codebase to follow? |
| Non-goals | What is explicitly NOT in scope? |

See [deep-interview.md](./references/deep-interview.md) for deep interview techniques, including **rigor probes** (evidence/specificity/counterfactual/attachment as open-ended forced production, not menus) and the **integration check** that fires before Phase 1 exit when combining stated answers + agent defaults produces an unsurfaced downstream effect.

**Exit Condition:** Continue until the idea is clear OR user says "proceed". Before moving to Phase 2, summarize understanding in 3-5 bullets and confirm with the user.

### Phase 2: Explore Approaches

After understanding the idea, propose 2-3 concrete approaches.

**Structure for Each Approach:**

```markdown
### Approach A: [Name]

[2-3 sentence description]

**Pros:**
- [Benefit 1]
- [Benefit 2]

**Cons:**
- [Drawback 1]
- [Drawback 2]

**Best when:** [Circumstances where this approach shines]
```

**Guidelines:**
- Lead with a recommendation and explain why
- Be honest about trade-offs
- Consider YAGNI--simpler is usually better
- Reference codebase patterns when relevant
- If no approach is accepted after 2 rounds, ask the user to describe their preferred direction directly

**Ideation lenses** (use 2-3 to stress-test approaches when the design space is wide):
- **Inversion**: What if we solved the opposite problem?
- **Constraint removal**: What would we build if [biggest constraint] didn't exist?
- **Simplification**: What's the version that ships in a day?
- **10x version**: What if this needed to handle 10x the scale?
- **Expert lens**: How would [domain expert] approach this?

**"Not Doing" list:** Include an explicit list of what the chosen approach will NOT do. Focus is about saying no to good ideas. Make the trade-offs visible so they're a deliberate choice, not an oversight.

**Assumptions with validation:** For each key assumption in the chosen approach, state how to test it. Not just "we assume X" but "we assume X -- we'll know by [validation method]."

### Phase 2.5: Pre-Write Scope Synthesis

Surface the scope interpretation so the user can correct it before Phase 3 writes the design doc. Phase 2.5 catches scope misalignment before the doc is written; Phase 3b catches drafting issues after.

**Two-stage shape: internal draft, then chat-time scoping synthesis.** Compose in two stages. Stage 1 is an internal three-bucket thinking pass (Stated / Inferred / Out of scope) for comprehensive scope analysis. Stage 2 is what the user sees — shaped like what two product collaborators would confirm before writing a PRD. The internal draft never reaches the user verbatim; it routes into the Phase 3 doc body.

**Stage 1 — internal three-bucket draft (thinking, not output):**
- **Stated** — what the user said directly. Explicit user-language anchors.
- **Inferred** — gaps the agent filled with assumptions. Most actionable bucket; bets the user can correct.
- **Out of scope** — deliberately excluded items.

Use this as a thinking step. Do not paste it into chat.

**Stage 2 — user-facing scoping synthesis.** Up to four named sections, each render-conditional. Empty sections are omitted, not padded:

1. **What we're building** (always present) — 1-3 sentences. The shape that emerged from dialogue, forward-looking, plain words. Not a transcript of "you said X".
2. **Key trade-offs** (conditional) — 1-3 bullets, each with a brief why. Render only when real trade-offs were made.
3. **What's not in scope** (conditional) — 1-3 bullets, or fold into a sentence. Render only when deferred items would surprise a downstream reader if absent.
4. **Call-outs** (conditional) — 0-3 bullets. Residual forks the dialogue didn't resolve: post-dialogue consequences, silent agent inferences, or — in pre-loaded contexts — scope bets the user is seeing for the first time. Not "questions the agent could have asked during Phase 1 but didn't" — if a call-out reads like a missed dialogue question, Phase 1's integration check failed; flag the gap.

Close with: *"Confirm and I'll write the design doc next. Or tell me what to change."*

**Path A vs Path B gate.** Routing depends on TWO signals: (1) did any *blocking* question fire before Phase 2.5? AND (2) what tier did Phase 0 classify? Blocking questions = scope disambiguation, dialogue probes, approach selection menus. Internal classification and pressure-tests do not count.

- **Path A** — Lightweight tier AND no blocking questions fired → announce-mode. Emit "What we're building" prose only (no other sections, no confirmation question), then proceed to Phase 3 doc-write in the same turn. Lightweight Path A docs are short; post-hoc revision is cheap.
- **Path B** — Standard/Deep tier OR any blocking question fired → full synthesis with confirmation gate. Two scenarios fire Path B: the user invested answer-time in dialogue, or pre-loaded substantive scope content. Either way, the substance earns a real checkpoint. The tier guard catches pre-loaded Deep brainstorms that would otherwise shortcut via the no-questions branch.

**Keep tests per section.** Each conditional section has its own keep test; failing items dissolve into the internal draft only.
- **Trade-offs**: would the user be surprised if I didn't surface this acknowledgment? Mechanical or inevitable choices fail.
- **Deferred**: is a reasonable downstream reader likely to ask "why isn't X here?" Mechanical excludes fail.
- **Call-outs**: two-step test. (1) Affirmability: would the user need to read code to evaluate this? If yes, it's doc-body content — cut. (2) Keep only if it's a real scope fork, non-obvious inclusion/exclusion, cheap-now-expensive-later correction, or non-obvious consequence of combined multi-turn answers. (3) Phase 1 boundary: if the call-out depends only on Phase 1 facts (no Phase 2 approach, no later-surfaced default), Phase 1's integration check failed — cut and revisit Phase 1. Call-outs catch what Phase 1 *couldn't* surface, not what it *should have*.

Cut re-statements of Q&A turns, re-statements of the picked Phase 2 approach, mechanical items, and implementation choices that settle during planning.

**Bullet budget across sections 2-4 combined.** Heuristic, not law — the real discipline is each section's keep test:

| Tier | Typical total | Hard ceiling |
|---|---|---|
| Lightweight | 0-1 | 2 |
| Standard | 2-4 | 5 |
| Deep | 3-7 | 9 |

Above the ceiling means the synthesis is mis-shapen — re-cut at a higher level of abstraction, do not raise the cap.

**Detail level: conversational, not documentary.** 1 line ideally, 2 max. Bullets that need semicolons stringing clauses or an internal list are two decisions sharing a bullet — split or drop.

**Re-present after revision; write only on confirm.** If the user revises any bullet (even trivially), integrate the change, re-present, and wait for explicit confirmation. A revision is not a confirmation.

**Headless mode** (`/ia-lfg` or any `disable-model-invocation` context): compose the synthesis but skip the confirmation step. Route internal-draft Inferred items to a `## Assumptions` section in the Phase 3 doc — explicitly labeled as un-validated bets — instead of into Key Decisions. Stated routes to Requirements; Out-of-scope routes to Non-Goals.

Skip Phase 2.5 entirely when Phase 0.2 detected requirements were already clear and the flow proceeded straight to summary without a Phase 1 dialogue. Path A handles every other Lightweight case.

### Phase 3: Capture the Design

Summarize key decisions in a structured format. For each major component, verify isolation and clarity: it must answer "what does it do, how do you use it, what does it depend on?" and be independently understandable and testable. If working in an existing codebase, note which existing patterns to follow and where targeted improvements fit naturally.

**Design Doc:** Save to `docs/brainstorms/YYYY-MM-DD-<topic>-brainstorm.md`. Required sections: What We're Building, Why This Approach, Key Decisions (with rationale), Open Questions, Next Steps. Collapse the Q&A interview log in a `<details>` block. Include YAML frontmatter with `date` and `topic`. Commit to git -- design decisions are project history.

### Phase 3b: Spec Self-Review

Run this checklist before presenting the design doc. Any failure returns to Phase 2 or Phase 3, not Phase 4.

- **Placeholder scan**: no TBD, "figure out later", "appropriate error handling", bracketed gaps, or tasks without concrete criteria.
- **Internal consistency**: names, types, and verbs match across sections (no `createOrder()` in one place and `placeOrder()` in another).
- **Scope containment**: every decision traces back to a stated goal; otherwise cut or surface as explicit scope expansion.
- **Ambiguity sweep**: each Key Decision survives "could a reasonable implementer interpret this two ways?"
- **Assumption validation**: every assumption names its validation method ("we assume X — we'll confirm by Y").
- **Non-goals present**: the explicit "Not Doing" list exists and is specific.

Silent pass is valid. Clean draft → move to Phase 4.

### Phase 4: Review and Handoff

Present the design doc to the user for approval. The user explicitly confirming the design is the gate to proceed. When invoked via `/ia-brainstorm`, the command handles spec review dispatch and next-step orchestration.

**Headless mode** (invoked via `/ia-lfg` or any `disable-model-invocation` context): skip the user approval step at Phase 4 — same carve-out as Phase 2.5. The doc-write completes; the artifact is the audit surface for downstream review (`/ia-plan`, PR review, the `ia-document-review` skill), not chat confirmation.

## Anti-Patterns to Avoid

| Anti-Pattern | Better Approach |
|--------------|-----------------|
| Asking 5 questions at once | Ask one at a time across dimensions; cluster 2-3 within a dimension |
| Jumping to implementation details | Stay focused on WHAT, not HOW |
| Proposing overly complex solutions | Start simple, add complexity only if needed |
| Ignoring existing codebase patterns | Research what exists first |
| Making assumptions without validating | State assumptions explicitly and confirm |
| Creating lengthy design documents | Keep it concise--details go in the plan |

## Success Criteria

- Design doc saved to `docs/brainstorms/YYYY-MM-DD-<topic>-brainstorm.md`
- User explicitly approves the spec before handoff to planning
- All open questions resolved or explicitly deferred with rationale

## Integration

Brainstorming answers WHAT to build. Planning answers HOW. When brainstorm output exists, `/ia-plan` detects it and skips idea refinement.

- **Next step:** `/ia-plan` (always)
- **Threat modeling:** when the brainstorm involves auth, payments, external API surfaces, or multi-tenant data, suggest a `ia-security-sentinel` threat model before moving to planning. Catching trust boundary issues at the design stage prevents costly rework.
- **Predecessor:** user request or ambiguous feature description
