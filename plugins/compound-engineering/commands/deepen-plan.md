---
name: deepen-plan
description: Enhance a plan with parallel research agents for each section to add depth, best practices, and implementation details
argument-hint: "[path to plan file]"
---

# Deepen Plan - Power Enhancement Mode

## Plan File

<plan_path> #$ARGUMENTS </plan_path>

**If the plan path above is empty:**
1. Check for recent plans: `ls -la docs/plans/`
2. Ask the user: "Which plan would you like to deepen? Please provide the path (e.g., `docs/plans/2026-01-15-feat-my-feature-plan.md`)."

Do not proceed until you have a valid plan file path.

## Main Tasks

### 1. Parse and Analyze Plan Structure

<thinking>
First, read and parse the plan to identify each major section that can be enhanced with research.
</thinking>

**Read the plan file and extract:**
- [ ] Overview/Problem Statement
- [ ] Proposed Solution sections
- [ ] Technical Approach/Architecture
- [ ] Implementation phases/steps
- [ ] Code examples and file references
- [ ] Acceptance criteria
- [ ] Any UI/UX components mentioned
- [ ] Technologies/frameworks mentioned (Rails, React, Python, TypeScript, etc.)
- [ ] Domain areas (data models, APIs, UI, security, performance, etc.)

**Create a section manifest:**
```
Section 1: [Title] - [Brief description of what to research]
Section 2: [Title] - [Brief description of what to research]
...
```

### 2. Discover All Available Skills and Agents

Discover everything once upfront. Match skills and agents to plan sections, then spawn sub-agents in later steps.

```bash
# Skills: project-local, user-global, all plugins
ls .claude/skills/ 2>/dev/null
ls ~/.claude/skills/ 2>/dev/null
find ~/.claude/plugins/cache -type d -name "skills" 2>/dev/null

# Agents: project-local, user-global, all plugins (skip workflow/ orchestrators)
find .claude/agents -name "*.md" 2>/dev/null
find ~/.claude/agents -name "*.md" 2>/dev/null
find ~/.claude/plugins/cache -path "*/agents/*.md" -not -path "*/workflow/*" 2>/dev/null
```

Read each discovered SKILL.md description and agent frontmatter. Build a manifest:

```
Skills:  [name] -> [description] -> [matching plan sections]
Agents:  [name] -> [description] -> [matching plan sections]
```

### 3. Apply Matched Skills

For each skill that matches plan content, spawn a sub-agent to apply it:

```
Task general-purpose: "Read [skill-path]/SKILL.md and follow its instructions.
Apply the skill to this plan content: [relevant section or full plan].
Return the skill's full output."
```

Spawn all skill sub-agents in parallel, one per matched skill. Cap at 10 skill agents -- if more than 10 match, select the 10 most directly relevant to the plan's core domain.

### 4. Discover and Apply Learnings/Solutions

<thinking>
Check for documented learnings from /workflows:compound. These are solved problems stored as markdown files. Spawn a sub-agent for each learning to check if it's relevant.
</thinking>

**LEARNINGS LOCATION - Check these exact folders:**

```
docs/solutions/           <-- PRIMARY: Project-level learnings (created by /workflows:compound)
├── performance-issues/
│   └── *.md
├── debugging-patterns/
│   └── *.md
├── configuration-fixes/
│   └── *.md
├── integration-issues/
│   └── *.md
├── deployment-issues/
│   └── *.md
└── [other-categories]/
    └── *.md
```

**Step 1: Find ALL learning markdown files**

Run these commands to get every learning file:

```bash
# PRIMARY LOCATION - Project learnings
find docs/solutions -name "*.md" -type f 2>/dev/null

# If docs/solutions doesn't exist, check alternate locations:
find .claude/docs -name "*.md" -type f 2>/dev/null
find ~/.claude/docs -name "*.md" -type f 2>/dev/null
```

**Step 2: Read frontmatter of each learning to filter**

Each learning file has YAML frontmatter with metadata. Read the first ~20 lines of each file to get:

```yaml
---
title: "N+1 Query Fix for Briefs"
category: performance-issues
tags: [activerecord, n-plus-one, includes, eager-loading]
module: Briefs
symptom: "Slow page load, multiple queries in logs"
root_cause: "Missing includes on association"
---
```

**For each .md file, quickly scan its frontmatter:**

```bash
# Read first 20 lines of each learning (frontmatter + summary)
head -20 docs/solutions/**/*.md
```

**Step 3: Filter - only spawn sub-agents for LIKELY relevant learnings**

