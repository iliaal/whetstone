# Two-Phase Audit Workflow

Fix-as-you-go editing causes blind spots: correcting one tell shifts attention away from detecting others. Separate detection from correction to catch more issues.

## Phase 1: Audit (detection only)

Read the full text start to finish. Tag every tell inline without fixing anything. Use these category tags:

### Prose tells

| Tag | Trigger |
|-----|---------|
| `[FALSE-AGENCY]` | Inanimate thing performing a human verb |
| `[BINARY-CONTRAST]` | "Not X. But Y." / "Not because X. Because Y." / "The answer isn't X. It's Y." |
| `[META-COMMENTARY]` | "The rest of this essay explains..." / "Let me walk you through..." / "In this section, we'll..." / "As we'll see..." / "I want to explore..." |
| `[JARGON]` | Business buzzword with a simpler substitute (see phrases.md) |
| `[PASSIVE]` | Passive voice hiding the actor |
| `[ADVERB]` | -ly word, softener, intensifier, or hedge |
| `[BANNED-PHRASE]` | Any phrase from the kill-on-sight list |
| `[SYNONYM-CYCLE]` | Same concept renamed across consecutive sentences |
| `[VAGUE-DECLARATIVE]` | Announces importance without naming the specific thing |

### Citation tells (documentation and research contexts)

| Tag | Trigger |
|-----|---------|
| `[OAICITE]` | Malformed AI citation artifacts -- `[oai_citation:...]`, `【...†source】`, or similar markup leaked from a language model's internal retrieval |
| `[LINK-ROT]` | Dead URLs, placeholder links (`example.com`, `#`), or links that return 404 |
| `[ISBN-DOI-FAIL]` | Invalid ISBN/DOI identifiers -- wrong check digit, truncated, or fabricated |
| `[REF-BUG]` | Reference formatting errors: mismatched footnote numbers, dangling `[1]` with no matching entry, duplicate reference IDs, inconsistent citation style within the same document |

### Audit output format

Produce a numbered list of findings before making any edits:

```
1. [FALSE-AGENCY] para 3: "the codebase resists change" -- name who finds it hard to change
2. [BINARY-CONTRAST] para 5: "Not speed. Clarity." -- state "Clarity matters" directly
3. [OAICITE] para 8: "[oai_citation:1]" -- remove artifact, add real citation or delete claim
4. [REF-BUG] footnotes: [3] referenced in text but missing from reference list
```

## Phase 2: Rewrite (correction only)

Work through the tagged findings in order. For each:

1. Apply the fix.
2. Re-read the surrounding paragraph to verify no new tells were introduced.
3. Mark the finding as resolved.

After completing all fixes, do one final read-through of the full text to catch any tells introduced during rewriting.

## When to use each mode

- **Short-form** (commits, PR descriptions, comments, changelogs): single-pass Quick Audit from the main skill is sufficient.
- **Long-form** (blog posts, documentation, essays, reports): use the full two-phase workflow.
- **Research content** (papers, technical docs with citations): use both prose and citation tell categories.
