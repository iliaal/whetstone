---
name: writing
description: >-
  Prose editing, rewriting, and humanizing text for natural tone. Use when asked
  to write, rewrite, edit, humanize, proofread, fix tone, or remove AI language.
  For copy, docs, blog posts, emails, or PRs.
---

# Human Writing

## Core Principles

- **Active voice**: "We shipped the fix" not "The fix was shipped"
- **Name the actor**: Every sentence needs a human subject doing something. Inanimate objects don't fix bugs, shift cultures, or tell us anything — a person does.
- **Specific over vague**: "Cut reporting from 4 hours to 15 minutes" not "Save time"
- **Simple words**: "Use" not "utilize", "help" not "facilitate", "start" not "initiate"
- **Positive form**: Say what it is, not what it isn't — "Ignore" not "Do not pay attention to"
- **Confident**: Cut "almost", "very", "really", "quite", "arguably", and all -ly adverbs
- **Concrete**: Name the thing, state the number, cite the source
- **Omit needless words**: "Because" not "due to the fact that"; "Now" not "at this point in time"; "Can" not "has the ability to"
- **Use contractions**: "don't", "won't", "it's", "they're" — uncontracted forms are a major AI tell
- **Put the reader in the room**: "You" beats "People." Specifics beat abstractions. Avoid narrating from a distance.

## AI Patterns — Kill on Sight

**Vocabulary**: delve, crucial, pivotal, foster, leverage, tapestry, testament, underscore, vibrant, landscape (abstract), interplay, multifaceted, enhance, enduring, garner, showcase, Additionally, seamless, robust, cutting-edge, groundbreaking, nestled, renowned

**Structural tells**:
- Rule of three: forced triads ("streamline, optimize, and enhance")
- Negative parallelism: "It's not just X — it's Y" / "Not X. But Y." → state Y directly
- Superficial -ing phrases: "ensuring reliability", "showcasing features"
- Copula avoidance: "serves as", "stands as", "boasts" — use "is", "has"
- Synonym cycling: four names for the same thing in four sentences
- False ranges: "from X to Y" where X and Y aren't on a meaningful scale
- Formulaic challenges: "Despite X, Y continues to thrive"
- Dramatic fragmentation: "[Noun]. That's it. That's the [thing]." — performative simplicity
- Rhetorical setups: "What if I told you..." / "Think about it:" / "Here's what I mean:"

**Formatting tells**:
- Em dash overuse — replace most with commas or periods
- Mechanical bold on every other phrase
- Emoji-decorated headers
- Bolded-header bullet lists (**Thing:** explanation of thing)
- Title Case In Every Heading Word — use sentence case instead

**Banned phrases** — delete and rewrite on sight. See [references/phrases.md](./references/phrases.md) for the full list.

Core offenders:
- "In today's rapidly evolving landscape"
- "game-changer", "revolutionary", "transformative"
- "Moreover", "Furthermore", "Additionally" (as sentence starters)
- "It's worth noting that", "It is important to note that"
- "At the end of the day"
- "Here's the thing:" / "It turns out" / "Let me be clear" / "The uncomfortable truth is"
- "Full stop." / "Let that sink in." / "Make no mistake"
- "In order to" → "To" | "Due to the fact that" → "Because"
- Generic conclusions: "The future looks bright" → state the actual plan

**Communication artifacts** (remove entirely):
- "Great question!", "I hope this helps!", "Let me know if..."
- "As of my last update", "based on available information"
- Sycophantic openers and vague attributions ("Experts argue", "Industry reports suggest")

## False Agency

AI avoids naming actors by giving inanimate things human verbs. Find the person; put them at the front of the sentence.

| AI slop | Fix |
|---------|-----|
| "the complaint becomes a fix" | Someone fixed it |
| "the data tells us" | Name who read it and what they concluded |
| "the decision emerges" | Someone decided |
| "the culture shifts" | People changed their behavior |
| "the market rewards" | Buyers paid for it |
| "the conversation moves toward" | Someone steered it |

If no specific person fits, use "you" to put the reader in the seat. Person rules: use "you" when addressing the reader directly, "we" for organizational actions, "I" for personal voice. Avoid third-person passive ("it was decided") -- name the actor.

## Voice

- **Have opinions** — react to facts, don't just report them
- **Vary rhythm** — short sentences, then longer ones. Mix it up.
- **Acknowledge complexity** — "impressive but also unsettling" beats "impressive"
- **Use first person when appropriate** — "I keep coming back to..." signals a real person
- **Be specific about feelings** — not "this is concerning" but name what unsettles you
- **Let some mess in** — fragments ("Because that's real."), conjunction starters ("But here's the thing."), parentheticals (thinking mid-sentence) — all signal a human drafting, not generating

## Composition

- One paragraph, one topic. Lead with the topic sentence.
- Keep related words together. Place emphatic words at end of sentence.
- Don't join independent clauses with a comma. Don't break sentences in two.
- Beginning participial phrase must refer to the grammatical subject.
- Match tone to context: casual for blogs, precise for docs, direct for UI text.

## Self-Check

1. Read every sentence aloud. If it sounds like a press release, Wikipedia, or chatbot — rewrite.
2. Ctrl-F the banned-phrases list. Zero matches required.
3. Check for false agency: any inanimate thing performing a human verb? Name the person.
4. Check for em dash overuse, mechanical bold, and synonym cycling.
5. Score 1–10 on each: Directness / Rhythm / Trust / Authenticity / Density. Below 35/50: revise.

## Changelog Voice

- **Sell test**: every bullet should pass "would a user reading this think 'I want to try that'?" Lead with what the user can now *do*, not implementation details. "You can now filter by date range" not "Refactored the query builder to support date predicates"
- **User-facing vs internal**: internal changes (refactors, dependency bumps, CI fixes) belong in a separate "For contributors" subsection, not mixed with user-facing bullets
- **Verb tense**: past tense for what changed ("Added", "Fixed"), not present ("Adds", "Fixes")

See [references/examples.md](./references/examples.md) for before/after transformations.
