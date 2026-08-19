---
name: ia-writing
class: discipline
description: >-
  Prose editing, rewriting, and humanizing text for natural tone, or auditing a
  draft for AI tells without rewriting. Use when asked to write, rewrite, edit,
  humanize, proofread, fix tone, remove AI language, or check whether writing
  reads as AI. For copy, docs, blog posts, emails, or PRs.
---

# Human Writing

## Modes

**Edit (default)** -- rewrite the draft to strip AI tells while preserving the writer's voice; produce corrected text plus a changelog.

**Detect** -- when asked whether text reads as AI, or to audit, scan, or flag a draft without rewriting: name each pattern that appears, quote the offending line, and give the fix in a few words. Do not rewrite, do not score, do not claim whether AI wrote it -- named patterns are evidence the reader can check; an authorship verdict is a guess. Run detection per Phase 1 of [audit-workflow.md](./references/audit-workflow.md), stop there, and offer to edit afterward.

**Not this skill** -- text whose reader is a model rather than a person: tool descriptions, system prompts, skill and agent instructions, error strings, inter-agent messages. The human-voice rules below (contractions, varied rhythm, fragments, opinions, let-some-mess-in) make that text harder to parse, not easier. Route it to `ia-refine-prompt`.

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

Weight detection toward structure: models reproduce sentence *structures* more reliably than vocabulary, and most AI tone lives in the shape, not the words.

**Vocabulary**: delve, crucial, pivotal, foster, leverage, tapestry, testament, underscore, vibrant, landscape (abstract), shape (abstract, as in "previous shape" / "the shape of the problem"), interplay, multifaceted, enhance, enduring, garner, showcase, Additionally, seamless, robust, cutting-edge, groundbreaking, nestled, renowned

**Structural tells**:
- Rule of three: forced triads ("streamline, optimize, and enhance")
- Negative parallelism: "It's not just X -- it's Y" / "Not X. But Y." → state Y directly
- Superficial -ing phrases: "ensuring reliability", "showcasing features"
- Copula avoidance: "serves as", "stands as", "boasts" -- use "is", "has"
- Synonym cycling: four names for the same thing in four sentences
- False ranges: "from X to Y" where X and Y aren't on a meaningful scale
- Formulaic challenges: "Despite X, Y continues to thrive"
- Dramatic fragmentation: "[Noun]. That's it. That's the [thing]." -- performative simplicity
- Fake-profound kicker: a final "deep" line that turns the point into a metaphor, aphorism, or mic-drop. Delete it -- don't rewrite into a better line; end on the clearest concrete sentence already present.
- Rhetorical setups: "What if I told you..." / "Think about it:" / "Here's what I mean:"
- Colon reveals: noun phrase, colon, lowercase dramatic reveal ("The best part: it learns"). Rewrite as a plain sentence. Reserve colons for lists, labels, and quotes; sentence case after a colon unless grammar, a proper noun, a title, or code requires it.
- Wh- sentence openers: sentences starting with What/When/Where/Which/Who/Why/How as filler. Restructure to lead with the subject or verb.
- Narrator-from-a-distance: "This happens because...", "People tend to...", "Nobody designed this." Put the reader in the room instead.
- Lazy extremes: every, always, never, everyone, nobody -- false authority. Use specifics instead of sweeping claims.
- Meta-commentary: "Hint:", "Plot twist:", "Spoiler:", "In this section, we'll...", "As we'll see...", "Let me walk you through..."

**Formatting tells**:
- No em dashes in delivered prose -- restructure the sentence (split, comma, colon, rewrite); en dash only in numeric ranges
- Mechanical bold on every other phrase
- Emoji-decorated headers (exception: README section headers; see README Rules below)
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

**Communication artifacts** (remove entirely): sycophantic openers and closers ("Great question!", "I hope this helps!"), knowledge-cutoff hedges ("As of my last update"), vague attributions ("Experts argue").

**Chat-UI artifacts** (grep before publishing): text and links copied out of a chat interface carry machine fingerprints that no amount of tone editing removes. Strip the AI-referrer tracking parameter from URLs -- `utm_source=chatgpt.com`, `utm_source=claude.ai`, `utm_source=perplexity.ai`, `referrer=grok.com` -- leaving the rest of the query string intact. Leaked citation markup is the `[OAICITE]` class in [audit-workflow.md](./references/audit-workflow.md) -- extend that list rather than starting a second one; `citeturn0search0`, `contentReference[oaicite:0]{index=0}`, `[attached_file:1]`, and `grok_card` belong there alongside the `[oai_citation:...]` and `【...†source】` forms already listed. These are mechanical, so check them mechanically; unlike a vocabulary tell they are not a judgement call, and shipping one in a README or PR body is not a style problem but a provenance leak.

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

If no specific person fits, use "you" to put the reader in the seat. Person rules: "you" for the reader, "we" for organizational actions, "I" for personal voice. Avoid third-person passive ("it was decided") -- name the actor.

## Quality Gate

Route by length first. Short-form (commits, PR descriptions, comments, posts): quick audit + Self-Check 1-4, stop there. Long-form (docs, essays, reports): two-phase audit per [audit-workflow.md](./references/audit-workflow.md), then Self-Check 1-5.

**Quick audit** -- flag anything below; a flag is a candidate, not a verdict (adjudicate with Restraint before editing):
- Intensifiers and -ly hedges ("very", "really", "significantly")? Flag them.
- Any passive voice? Find the actor, make them the subject.
- Inanimate thing doing a human verb? Name the person.
- "Not X, it's Y" contrast? State Y directly.
- Three consecutive sentences match length? Break one.
- Vague declarative ("The implications are significant")? Name the specific implication.
- Meta-joiner ("The rest of this section...")? Delete. Let the text move.

