# editing and voice

## Quality Gate

Route by length first. Short-form (commits, PR descriptions, comments, posts): quick audit + Self-Check 1-4, stop there. Long-form (docs, essays, reports): two-phase audit per [audit-workflow.md](./audit-workflow.md), then Self-Check 1-5.

**Quick audit** -- flag anything below; a flag is a candidate, not a verdict (adjudicate with Restraint before editing):
- Intensifiers and -ly hedges ("very", "really", "significantly")? Flag them.
- Any passive voice? Find the actor, make them the subject.
- Inanimate thing doing a human verb? Name the person.
- "Not X, it's Y" contrast? State Y directly.
- Three consecutive sentences match length? Break one.
- Sentence past 30 words carrying two ideas? Split it.
- Paragraph running six or more sentences on one topic sentence? Break it.
- Vague declarative ("The implications are significant")? Name the specific implication.
- Meta-joiner ("The rest of this section...")? Delete. Let the text move.

**Restraint -- over-editing is a failure mode, equal in weight to under-editing.**
- If a sentence already reads naturally, leave it. Touching prose that was fine introduces new tells and strips voice.
- Match the smell, not the string. A listed word that reads naturally in its actual context stays -- flag the tone, not the token. Blanket-banning a word is mechanical editing, the same defect the skill exists to remove.
- Under-formatting is a defect too. Three or more parallel items packed into one sentence want a list; a grid of attributes wants a table. Strip formatting that is mechanical, not formatting that carries structure.
- Before the first edit, name the draft's core point and 3-5 concrete voice signals to preserve -- vocabulary, cadence, bluntness, humour, admitted uncertainty, digressions, how polished it is meant to sound. Keep the note internal; it is the reference the two checks below are measured against, not output.

**Long-form output skeleton** (tag vocabulary, severity suffixes, and fix actions live in [audit-workflow.md](./audit-workflow.md)):

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
2. Grep the text against the entries in [phrases.md](./phrases.md); zero unexamined matches required. Apply Restraint to legitimate contextual uses; remove formulaic uses.
3. Check for false agency: any inanimate thing performing a human verb? Name the person.
4. Check for em dashes, mechanical bold, and synonym cycling.
5. Cut quotables: if a sentence sounds like a pull-quote, aphorism, or mic-drop kicker, delete it -- don't rewrite it into a better line. End on the clearest concrete sentence already in the draft; add a plain takeaway or next action only if the ending needs closure.
6. Proportionality: is the amount cut proportional to the slop actually found? Compression that strips character is over-editing, not thoroughness.
7. Recognizability: against the voice signals captured before editing, would the writer still recognize this as their own? If it now reads like a different, tidier author, restore what carried the voice.
