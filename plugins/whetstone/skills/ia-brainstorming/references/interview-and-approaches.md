# Interview and approach selection

Read when requirements need dialogue or multiple approaches need comparison. Headless execution follows the entry point’s caller-delegated decision scope.

### Phase 1: Understand the Idea

**User context calibration (before diving into the idea):**

Read signals from the user's first message to calibrate communication register:
- **Vocabulary**: Are they using technical terms (API, schema, migration) or describing experiences (it's slow, it breaks when...)?
- **Framing**: Are they describing a solution ("build a dashboard") or a problem ("I can't see what's happening")?
- **References**: Are they pointing to code, files, and patterns, or to analogies and comparisons ("something like Notion")?

Adjust question style accordingly. Technical users get architecture-level probing. Non-technical users get experience-level probing. Don't ask about this calibration -- just do it. If signals are ambiguous, default to the vocabulary the user is already using.

**Explore project context first:** Before asking questions, read existing files, docs, and recent commits related to the idea. Understanding what exists prevents asking questions the codebase already answers and grounds the conversation in reality. When the user's wording conflicts with what the code verifiably does ("the retry queue" when nothing retries; a table or endpoint named that doesn't exist), surface the conflict before treating the wording as settled -- silently adopting either side buries a requirements error.

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

See [deep-interview.md](./deep-interview.md) for deep interview techniques, including **rigor probes** (evidence/specificity/counterfactual/attachment as open-ended forced production, not menus), the **blindspot pass** for domains the user can't evaluate, and the **integration check** that fires before Phase 1 exit when combining stated answers + agent defaults produces an unsurfaced downstream effect.

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
