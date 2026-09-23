---
name: ia-writing
class: discipline
description: >-
  Prose editing, rewriting, and humanizing text for natural tone, or auditing a
  draft for AI tells without rewriting. Use when asked to write, rewrite, edit,
  humanize, proofread, fix tone, remove AI language, or check whether writing
  reads as AI. For copy, docs, blog posts, emails, or PRs.
---

# Human writing

Edit human-facing prose while preserving meaning, factual accuracy, and the writer's voice. User instructions and the intended audience outrank these style preferences. Editing a draft does not authorize posting it.

## Modes

- **Edit** (default): produce corrected text. Add a changelog only when the caller asks for one; place it outside the returned text, never inside a delivered artifact such as a commit body, PR description, or comment.
- **Detect**: when asked to flag AI tells without rewriting, quote each observed pattern and give a brief fix. Do not rewrite, score, or infer authorship. Use Phase 1 of [audit-workflow.md](./references/audit-workflow.md), then stop and offer an edit.
- **Machine-facing text**: tool descriptions, system prompts, skill/agent instructions, error strings, and inter-agent messages need precise specification language. Use `ia-refine-prompt` when appropriate; do not apply fragments, contractions, or invented personal voice mechanically.

## Procedure

1. Identify the draft's core point and 3-5 concrete voice signals to preserve: vocabulary, cadence, bluntness, humor, uncertainty, digressions, and intended polish. Keep this working note out of the delivered text.
2. Match the requested surface and mode. Short commits, PR descriptions, comments, and posts need a quick audit. Long documents, essays, and reports use the two-phase [audit-workflow.md](./references/audit-workflow.md).
3. Lead with a concrete fact or point. Use active voice, specific actors where relevant, simple words, stable terminology, and meaningful numbers. Keep related words together, one topic per paragraph, and tone appropriate to the audience.
4. Flag formulaic structures, vague claims, passive evasions, unnecessary qualifiers, artificial contrasts, synonym cycling, mechanical formatting, and fake-profound endings. A flag is a candidate, not a verdict.
5. Apply restraint: leave natural sentences intact, preserve useful uncertainty, and retain lists/tables that carry real structure. Match the tone problem, not a forbidden token. Do not invent opinions, feelings, facts, or actors to satisfy a stylistic pattern.
6. Read the result aloud. Check that edits remain proportional and that the writer would recognize the voice. Return the full corrected text when editing; add audit or changelog detail only when the caller asked for it, and keep it outside the delivered artifact.

## Conditional references

- For vocabulary, grammatical structure, false agency, formulaic rhetoric, or a draft that feels AI-written, read [language-and-patterns.md](./references/language-and-patterns.md). Use its catalog as contextual diagnostic guidance, subject to restraint.
- For rhythm, composition, over-editing, the quality gate, or preserving a distinctive voice, read [editing-and-voice.md](./references/editing-and-voice.md).
- For long-form auditing or detect mode, read [audit-workflow.md](./references/audit-workflow.md); its tag vocabulary and severity markers govern the audit format.
- When checking stock phrases before publication, read [phrases.md](./references/phrases.md). Resolve matches in context rather than stripping legitimate technical language.
- For a changelog or README, read [publication-surfaces.md](./references/publication-surfaces.md). Preserve accurate install commands, examples, version pins, and other technical content during rewrites.
- For a PR/MR description, read [pr-descriptions.md](./references/pr-descriptions.md). Match length to complexity and explain the net end state rather than the iteration history.
- When a before/after example would clarify an edit, read [examples.md](./references/examples.md).

## Verify

Check factual meaning, voice preservation, grammatical relationships, and useful formatting. Restructure em dashes in delivered prose; README headers may use one emoji each under the surface rules. Delete a manufactured aphorism rather than polishing it.

Before publishing, mechanically check chat citation artifacts and AI-referrer parameters. Remove the identified tracking parameter while retaining the rest of a URL's query string. Follow the citation-artifact catalog in the audit reference; do not mistake a retained capture or UI token for a source.

For detect mode, return evidence of patterns without a speculative authorship verdict. For editing, deliver corrected text, with concise material changes listed only on request and outside the artifact; obtain required posting authority separately.
