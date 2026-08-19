# Two-Phase Audit Workflow

Fix-as-you-go editing causes blind spots: correcting one tell shifts attention away from detecting others. Separate detection from correction to catch more issues.

## Phase 1: Audit (detection only)

Read the full text start to finish without changing anything. Quote the shortest offending snippet (≤12 words) and append every applicable tag. Stack tags if multiple tells land in one sentence. One numbered line per offense. End with `— END AUDIT: [n] issues found —`. If zero, write `— AUDIT COMPLETE: 0 issues —` and skip Phase 2.

### Prose tells

| Tag | What it catches |
|-----|-----------------|
| `[FALSE-AGENCY]` | Inanimate subject with a human verb ("the data tells us") |
| `[BINARY-CONTRAST]` | "Not X, it's Y" / "Not X. But Y." / "The answer isn't X. It's Y." |
| `[COLON-REVEAL]` | Noun phrase + colon + lowercase dramatic reveal ("The best part: it learns") |
| `[KICKER]` | Fake-profound final line: metaphor, aphorism, or mic-drop that restates the point |
| `[STACCATO]` | Punchy fragment sequences simulating manufactured rhythm ("This matters. A lot. Here's why.") |
| `[ELEGANT-VAR]` | Synonym cycling: four names for the same entity across four sentences |
| `[NOT-ONLY-BUT]` | False-pivot contrasts: "Not only X, but also Y" and variants |
| `[RULE-OF-3]` | Forced triads ("streamline, optimize, and enhance") |
| `[INFLATED]` / `[PROMO]` | Puffery and promotional gloss without a verifiable claim |
| `[SUPERFICIAL-ING]` | Trailing -ing phrases that add no information ("ensuring reliability") |
| `[AI-LEX]` | Vocabulary tells (delve, crucial, pivotal, leverage, tapestry, robust...) |
| `[JARGON]` | Business buzzword with a simpler substitute (see phrases.md) |
| `[VAGUE-ATTR]` / `[WEASEL]` | "Experts argue", "studies show" without specific source |
| `[META-COMMENTARY]` | Structural self-reference ("In this section, we'll...", "Let me walk you through...", "As we'll see...") |
| `[METADISCOURSE]` | Interpretive labeling — stepping outside the scene or argument to name its meaning ("that's the lesson", "that part mattered", "this is the point") when the concrete details already carry it. Distinct from `[META-COMMENTARY]` (announces structure) and `[VAGUE-DECLARATIVE]` (announces importance). Keep a direct thesis that adds new information. |
| `[EM-DASH]` | Any em dash, or en dash outside a numeric range |
| `[INLINE-BOLD]` / `[INLINE-LIST]` / `[TITLE-CASE]` | Mechanical formatting tells |
| `[VAGUE-DECLARATIVE]` | "The implications are significant" without naming the implication |
| `[PASSIVE]` / `[ADVERB]` / `[BANNED-PHRASE]` | Standard corrections |
| `[CURLY-QUOTES]` | Curly single or double quotes (`’ ‘ “ ”`) in running prose. AI autocorrect artifact — replace with straight ASCII quotes. |
| `[EMOJI]` | Emoji in running text or headings. Functional UI emoji in product copy is fine; editorial/promotional emoji is an AI tell. |
| `[FALSE-RANGE]` | "From X to Y" where X and Y aren't on a coherent scale ("from code review to cultural shift"). Restructure to state both items without implying a continuum. |

**Severity suffixes** when tagging: `+H` for high severity (strong tell or compound patterns), `+S` for structural (affects document structure, not just wording).

### Citation tells (documentation and research contexts)

| Tag | Trigger |
|-----|---------|
| `[OAICITE]` | Malformed AI citation artifacts -- `[oai_citation:...]`, `【...†source】`, `citeturn0search0`, `contentReference[oaicite:0]{index=0}`, `[attached_file:1]`, `grok_card`, or similar markup leaked from a language model's internal retrieval or copied out of a chat UI |
| `[LINK-ROT]` | Dead URLs, placeholder links (`example.com`, `#`), or links that return 404 |
| `[ISBN-DOI-FAIL]` | Invalid ISBN/DOI identifiers -- wrong check digit, truncated, or fabricated |
| `[REF-BUG]` | Reference formatting errors: mismatched footnote numbers, dangling `[1]` with no matching entry, duplicate reference IDs, inconsistent citation style within the same document |

### Audit output example

```
1. [FALSE-AGENCY] para 3: "the codebase resists change" -- name who finds it hard to change
2. [BINARY-CONTRAST] para 5: "Not speed. Clarity." -- state "Clarity matters" directly
3. [OAICITE] para 8: "[oai_citation:1]" -- remove artifact, add real citation or delete claim
4. [REF-BUG] footnotes: [3] referenced in text but missing from reference list
— END AUDIT: 4 issues found —
```

## Phase 2: Rewrite (correction only)

Correct tagged items in a single pass using the fix table below. Preserve everything not flagged; no scope creep. For each finding: apply the fix, re-read the surrounding paragraph to verify no new tells were introduced, mark it resolved. After completing all fixes, do one final read-through of the full text to catch tells introduced during rewriting.

| Tags | Fix action |
|------|------------|
| `[INFLATED]` `[PROMO]` `[VAGUE-DECLARATIVE]` | Delete puffery or replace with a specific factual claim. If no fact exists, cut entirely. |
| `[SUPERFICIAL-ING]` | Remove the -ing phrase or convert to a separate sentence with substance. |
| `[AI-LEX]` `[JARGON]` | Replace with a plainer synonym or restructure to eliminate the word. |
| `[NOT-ONLY-BUT]` `[RULE-OF-3]` `[BINARY-CONTRAST]` | Break the pattern. State Y directly. |
| `[COLON-REVEAL]` | Rewrite as a plain declarative sentence; reserve colons for lists, labels, quotes. |
| `[KICKER]` | Delete the line -- don't rewrite it. End on the clearest concrete sentence already present. |
| `[STACCATO]` | Reconstruct into a single flowing sentence that matches the source material's natural rhythm. |
| `[ELEGANT-VAR]` | Pick one term and use it consistently (or use pronouns). |
| `[VAGUE-ATTR]` `[WEASEL]` | Name the source, add a quantifier, or delete the claim. |
| `[EM-DASH]` | Remove entirely. Restructure the sentence: split, comma, colon, or rewrite. Never preserve the dash. |
| `[FALSE-AGENCY]` | Name the human actor; put them at the front of the sentence. |
| `[META-COMMENTARY]` | Delete. Let the text move without announcing itself. |
| `[METADISCOURSE]` | Delete the frame; let the scene, quote, or factual claim it pointed at stand on its own. If no concrete claim remains, cut the sentence. |
| `[INLINE-BOLD]` `[INLINE-LIST]` `[TITLE-CASE]` | Strip excess formatting; sentence case for headings. |
| `[OAICITE]` `[LINK-ROT]` `[ISBN-DOI-FAIL]` `[REF-BUG]` | Remove the artifact or fix the reference; add a real citation or delete the claim it supported. |

## Output format

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
