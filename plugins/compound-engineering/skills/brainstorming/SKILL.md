---
name: brainstorming
description: >-
  Pre-implementation brainstorming process: deep interview protocol, approach
  exploration, and design doc generation. Provides process knowledge for
  `/workflows:brainstorm`. Use when brainstorming inline without the full
  command workflow, or when clarifying ambiguous requirements.
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

**Assess whether brainstorming is needed:**

**Signals that requirements are clear:**
- User provided specific acceptance criteria
- User referenced existing patterns to follow
- User described exact behavior expected
- Scope is constrained and well-defined

**Signals that brainstorming is needed:**
- User used vague terms ("make it better", "add something like")
- Multiple reasonable interpretations exist
- Trade-offs haven't been discussed
- User seems unsure about the approach
- User described a solution ("build a dashboard") instead of a problem
- Request spans multiple independent subsystems -- decompose first (see Scope Decomposition below)

If requirements are clear, suggest: "Your requirements seem clear. Consider proceeding directly to planning or implementation."

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

Ask questions **one at a time** to understand the user's intent. Avoid overwhelming with multiple questions.

**Question Techniques:**

1. **Prefer multiple choice when natural options exist**
   - Good: "Should the notification be: (a) email only, (b) in-app only, or (c) both?"
   - Avoid: "How should users be notified?"

2. **Start broad, then narrow**
   - First: What is the core purpose?
   - Then: Who are the users?
   - Finally: What constraints exist?

3. **Validate assumptions explicitly**
   - "I'm assuming users will be logged in. Is that correct?"

4. **Ask about success criteria early**
   - "How will you know this feature is working well?"

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

### Deep Interview Layer

Apply the deep interview protocol on top of the baseline questions above. Assumption probing and contradiction tracking always run. Research-backed challenges and second-order effects run when the scope warrants it (multi-system changes, infrastructure decisions, technology selection).

**Assumption probing:** After each substantive answer, identify what the user assumed but didn't state. "You described X -- are you assuming Y is already in place?" Surface hidden dependencies and unstated constraints.

**Second-order effects:** For features that touch shared infrastructure or data models, ask what success creates downstream. "If this works and gets adopted, what pressure does it put on [related system]?"

**Research-backed challenges:** Fire background research on technology choices and claims. When findings contradict, challenge directly with citation. When findings support, briefly confirm to build confidence in the decision.

**Contradiction tracking:** If the user's answer contradicts something said earlier, flag it immediately: "Earlier you said X, but this implies Y. Which takes priority?"

**Anti-requirements:** When the user rejects an approach or says "definitely not X," capture the rejection and rationale inline with the related decision. Don't force this -- capture organically when it surfaces.

**Question clustering:** When probing a single dimension (e.g., data model, auth flow), ask 2-3 related questions together using AskUserQuestion's multi-question support. Switch to one-at-a-time when jumping between dimensions.

**Completeness assessment:** Track which dimensions have been explored. Before proposing to move to Phase 2, assess coverage and signal confidence: "We've covered purpose, users, and constraints well. Data flow and failure modes are still thin -- want to explore those, or proceed?"

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

### Phase 3: Capture the Design

Summarize key decisions in a structured format. For each major component, verify isolation and clarity: it must answer "what does it do, how do you use it, what does it depend on?" and be independently understandable and testable. If working in an existing codebase, note which existing patterns to follow and where targeted improvements fit naturally.

**Design Doc:** Save to `docs/brainstorms/YYYY-MM-DD-<topic>-brainstorm.md`. Required sections: What We're Building, Why This Approach, Key Decisions (with rationale), Open Questions, Next Steps. Collapse the Q&A interview log in a `<details>` block. Include YAML frontmatter with `date` and `topic`. Commit to git -- design decisions are project history.

### Phase 4: Spec Review

After writing the design doc, dispatch a `spec-flow-analyzer` agent with the document and original requirements (not session history). If issues found, fix and re-dispatch (max 3 iterations). Then present to the user for approval -- the user explicitly confirming the design is the gate to proceed.

### Phase 5: Handoff

Present clear options for what to do next:

1. **Proceed to planning** → Run `/workflows:plan` (pass the approved brainstorm doc as input)
2. **Refine further** → Continue exploring the design
3. **Done for now** → User will return later

## Anti-Patterns to Avoid

| Anti-Pattern | Better Approach |
|--------------|-----------------|
| Asking 5 questions at once | Ask one at a time |
| Jumping to implementation details | Stay focused on WHAT, not HOW |
| Proposing overly complex solutions | Start simple, add complexity only if needed |
| Ignoring existing codebase patterns | Research what exists first |
| Making assumptions without validating | State assumptions explicitly and confirm |
| Creating lengthy design documents | Keep it concise--details go in the plan |

## Integration

Brainstorming answers WHAT to build. Planning answers HOW. When brainstorm output exists, `workflows:plan` detects it and skips idea refinement.

- **Next step:** `workflows:plan` (always)
- **Predecessor:** user request or ambiguous feature description
