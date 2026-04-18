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
- **Name the actor**: Every sentence needs a human subject doing something. Inanimate objects don't fix bugs, shift cultures, or tell us anything -- a person does.
- **Specific over vague**: "Cut reporting from 4 hours to 15 minutes" not "Save time"
- **Simple words**: "Use" not "utilize", "help" not "facilitate", "start" not "initiate"
- **Positive form**: Say what it is, not what it isn't -- "Ignore" not "Do not pay attention to"
- **Confident**: Cut "almost", "very", "really", "quite", "arguably", and all -ly adverbs
- **Concrete**: Name the thing, state the number, cite the source
- **Omit needless words**: "Because" not "due to the fact that"; "Now" not "at this point in time"; "Can" not "has the ability to"
- **Use contractions**: "don't", "won't", "it's", "they're" -- uncontracted forms are a major AI tell
- **Put the reader in the room**: "You" beats "People." Specifics beat abstractions. Avoid narrating from a distance.

## AI Patterns -- Kill on Sight

**Vocabulary**: delve, crucial, pivotal, foster, leverage, tapestry, testament, underscore, vibrant, landscape (abstract), interplay, multifaceted, enhance, enduring, garner, showcase, Additionally, seamless, robust, cutting-edge, groundbreaking, nestled, renowned

**Structural tells**:
- Rule of three: forced triads ("streamline, optimize, and enhance")
- Negative parallelism: "It's not just X -- it's Y" / "Not X. But Y." → state Y directly
- Superficial -ing phrases: "ensuring reliability", "showcasing features"
- Copula avoidance: "serves as", "stands as", "boasts" -- use "is", "has"
- Synonym cycling: four names for the same thing in four sentences
- False ranges: "from X to Y" where X and Y aren't on a meaningful scale
- Formulaic challenges: "Despite X, Y continues to thrive"
- Dramatic fragmentation: "[Noun]. That's it. That's the [thing]." -- performative simplicity
- Rhetorical setups: "What if I told you..." / "Think about it:" / "Here's what I mean:"
- Wh- sentence openers: sentences starting with What/When/Where/Which/Who/Why/How as filler. Restructure to lead with the subject or verb.
- Narrator-from-a-distance: "This happens because...", "People tend to...", "Nobody designed this." Put the reader in the room instead.
- Lazy extremes: every, always, never, everyone, nobody -- false authority. Use specifics instead of sweeping claims.
- Meta-commentary: "Hint:", "Plot twist:", "Spoiler:", "In this section, we'll...", "As we'll see...", "Let me walk you through..."

**Formatting tells**:
- Em dash overuse -- replace most with commas or periods
- Mechanical bold on every other phrase
- Emoji-decorated headers
- Bolded-header bullet lists (**Thing:** explanation of thing)
- Title Case In Every Heading Word -- use sentence case instead

**Banned phrases** -- delete and rewrite on sight. See [references/phrases.md](./references/phrases.md) for the full list.

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
| "a bet lives or dies" | Someone kills or ships it |

If no specific person fits, use "you" to put the reader in the seat. Person rules: use "you" when addressing the reader directly, "we" for organizational actions, "I" for personal voice. Avoid third-person passive ("it was decided") -- name the actor.

## Quality Gate

Before delivering prose, run two checks:

**Quick audit** (binary, kill anything that triggers):
- Any adverbs? Kill them.
- Any passive voice? Find the actor, make them the subject.
- Inanimate thing doing a human verb? Name the person.
- "Not X, it's Y" contrast? State Y directly.
- Three consecutive sentences match length? Break one.
- Em-dash anywhere? Replace with comma or period.
- Vague declarative ("The implications are significant")? Name the specific implication.
- Meta-joiner ("The rest of this section...")? Delete. Let the text move.

**Five-dimension scoring** (rate 1-10 each):

| Dimension | Question |
|-----------|----------|
| Directness | Statements or announcements? |
| Rhythm | Varied or metronomic? |
| Trust | Respects reader intelligence? |
| Authenticity | Sounds human? |
| Density | Anything cuttable? |

Below 35/50: revise before delivering.

**Long-form audit workflow** -- for documents, essays, and research content, run a two-phase pass to avoid fix-as-you-go bias (fixing one tell while missing three others). This section reuses the vocabulary and structural tells from "AI Patterns -- Kill on Sight" above but adds named tags for tracking and a structured fix table. Short-form edits can use the Kill-on-Sight list directly; long-form audits should use the tag-based workflow below.

*Phase 1 -- Audit*: Read the full text without changing anything. Quote the shortest offending snippet (≤12 words) and append every applicable tag. Stack tags if multiple tells land in one sentence. One numbered line per offense. End with `— END AUDIT: [n] issues found —`. If zero, write `— AUDIT COMPLETE: 0 issues —` and skip Phase 2.

Tag vocabulary (extend the earlier prose rules with these named IDs):

