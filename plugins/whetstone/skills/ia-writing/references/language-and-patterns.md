# language and patterns

## Modes

**Edit (default)**: rewrite the draft to strip AI tells while preserving the writer's voice; produce corrected text. Add a changelog only when the caller asks for one, and keep it outside the returned text. A line such as "Edit-mode pass applied: split two long sentences" inside a commit body, PR description, or reply is the AI tell this mode exists to remove.

**Detect**: when asked whether text reads as AI, or to audit, scan, or flag a draft without rewriting, name each pattern that appears, quote the offending line, and give the fix in a few words. Do not rewrite, do not score, do not claim whether AI wrote it; named patterns are evidence the reader can check, an authorship verdict is a guess. Run detection per Phase 1 of [audit-workflow.md](./audit-workflow.md), stop there, and offer to edit afterward.

**Not this skill**: text whose reader is a model rather than a person: tool descriptions, system prompts, skill and agent instructions, error strings, inter-agent messages. The human-voice rules below (contractions, varied rhythm, fragments, opinions, let-some-mess-in) make that text harder to parse, not easier. Apply [machine-parsed-text.md](./machine-parsed-text.md) instead.

## Core Principles

- **Active voice**: "We shipped the fix" not "The fix was shipped"
- **Name the actor**: Every sentence needs a human subject doing something. Inanimate objects don't fix bugs, shift cultures, or tell us anything; a person does.
- **Specific over vague**: "Cut reporting from 4 hours to 15 minutes" not "Save time"
- **Simple words**: "Use" not "utilize", "help" not "facilitate", "start" not "initiate"
- **Positive form**: Say what it is, not what it isn't: "Ignore" not "Do not pay attention to"
- **Confident**: Cut "almost", "very", "really", "quite", "arguably", and all -ly adverbs
- **Concrete**: Name the thing, state the number, cite the source
- **Omit needless words**: "Because" not "due to the fact that"; "Now" not "at this point in time"; "Can" not "has the ability to"
- **Use contractions**: "don't", "won't", "it's", "they're". Uncontracted forms are a major AI tell
- **Put the reader in the room**: "You" beats "People." Specifics beat abstractions. Avoid narrating from a distance.

## AI Patterns: Kill on Sight

Weight detection toward structure: models reproduce sentence *structures* more reliably than vocabulary, and most AI tone lives in the shape, not the words.

**Vocabulary**: delve, crucial, pivotal, foster, leverage, tapestry, testament, underscore, vibrant, landscape (abstract), shape (abstract, as in "previous shape" / "the shape of the problem"), interplay, multifaceted, enhance, enduring, garner, showcase, Additionally, seamless, robust, cutting-edge, groundbreaking, nestled, renowned

**Structural tells**:
- Rule of three: forced triads ("streamline, optimize, and enhance")
- Negative parallelism: "It's not just X -- it's Y" / "Not X. But Y." → state Y directly
- Superficial -ing phrases: "ensuring reliability", "showcasing features"
- Copula avoidance: "serves as", "stands as", "boasts" → use "is", "has"
- Synonym cycling: four names for the same thing in four sentences
- False ranges: "from X to Y" where X and Y aren't on a meaningful scale
- Formulaic challenges: "Despite X, Y continues to thrive"
- Dramatic fragmentation: "[Noun]. That's it. That's the [thing]." (performative simplicity)
- Fake-profound kicker: a final "deep" line that turns the point into a metaphor, aphorism, or mic-drop. Delete it; don't rewrite into a better line. End on the clearest concrete sentence already present.
- Rhetorical setups: "What if I told you..." / "Think about it:" / "Here's what I mean:"
- Colon reveals: noun phrase, colon, lowercase dramatic reveal ("The best part: it learns"). Rewrite as a plain sentence. Reserve colons for lists, labels, and quotes; sentence case after a colon unless grammar, a proper noun, a title, or code requires it.
- Wh- sentence openers: sentences starting with What/When/Where/Which/Who/Why/How as filler. Restructure to lead with the subject or verb.
- Narrator-from-a-distance: "This happens because...", "People tend to...", "Nobody designed this." Put the reader in the room instead.
- Lazy extremes: every, always, never, everyone, nobody (false authority). Use specifics instead of sweeping claims.
- Meta-commentary: "Hint:", "Plot twist:", "Spoiler:", "In this section, we'll...", "As we'll see...", "Let me walk you through..."
- Mannered prose: an idiom or metaphor standing in for a literal phrase ("earns its keep", "a dial worth turning", "does the heavy lifting"). It displays the writer, not the idea, and drags in connotations the writer did not choose. Use the literal phrase.
- Process narration: steps the writer took that do not change what the reader does next ("First I checked X, then re-ran Y"). Keep the finding or decision; cut the account of how the time was spent.
- Bare tallies: counts, scorecards, and lists of everything checked with no decision attached ("resolved 11 threads"). Say what was decided and why; if nothing non-routine was decided, say nothing. Counts that are themselves the evidence (tests executed and passed, gate pass/fail, coverage-ledger file counts) stay, stated exact.

**Formatting tells**:
- No em dashes in delivered prose; restructure the sentence (split, comma, colon, rewrite). En dash only in numeric ranges
- Mechanical bold on every other phrase
- Emoji-decorated headers (exception: README section headers; see [README rules](./publication-surfaces.md#readme-rules))
- Bolded-header bullet lists (**Thing:** explanation of thing)
- Title Case In Every Heading Word → use sentence case instead

**Banned phrases**: delete and rewrite on sight. See [references/phrases.md](./phrases.md) for the full list.

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

**Chat-UI artifacts** (grep before publishing): text and links copied out of a chat interface carry machine fingerprints that no amount of tone editing removes. Strip the AI-referrer tracking parameter from URLs (`utm_source=chatgpt.com`, `utm_source=claude.ai`, `utm_source=perplexity.ai`, `referrer=grok.com`), leaving the rest of the query string intact. Leaked citation markup is the `[OAICITE]` class in [audit-workflow.md](./audit-workflow.md); extend that list rather than starting a second one. `citeturn0search0`, `contentReference[oaicite:0]{index=0}`, `[attached_file:1]`, and `grok_card` belong there alongside the `[oai_citation:...]` and `【...†source】` forms already listed. These are mechanical, so check them mechanically; unlike a vocabulary tell they are not a judgement call, and shipping one in a README or PR body is a provenance leak, not a style problem.

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

If no specific person fits, use "you" to put the reader in the seat. Person rules: "you" for the reader, "we" for organizational actions, "I" for personal voice. Avoid third-person passive ("it was decided"); name the actor.
