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
