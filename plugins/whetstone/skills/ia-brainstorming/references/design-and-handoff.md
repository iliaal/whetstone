# Design capture and handoff

Read when writing or reviewing a durable design. The entry point’s authority boundary also applies to commits and handoff.

### Phase 3: Capture the Design

Summarize key decisions in a structured format. For each major component, verify isolation and clarity: it must answer "what does it do, how do you use it, what does it depend on?" and be independently understandable and testable. If working in an existing codebase, note which existing patterns to follow and where targeted improvements fit naturally.

**Design Doc:** Save to `docs/brainstorms/YYYY-MM-DD-<topic>-brainstorm.md`. Required sections: What We're Building, Why This Approach, Key Decisions (with rationale), Open Questions, Next Steps. Collapse the Q&A interview log in a `<details>` block. Include YAML frontmatter with `date` and `topic`. Commit to git; design decisions are project history.

**Settled vs. directive: don't re-litigate.** A decision the user made with the alternative and its trade-off in view is **settled**: record it in Key Decisions with its rationale and carry it forward. Do not re-ask it in Phase 3b, at planning, or during work. A cold **directive** (a choice asserted without anyone weighing it, e.g. "build it with X") earns exactly **one** in-pipeline challenge (one pass of the Phase 2 ideation lenses against that specific choice), then it too is recorded and not re-challenged at every downstream stage. A settled label never suppresses defect evidence: a real bug or infeasibility found *inside* a settled approach keeps full severity and is surfaced.

### Phase 3b: Spec Self-Review

Run this checklist before presenting the design doc. Any failure returns to Phase 2 or Phase 3, not Phase 4.

- **Placeholder scan**: no TBD, "figure out later", "appropriate error handling", bracketed gaps, or tasks without concrete criteria.
- **Internal consistency**: names, types, and verbs match across sections (no `createOrder()` in one place and `placeOrder()` in another).
- **Scope containment**: every decision traces back to a stated goal; otherwise cut or surface as explicit scope expansion.
- **Ambiguity sweep**: each Key Decision survives "could a reasonable implementer interpret this two ways?"
- **Assumption validation**: every assumption names its validation method ("we assume X; we'll confirm by Y").
- **Value sourcing**: enumerate every value the work must produce, compute, or display, and confirm the spec names each one's source (an input param, a stored field, a derivation from a named value, or a prior decision). A produced value with no named source is an owed design decision; surface it, don't invent it. Judge by positive enumeration, not introspection: "show the user's local day" that never says where the timezone comes from passes every other check yet hides an undecided source.
- **Non-goals present**: the explicit "Not Doing" list exists and is specific.

Silent pass is valid. Clean draft → move to Phase 4.

### Phase 4: Review and Handoff

Present the design doc to the user for approval. The user explicitly confirming the design is the gate to proceed. When invoked via `/ia-brainstorm`, the command handles spec review dispatch and next-step orchestration.

**Explicit headless mode:** return the design and unresolved assumptions to the caller. Handoff may continue only within the caller's delegated authority; report the design as caller-delegated, not user-approved.

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
- Interactive mode: user approves the spec before handoff. Explicit headless mode: caller-delegated decisions and remaining assumptions are identified.
- All open questions resolved or explicitly deferred with rationale

## Integration

Brainstorming answers WHAT to build. Planning answers HOW. When brainstorm output exists, `/ia-plan` (Claude Code) or the ia-planning skill detects it and skips idea refinement.

- **Next step:** planning, always (`/ia-plan` in Claude Code; the `ia-planning` skill elsewhere)
- **Threat modeling:** when the brainstorm involves auth, payments, external API surfaces, or multi-tenant data, suggest a `ia-security-sentinel` threat model before moving to planning. Catching trust boundary issues at the design stage prevents costly rework.
- **Predecessor:** user request or ambiguous feature description
