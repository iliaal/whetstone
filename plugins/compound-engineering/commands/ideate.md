---
name: ideate
description: Generate ranked improvement ideas by scanning the codebase, divergent ideation, adversarial critique, and impact ranking
---

# Ideate

Generate and rank high-impact improvement ideas for the current project.

## Process

### 1. Ground in reality

Scan the codebase before ideating. Read project structure, recent commits (`git log --oneline -20`), open issues, CLAUDE.md, README, and any `docs/` content. Note: tech debt signals, architectural patterns, test coverage gaps, performance bottlenecks, DX friction points.

### 2. Diverge

Generate 10-15 improvement ideas across categories:

- **Architecture** -- structural improvements, decoupling, simplification
- **Developer experience** -- tooling, automation, onboarding friction
- **Performance** -- queries, caching, bundle size, startup time
- **Testing** -- coverage gaps, flaky tests, missing integration tests
- **Security** -- hardening, audit gaps, dependency vulnerabilities
- **Features** -- user-facing improvements grounded in existing patterns

Each idea: one sentence describing what changes, one sentence describing the expected impact.

**Ideation lenses.** After generating category-based ideas, force divergent thinking by running each lens against the codebase:

1. **Inversion** -- what if the exact opposite of the current approach were taken?
2. **Constraint removal** -- what if the biggest constraint (time, budget, compatibility, backwards-compat) didn't exist?
3. **Audience shift** -- what if the primary user were a different persona (novice vs expert, internal vs external, human vs machine)?
4. **Time shift** -- what would the solution look like with 10x more time? With 1/10th the time?
5. **Scale shift** -- what if traffic/data/users were 100x current? What simplifications would break?
6. **Simplification** -- what's the version with zero external dependencies? What's the version a junior engineer could maintain?
7. **Combination** -- what if the two best approaches were merged? What hybrid gets the strengths of both?

Each lens generates at least one candidate idea. Not all lenses will produce viable ideas for every problem -- that's fine. The point is forcing exploration beyond the obvious first idea.

### 3. Adversarial critique

For each idea, challenge it:

- Is the impact real or imagined? What evidence supports it?
- What's the cost (time, complexity, risk of regression)?
- Does it solve a problem that actually exists, or a hypothetical one?
- Would a senior engineer on this project prioritize this?

Kill ideas that fail the critique. Be ruthless -- surviving ideas should be genuinely worth doing.

### 4. Rank survivors

Score remaining ideas by impact/effort ratio. Present the top 5-8:

```markdown
| # | Idea | Impact | Effort | Why |
|---|------|--------|--------|-----|
| 1 | [What to do] | HIGH | LOW | [Why this matters now] |
```

### 5. Output

Save to `docs/ideation/YYYY-MM-DD-ideation.md` (create directory if needed). Present the ranked list to the user and ask which ideas to pursue.

## Constraints

- Ideas must be grounded in the actual codebase, not generic advice
- No ideas that require information you don't have (user metrics, business priorities)
- No ideas that duplicate ongoing work (check recent branches, PRs)
- If the codebase is small or well-maintained, it's fine to return fewer than 5 ideas
