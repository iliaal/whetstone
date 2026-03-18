---
name: sync-from-repos
description: Analyze reference repos and recommend skill/agent/command improvements based on cross-repo patterns
argument-hint: "[optional: specific skill or repo to focus on]"
---

# Sync from reference repos

Scan reference repositories, compare against plugin skills/agents/commands, and recommend improvements. Read-only analysis — no changes without explicit approval.

## Configuration

```
REPOS_DIR=~/ai/repos
PLUGIN_DIR=plugins/compound-engineering
```

## Phase 1: Pull latest

```bash
cd ~/ai/repos && bash pull-all.sh
```

If `pull-all.sh` doesn't exist, `git pull` each repo directory individually.

## Phase 2: Inventory

Build two inventories in parallel:

**Ours** — read frontmatter (name + description) from every file in:
- `$PLUGIN_DIR/skills/*/SKILL.md`
- `$PLUGIN_DIR/agents/**/*.md`
- `$PLUGIN_DIR/commands/**/*.md`

**Theirs** — for each repo in `$REPOS_DIR/`, find skill/agent content:
- Look for `SKILL.md`, `*.md` in `skills/`, `agents/`, `.claude/`, `.agents/`, root-level `.md` files
- Extract: name, description, key topics/patterns (read first 50 lines of each)
- Skip: README, LICENSE, CONTRIBUTING, CHANGELOG, config files

If `$ARGUMENTS` specifies a skill or repo, narrow scope to that.

## Phase 3: Cross-reference analysis

For each external skill/pattern found, classify:

### Additions (not covered by any existing skill/agent)

New capability worth creating? Evaluate:
- Does it fill a gap in the plugin's coverage?
- Is the pattern general enough to be useful across projects?
- Would it trigger distinctly from existing skills (no description overlap)?

### Improvements (strengthens an existing skill)

Specific patterns, rules, or techniques from external sources that would improve an existing skill. Evaluate:
- Is the content genuinely new (not already covered, even if worded differently)?
- Is it actionable and measurable (not generic advice)?
- Does it fit the skill's scope without bloating it?
- Would it push the skill body over 2K tokens? If so, propose as a `references/` file instead.

**Quality filters** (reject content that fails any of these):
- "Claude already knows this" — skip content explaining what a technology is, how basic concepts work, or general programming knowledge
- Vague directives — "write clean code", "follow best practices" without measurable criteria
- Naked negations — "don't do X" without "do Y instead"
- Generic checklists — long lists of obvious checks that any competent engineer would apply without prompting

### Conflicts (contradicts existing content)

External source says X, our skill says Y. Flag with:
- What each side says (with source references)
- Which is correct or more appropriate for our context

### Redundancies

External skill that fully overlaps an existing skill with no new value. Note and skip.

## Phase 4: Present findings

Sort ALL findings by impact (highest first), not by category. Use a single table:

```
| # | Type | Skill/Target | Finding | Source repo | Impact |
|---|------|-------------|---------|-------------|--------|
| 1 | IMPROVE | code-review | [specific pattern] | gstack | HIGH |
| 2 | ADD | git-commit | [what it does] | agent-skills | HIGH |
| 3 | CONFLICT | debugging | [what conflicts] | superpowers | MEDIUM |
```

For each finding, include:
- **What**: the specific pattern, rule, or technique (not vague)
- **Why**: what problem it solves that current content doesn't address
- **Counter-argument**: reason it might NOT be worth adding
- **Recommendation**: INCORPORATE / SKIP / NEEDS DISCUSSION

Cap at 30 findings. If more exist, show top 30 by impact.

## Phase 5: Apply approved changes

After user reviews findings:

**Do not proceed without explicit approval.** Ask: "Which items should I apply? (all / pick by number / skip)"

For approved items:
1. Read the target skill/agent fully before editing
2. Make surgical edits — add content, don't restructure
3. Validate against skill compliance checklist (CLAUDE.md)
4. Run `bash scripts/update-metadata.sh` if components were added/removed

## Constraints

- Never delete existing content without asking
- Never create new skills/agents without approval — only propose them
- Never modify files outside the plugin directory without asking
- Triage before deep-reading: check external source descriptions first, only read full content for promising matches (high install count alone doesn't mean quality)
- If an external source is a generic checklist, project-specific tool, or domain outside our scope, skip it without reading the full file