**Restraint -- over-editing is a failure mode, equal in weight to under-editing.**
- If a sentence already reads naturally, leave it. Touching prose that was fine introduces new tells and strips voice.
- Match the smell, not the string. A listed word that reads naturally in its actual context stays -- flag the tone, not the token. Blanket-banning a word is mechanical editing, the same defect the skill exists to remove.
- Before the first edit, name the draft's core point and 3-5 concrete voice signals to preserve -- vocabulary, cadence, bluntness, humour, admitted uncertainty, digressions, how polished it is meant to sound. Keep the note internal; it is the reference the two checks below are measured against, not output.

**Long-form output skeleton** (tag vocabulary, severity suffixes, and fix actions live in the audit workflow reference above):

```
## AUDIT
1. "quoted snippet" [TAG] [TAG +H]
— END AUDIT: [n] issues found —

## CORRECTED TEXT
[full corrected text]

## CHANGELOG
- Line/section: brief description of change
```

## Voice

- **Have opinions** -- react to facts, don't just report them
- **Vary rhythm** -- short sentences, then longer ones. Quick audit rule: three consecutive sentences match length? Break one.
- **Acknowledge complexity** -- "impressive but also unsettling" beats "impressive"
- **Use first person when appropriate** -- "I keep coming back to..." signals a real person
- **Be specific about feelings** -- not "this is concerning" but name what unsettles you
- **Let some mess in** -- fragments ("Because that's real."), conjunction starters ("But that changes everything."), parentheticals (thinking mid-sentence) -- all signal a human drafting, not generating

## Composition

- First sentence earns the second. In long-form prose, open on a concrete fact, number, or specific the reader doesn't have yet -- not on context-setting, a definition, or what the piece will cover. Test: delete the opening sentence. If nothing is lost, it was throat-clearing.
- One paragraph, one topic. Lead with the topic sentence.
- Keep related words together. Place emphatic words at end of sentence.
- Don't join independent clauses with a comma. Don't break sentences in two.
- Beginning participial phrase must refer to the grammatical subject.
- Match tone to context: casual for blogs, precise for docs, direct for UI text.

## Self-Check

1. Read every sentence aloud. If it sounds like a press release, Wikipedia, or chatbot -- rewrite.
2. Grep the text against the entries in [phrases.md](./references/phrases.md); zero matches required.
3. Check for false agency: any inanimate thing performing a human verb? Name the person.
4. Check for em dashes, mechanical bold, and synonym cycling.
5. Cut quotables: if a sentence sounds like a pull-quote, aphorism, or mic-drop kicker, delete it -- don't rewrite it into a better line. End on the clearest concrete sentence already in the draft; add a plain takeaway or next action only if the ending needs closure.
6. Proportionality: is the amount cut proportional to the slop actually found? Compression that strips character is over-editing, not thoroughness.
7. Recognizability: against the voice signals captured before editing, would the writer still recognize this as their own? If it now reads like a different, tidier author, restore what carried the voice.

## Changelog Voice

- **Sell test**: every bullet should pass "would a user reading this think 'I want to try that'?" Lead with what the user can now *do*, not implementation details. "You can now filter by date range" not "Refactored the query builder to support date predicates"
- **User-facing vs internal**: internal changes (refactors, dependency bumps, CI fixes) belong in a separate "For contributors" subsection, not mixed with user-facing bullets
- **Verb tense**: past tense for what changed ("Added", "Fixed"), not present ("Adds", "Fixes")

## PR / MR Descriptions

Match length to change complexity (1 sentence for trivial, full narrative for architecturally significant). Lead with Before / After / Scope rationale; describe net end state, not iteration journey; pick Mermaid for topology, tables for grids. See [references/pr-descriptions.md](./references/pr-descriptions.md) for the sizing matrix, narrative frame, GitHub hazards (`#NN` auto-link trap), and self-check list.

## README Rules

READMEs are a different surface than blog posts, social posts, or PR descriptions. The general anti-AI-tells rules apply, with these carve-outs:

- **Em dash gate.** `grep -c "—" README.md` must return `0` before commit. Replacements per role: `Term — explanation` → `**Term**: explanation`; `name — qualifier` → `name (qualifier)`; mid-sentence break → two sentences or `;`; `- foo — bar` → `- **foo**: bar`; `Section — note` → `Section: note`.
- **Emoji headers are normal README idiom.** `## 🚀 Features`, `## 📦 Installation` read as open-source convention, not AI styling; the social-post emoji ban does NOT apply here. At most one per header, never inline in prose.
- **Plain-text star link, not a markdown URL.** `If this saves you a debugging cycle, ⭐ star it!` reads as a human ask. `[⭐ Star on GitHub](https://...)` reads as marketing chrome.
- **Hybrid merge on rewrites.** When rewriting an existing README, classify each section: PRESERVE (technical accuracy, version pins, install commands, working code blocks), ADD (missing context), REJECT (AI fluff, marketing voice, padding), FIX (wrong claims, stale versions, broken links). Resist wholesale replacement: the existing technical content is usually correct; the voice is what's wrong.
- **The self-check is per-section, not per-paragraph.** Each H2 section serves one job and is its own audit unit; one polished section next to a fluffy one is worse than uniform mediocrity.

See [references/examples.md](./references/examples.md) for before/after transformations.