| Tag | What it catches |
|-----|-----------------|
| `[FALSE-AGENCY]` | Inanimate subject with a human verb ("the data tells us") |
| `[BINARY-CONTRAST]` | "Not X, it's Y" / "It's not about X. It's about Y." constructions |
| `[STACCATO]` | Punchy fragment sequences simulating manufactured rhythm ("This matters. A lot. Here's why.") |
| `[ELEGANT-VAR]` | Synonym cycling: four names for the same entity across four sentences |
| `[NOT-ONLY-BUT]` | False-pivot contrasts: "Not only X, but also Y" and variants |
| `[RULE-OF-3]` | Forced triads ("streamline, optimize, and enhance") |
| `[INFLATED]` / `[PROMO]` | Puffery and promotional gloss without a verifiable claim |
| `[SUPERFICIAL-ING]` | Trailing -ing phrases that add no information ("ensuring reliability") |
| `[AI-LEX]` | Vocabulary tells (delve, crucial, pivotal, leverage, tapestry, robust...) |
| `[VAGUE-ATTR]` / `[WEASEL]` | "Experts argue", "studies show" without specific source |
| `[META-COMMENTARY]` | Structural self-reference ("In this section, we'll...", "Let me walk you through...") |
| `[EM-DASH]` | Any em or en dash -- restructure, don't preserve |
| `[INLINE-BOLD]` / `[INLINE-LIST]` / `[TITLE-CASE]` | Mechanical formatting tells |
| `[VAGUE-DECLARATIVE]` | "The implications are significant" without naming the implication |
| `[PASSIVE]` / `[ADVERB]` / `[BANNED-PHRASE]` | Standard corrections |

**Severity suffixes** when tagging: `+H` for high severity (strong tell or compound patterns), `+S` for structural (affects document structure, not just wording).

*Phase 2 -- Rewrite*: Correct tagged items in a single pass using the fix table below. Preserve everything not flagged; no scope creep. Verify no new tells were introduced during rewriting.

| Tags | Fix action |
|------|------------|
| `[INFLATED]` `[PROMO]` `[VAGUE-DECLARATIVE]` | Delete puffery or replace with a specific factual claim. If no fact exists, cut entirely. |
| `[SUPERFICIAL-ING]` | Remove the -ing phrase or convert to a separate sentence with substance. |
| `[AI-LEX]` | Replace with a plainer synonym or restructure to eliminate the word. |
| `[NOT-ONLY-BUT]` `[RULE-OF-3]` `[BINARY-CONTRAST]` | Break the pattern. State Y directly. |
| `[STACCATO]` | Reconstruct into a single flowing sentence that matches the source material's natural rhythm. |
| `[ELEGANT-VAR]` | Pick one term and use it consistently (or use pronouns). |
| `[VAGUE-ATTR]` `[WEASEL]` | Name the source, add a quantifier, or delete the claim. |
| `[EM-DASH]` | Remove entirely. Restructure the sentence: split, comma, colon, or rewrite. Never preserve the dash. |
| `[FALSE-AGENCY]` | Name the human actor; put them at the front of the sentence. |
| `[META-COMMENTARY]` | Delete. Let the text move without announcing itself. |
| `[INLINE-BOLD]` `[INLINE-LIST]` `[TITLE-CASE]` | Strip excess formatting; sentence case for headings. |

For documents with references or citations, also tag: `[OAICITE]` (malformed AI citation artifacts), `[LINK-ROT]` (dead or placeholder URLs), `[ISBN-DOI-FAIL]` (invalid identifiers), `[REF-BUG]` (misformatted references, wrong numbering, dangling footnotes). See [references/audit-workflow.md](./references/audit-workflow.md) for the full procedure.

**Output format:**

```
## AUDIT
1. "quoted snippet" [TAG] [TAG +H]
2. "quoted snippet" [TAG]
...
— END AUDIT: [n] issues found —

## CORRECTED TEXT
[full corrected text]

## CHANGELOG
- Line/section: brief description of change
- Line/section: brief description of change
```

## Voice

- **Have opinions** -- react to facts, don't just report them
- **Vary rhythm** -- short sentences, then longer ones. Mix it up.
- **Acknowledge complexity** -- "impressive but also unsettling" beats "impressive"
- **Use first person when appropriate** -- "I keep coming back to..." signals a real person
- **Be specific about feelings** -- not "this is concerning" but name what unsettles you
- **Let some mess in** -- fragments ("Because that's real."), conjunction starters ("But that changes everything."), parentheticals (thinking mid-sentence) -- all signal a human drafting, not generating

## Composition

- One paragraph, one topic. Lead with the topic sentence.
- Keep related words together. Place emphatic words at end of sentence.
- Don't join independent clauses with a comma. Don't break sentences in two.
- Beginning participial phrase must refer to the grammatical subject.
- Match tone to context: casual for blogs, precise for docs, direct for UI text.

## Self-Check

**Short-form** (commits, PR descriptions, comments): checks 1-4 only. **Long-form** (blog posts, docs, essays): run the full Quality Gate above, then checks 1-5.

1. Read every sentence aloud. If it sounds like a press release, Wikipedia, or chatbot -- rewrite.
2. Ctrl-F the banned-phrases list. Zero matches required.
3. Check for false agency: any inanimate thing performing a human verb? Name the person.
4. Check for em dash overuse, mechanical bold, and synonym cycling.
5. Cut quotables: if a sentence sounds like a pull-quote or aphorism, rewrite it.

## Changelog Voice

- **Sell test**: every bullet should pass "would a user reading this think 'I want to try that'?" Lead with what the user can now *do*, not implementation details. "You can now filter by date range" not "Refactored the query builder to support date predicates"
- **User-facing vs internal**: internal changes (refactors, dependency bumps, CI fixes) belong in a separate "For contributors" subsection, not mixed with user-facing bullets
- **Verb tense**: past tense for what changed ("Added", "Fixed"), not present ("Adds", "Fixes")

## PR / MR Descriptions

For pull-request and merge-request descriptions, match length to change complexity (1 sentence for trivial, full narrative for architecturally significant). Lead with Before / After / Scope rationale; describe net end state, not iteration journey; pick Mermaid for topology, tables for grids. See [references/pr-descriptions.md](./references/pr-descriptions.md) for the sizing matrix, narrative frame, GitHub-specific hazards (`#NN` auto-link trap), and the self-check list.

See [references/examples.md](./references/examples.md) for before/after transformations.
