---
name: ia-refine-prompt
class: meta
description: >-
  Transforms vague prompts into precise, structured AI instructions. Use when
  asked to refine, improve, or sharpen a prompt, do prompt engineering,
  write a system prompt, or make AI instructions more effective.
---

# Refining Prompts

## Process

1. **Assess** -- Identify what the prompt is missing:

| Element | Check |
|---------|-------|
| Task | Is the core action explicit and unambiguous? |
| Constraints | Are length, format, tone, and scope defined? |
| Output format | Does it specify the expected structure? |
| Context | Does the model have enough background to act? Check: audience, input format, success criteria, scope boundaries, technical constraints |
| Examples | Would a demonstration clarify the expected output? |
| Edge cases | Are failure modes and boundary conditions addressed? |

2. **Rewrite** -- Transform into specification language: precise, imperative, no filler. Treat the prompt as a spec, not conversation.

3. **Validate** -- Check the rewrite against the assessment table. Every gap identified in step 1 must be addressed.

## Rules

- **Length**: 0.75x–1.5x the original. Conciseness is a feature -- add only what's missing, cut what's vague.
- **A line must change behavior.** "Cut what's vague" and "cut what the model already does" are different filters, and the second removes far more -- every line reads as non-vague once it is imperative. If the model would act that way by default, delete the whole sentence rather than trimming words from it. The recurring offender is encouragement it already follows: "be careful", "be thorough", "think it through", "make sure to".
- **Name the concept, don't explain it.** Use terms the model knows (idempotent, invariant, race condition, TOCTOU, YAGNI) instead of spelling them out. Spell out only terms the project invented, once, in one place.
- **State a rule once.** If the same rule appears in two sections, cut one and point to the other.
- **Never invent** -- only use information present in the original prompt or conversation context. If critical info is missing, ask instead of assuming.
- **Instruction hierarchy** -- order sections by priority: task → constraints → examples → input data → output format. Place the most important instruction first.
- **Progressive complexity** -- start with the simplest prompt that could work. Add few-shot examples, chain-of-thought, or role framing only when the task demands it, not by default.
- **Specific verbs** -- replace vague actions ("analyze", "process", "handle") with measurable ones ("list the top 3", "classify as A/B/C", "return JSON with keys X, Y").
- **One output format** -- specify exactly one format (JSON schema, markdown template, numbered list). Ambiguous format expectations cause inconsistent results.
- **No meta-commentary** -- output only the refined prompt as markdown. No preamble ("Here's an improved version..."), no explanation of changes unless explicitly requested.

## Persistence

After refining, offer to save the result to `.ai/PROMPT.md` -- do not write without user confirmation. If approved, append with a heading and date:

```markdown
## [Prompt Name] -- YYYY-MM-DD

[refined prompt content]
```

## Anti-Patterns

| Problem | Fix |
|---------|-----|
| Vague verbs ("look into", "deal with") | Replace with concrete actions ("list", "compare", "extract") |
| Missing output spec | Add explicit format section with example structure |
| Examples contradict instructions | Align examples to match every stated rule |
| Over-engineered from the start | Strip to simplest working version, then add complexity only where output quality requires it |
| Prompt exceeds context with examples | Limit to 2–3 diverse examples; use one simple, one edge case |

## Constraints

- Stop refining if the original intent is unclear -- clarify first
- Do not refine prompts for harmful or illegal tasks

## Verify

- Rewrite addresses every gap identified in the assessment
- Length ratio within 0.75x-1.5x of original (unless structural change justified)
- No invented constraints or assumptions not in the original