Compare each learning's frontmatter against the plan:
- `tags:` - Do any tags match technologies/patterns in the plan?
- `category:` - Is this category relevant? (e.g., skip deployment-issues if plan is UI-only)
- `module:` - Does the plan touch this module?
- `symptom:` / `root_cause:` - Could this problem occur with the plan?

**SKIP learnings that are clearly not applicable:**
- Plan is frontend-only → skip `database-migrations/` learnings
- Plan is Python → skip `rails-specific/` learnings
- Plan has no auth → skip `authentication-issues/` learnings

**SPAWN sub-agents for learnings that MIGHT apply:**
- Any tag overlap with plan technologies
- Same category as plan domain
- Similar patterns or concerns

**Step 4: Spawn sub-agents for filtered learnings**

For each learning that passes the filter:

```
Task general-purpose: "
LEARNING FILE: [full path to .md file]

1. Read this learning file completely
2. This learning documents a previously solved problem

Check if this learning applies to this plan:

---
[full plan content]
---

If relevant:
- Explain specifically how it applies
- Quote the key insight or solution
- Suggest where/how to incorporate it

If NOT relevant after deeper analysis:
- Say 'Not applicable: [reason]'
"
```

**Example filtering:**
```
# Found 15 learning files, plan is about "Rails API caching"

# SPAWN (likely relevant):
docs/solutions/performance-issues/n-plus-one-queries.md      # tags: [activerecord] ✓
docs/solutions/performance-issues/redis-cache-stampede.md    # tags: [caching, redis] ✓
docs/solutions/configuration-fixes/redis-connection-pool.md  # tags: [redis] ✓

# SKIP (clearly not applicable):
docs/solutions/deployment-issues/heroku-memory-quota.md      # not about caching
docs/solutions/frontend-issues/stimulus-race-condition.md    # plan is API, not frontend
docs/solutions/authentication-issues/jwt-expiry.md           # plan has no auth
```

**Spawn sub-agents in PARALLEL for all filtered learnings.**

**These learnings are institutional knowledge - applying them prevents repeating past mistakes.**

### 5. Launch Per-Section Research Agents

<thinking>
For each major section in the plan, spawn dedicated sub-agents to research improvements. Use the Explore agent type for open-ended research.
</thinking>

**For each identified section, launch parallel research:**

```
Task Explore: "Research best practices, patterns, and real-world examples for: [section topic].
Find:
- Industry standards and conventions
- Performance considerations
- Common pitfalls and how to avoid them
- Documentation and tutorials
Return concrete, actionable recommendations."
```

**Also use Docfork MCP for framework documentation:**

For any technologies/frameworks mentioned in the plan, query Docfork:
```
mcp__plugin_compound-engineering_docfork__search_docs: Search documentation for [framework]
mcp__plugin_compound-engineering_docfork__fetch_doc: Fetch full content from a search result URL
```

**Use WebSearch for current best practices:**

Search for recent (2024-2026) articles, blog posts, and documentation on topics in the plan.

### 6. Run Review and Research Agents

Using the agent manifest from Step 2, launch review and research agents against the plan. Skip `workflow/` agents (orchestrators, not reviewers).

For each matched agent:
```
Task [agent-name]: "Review this plan using your expertise. Apply all your checks and patterns. Plan content: [full plan content]"
```

Launch all agents in a single message with multiple Task tool calls. Cap at 10 review agents -- if more match, select those most relevant to the plan's domain. Research agents (`best-practices-researcher`, `repo-research-analyst`, `git-history-analyzer`) run in addition to the review cap.

### 7. Wait for ALL Agents and Synthesize Everything

<thinking>
Wait for ALL parallel agents to complete - skills, research agents, review agents, everything. Then synthesize all findings into a comprehensive enhancement.
</thinking>

**Collect outputs from ALL sources:**

1. **Skill-based sub-agents** - Each skill's full output (code examples, patterns, recommendations)
2. **Learnings/Solutions sub-agents** - Relevant documented learnings from /workflows:compound
3. **Research agents** - Best practices, documentation, real-world examples
4. **Review agents** - All feedback from every reviewer (architecture, security, performance, simplicity, etc.)
5. **Docfork queries** - Framework documentation and patterns
6. **Web searches** - Current best practices and articles

