# publication surfaces

## Changelog Voice

- **Sell test**: every bullet should pass "would a user reading this think 'I want to try that'?" Lead with what the user can now *do*, not implementation details. "You can now filter by date range" not "Refactored the query builder to support date predicates"
- **User-facing vs internal**: internal changes (refactors, dependency bumps, CI fixes) belong in a separate "For contributors" subsection, not mixed with user-facing bullets
- **Verb tense**: past tense for what changed ("Added", "Fixed"), not present ("Adds", "Fixes")

## PR / MR Descriptions

Match length to change complexity (1 sentence for trivial, full narrative for architecturally significant). Lead with Before / After / Scope rationale; describe net end state, not iteration journey; pick Mermaid for topology, tables for grids. See [references/pr-descriptions.md](./pr-descriptions.md) for the sizing matrix, narrative frame, GitHub hazards (`#NN` auto-link trap), and self-check list.

## README Rules

READMEs are a different surface than blog posts, social posts, or PR descriptions. The general anti-AI-tells rules apply, with these carve-outs:

- **Em dash gate.** `grep -c "—" README.md` must return `0` before commit. Replacements per role: `Term — explanation` → `**Term**: explanation`; `name — qualifier` → `name (qualifier)`; mid-sentence break → two sentences or `;`; `- foo — bar` → `- **foo**: bar`; `Section — note` → `Section: note`.
- **Emoji headers are normal README idiom.** `## 🚀 Features`, `## 📦 Installation` read as open-source convention, not AI styling; the social-post emoji ban does NOT apply here. At most one per header, never inline in prose.
- **Plain-text star link, not a markdown URL.** `If this saves you a debugging cycle, ⭐ star it!` reads as a human ask. `[⭐ Star on GitHub](https://...)` reads as marketing chrome.
- **Hybrid merge on rewrites.** When rewriting an existing README, classify each section: PRESERVE (technical accuracy, version pins, install commands, working code blocks), ADD (missing context), REJECT (AI fluff, marketing voice, padding), FIX (wrong claims, stale versions, broken links). Resist wholesale replacement: the existing technical content is usually correct; the voice is what's wrong.
- **The self-check is per-section, not per-paragraph.** Each H2 section serves one job and is its own audit unit; one polished section next to a fluffy one is worse than uniform mediocrity.

See [references/examples.md](./examples.md) for before/after transformations.
