# Plan Deepening

Load this reference when asked to "deepen" or "strengthen" an existing plan. The `/ia-deepen-plan` command orchestrates this workflow with parallel research agents per section.

## Workflow

When asked to deepen a plan, don't re-run the full planning workflow. Instead:

1. Read the existing plan file
2. Identify phases or tasks that are vague, under-specified, or missing verification steps
3. For each weak area, run targeted research (read relevant code, check existing patterns, verify assumptions)
4. Expand the weak sections with concrete file paths, code patterns, and verification steps
5. Preserve everything that's already specific enough

Deepening is additive — it fills gaps without restructuring what already works.

## Enhancement format per section

When a section is deepened by research agents, append the findings using this structure (preserve the original section content above it):

```markdown
## [Original Section Title]

[Original content preserved verbatim]

### Research Insights

**Best Practices:**
- [Concrete recommendation with rationale]

**Performance Considerations:**
- [Optimization opportunity or benchmark to target]

**Implementation Details:**
​```[language]
// Concrete code example from research
​```

**Edge Cases:**
- [Edge case and handling strategy]

**References:**
- [Documentation URL]
```

## Enhancement summary block

At the top of the deepened plan, add a summary so reviewers can see what changed without diffing:

```markdown
## Enhancement Summary

**Deepened on:** [Date]
**Sections enhanced:** [Count]
**Research agents used:** [List]

### Key Improvements
1. [Major improvement]

### New Considerations Discovered
- [Important finding]
```

Both blocks are owned by this skill — commands that orchestrate deepening (e.g., `/ia-deepen-plan`) delegate format decisions here rather than restating the templates.
