# Pre-write scope synthesis

Read after substantive dialogue or when documenting a Standard/Deep design. Interaction mode and authority come from the skill entry point.

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

**Explicit headless mode:** compose the synthesis without requesting confirmation. Route inferred items to `## Assumptions` in the Phase 3 doc with validation methods; do not label them user-approved decisions. Stated requirements and non-goals retain their source. Report any decision beyond the caller's delegated authority instead of silently choosing it.

Skip Phase 2.5 entirely when Phase 0.2 detected requirements were already clear and the flow proceeded straight to summary without a Phase 1 dialogue. Path A handles every other Lightweight case.