**For each agent's findings, extract:**
- [ ] Concrete recommendations (actionable items)
- [ ] Code patterns and examples (copy-paste ready)
- [ ] Anti-patterns to avoid (warnings)
- [ ] Performance considerations (metrics, benchmarks)
- [ ] Security considerations (vulnerabilities, mitigations)
- [ ] Edge cases discovered (handling strategies)
- [ ] Documentation links (references)
- [ ] Skill-specific patterns (from matched skills)
- [ ] Relevant learnings (past solutions that apply - prevent repeating mistakes)

**Deduplicate and prioritize:**
- Merge similar recommendations from multiple agents
- Prioritize by impact (high-value improvements first)
- Flag conflicting advice for human review
- Group by plan section

### 7.5. Post-Research Interview

After agents return and findings are synthesized, interview the user about what the research surfaced. Apply the deep interview protocol (see CLAUDE.md).

**Present contradictions with evidence:**

For each case where agent findings contradict a plan decision, use **AskUserQuestion** to challenge directly with citation:
- "The plan uses approach X, but [agent/source] recommends Y because [reason] ([link]). Should we revise, or is the plan's choice intentional?"
- Group related contradictions into clustered questions (2-3 per AskUserQuestion call) when they concern the same plan section.

**Confirm research-backed decisions:**

Briefly note where research supports the plan: "Research confirms [decision] is the right call -- [brief reason]." Don't turn this into a list of validations; just mention the significant ones.

**Probe unresolved tensions:**

If agents returned conflicting recommendations (e.g., one agent favors performance, another favors simplicity), present the tension and ask the user to resolve it.

**Capture decisions:**

Record all interview outcomes (revised decisions, confirmed choices, anti-requirements) for incorporation in the next step. Add a collapsed Q&A appendix to the enhanced plan:

```markdown
<details>
<summary>Deepening Interview Q&A</summary>

[Key questions, contradictions surfaced, and user decisions from the post-research interview.]

</details>
```

**Exit condition:** Claude assesses coverage and proposes stopping with confidence signal. User can always say "stop" to proceed immediately.

### 8. Enhance Plan Sections

<thinking>
Merge research findings and interview outcomes back into the plan, adding depth without changing the original structure.
</thinking>

**Enhancement format for each section:**

```markdown
## [Original Section Title]

[Original content preserved]

### Research Insights

**Best Practices:**
- [Concrete recommendation 1]
- [Concrete recommendation 2]

**Performance Considerations:**
- [Optimization opportunity]
- [Benchmark or metric to target]

**Implementation Details:**
```[language]
// Concrete code example from research
```

**Edge Cases:**
- [Edge case 1 and how to handle]
- [Edge case 2 and how to handle]

**References:**
- [Documentation URL 1]
- [Documentation URL 2]
```

### 9. Add Enhancement Summary

At the top of the plan, add a summary section:

```markdown
## Enhancement Summary

**Deepened on:** [Date]
**Sections enhanced:** [Count]
**Research agents used:** [List]

### Key Improvements
1. [Major improvement 1]
2. [Major improvement 2]
3. [Major improvement 3]

### New Considerations Discovered
- [Important finding 1]
- [Important finding 2]
```

### 10. Update Plan File

**Write the enhanced plan:**
- Preserve original filename
- Add `-deepened` suffix if user prefers a new file
- Update any timestamps or metadata

## Output Format

Update the plan file in place (or if user requests a separate file, append `-deepened` after `-plan`, e.g., `2026-01-15-feat-auth-plan-deepened.md`).

## Quality Checks

Before finalizing:
- [ ] All original content preserved
- [ ] Research insights clearly marked and attributed
- [ ] Code examples are syntactically correct
- [ ] Links are valid and relevant
- [ ] No contradictions between sections
- [ ] Enhancement summary accurately reflects changes

## Post-Enhancement Options

After writing the enhanced plan, use the **AskUserQuestion tool** to present these options:

**Question:** "Plan deepened at `[plan_path]`. What would you like to do next?"

**Options:**
1. **View diff** - Show what was added/changed
2. **Run `/workflows:review`** - Get feedback from reviewers on enhanced plan
3. **Start `/workflows:work`** - Begin implementing this enhanced plan
4. **Deepen further** - Run another round of research on specific sections
5. **Revert** - Restore original plan (if backup exists)

Based on selection:
- **View diff** → Run `git diff [plan_path]` or show before/after
- **`/workflows:review`** → Call the /workflows:review command with the plan file path
- **`/workflows:work`** → Call the /workflows:work command with the plan file path
- **Deepen further** → Ask which sections need more research, then re-run those agents
- **Revert** → Restore from git or backup

NEVER CODE! Just research and enhance the plan.
