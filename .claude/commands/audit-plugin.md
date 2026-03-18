---
name: audit-plugin
description: Deep quality audit of all skills, agents, and commands for inconsistencies, gaps, duplication, and token waste
argument-hint: "[optional: specific skill/agent/command name or category to focus on]"
---

# Audit plugin content

Deep analysis of all skills, agents, and commands in the compound-engineering plugin. Surfaces quality issues that degrade skill effectiveness, waste tokens, or confuse the model.

## Scope

```
PLUGIN_DIR=plugins/compound-engineering
```

If `$ARGUMENTS` specifies a name or category, narrow to that. Otherwise audit everything.

**Reactive mode:** If invoked after a skill/agent failed during use, detect the failing component from conversation context and focus the audit on that component first.

## Phase 1: Inventory

Read frontmatter + first section of every file:
- `$PLUGIN_DIR/skills/*/SKILL.md`
- `$PLUGIN_DIR/agents/**/*.md`
- `$PLUGIN_DIR/commands/**/*.md`

Build a map: name, description, type, approximate token count (chars / 4).

## Phase 2: Quality checks

Run these checks against every file. Use parallel subagents (model: sonnet) grouped by category to keep context manageable.

### Token efficiency

| Check | Signal |
|-------|--------|
| "Claude already knows this" | Content explaining what a technology is, how basic concepts work, or general programming knowledge that any LLM inherently knows |
| Redundant phrasing | Same idea stated twice in different words within the same file |
| Oversized examples | Code examples longer than needed to illustrate the pattern (>15 lines when 5 would suffice) |
| Inert frontmatter | Fields beyond `name` and `description` that Claude Code ignores (triggers, role, scope, domain, author, version, license) |
| Body over budget | Skill body > 2K tokens without `references/` split; agent > 3K tokens |

### Directive quality

| Check | Signal |
|-------|--------|
| Vague directives | "write clean code", "follow best practices", "keep it simple" without measurable criteria |
| Naked negations | "don't do X" without "do Y instead" |
| Directive count | >10 discrete rules in one file — adherence drops at scale, consolidate |
| Second person | "you should..." instead of imperative form (skills only, not agents) |
| Unmeasurable success criteria | "ensure quality" instead of "all tests pass, no type errors" |

### Consistency

| Check | Signal |
|-------|--------|
| Cross-reference integrity | Skill A references skill B, but B doesn't exist or was renamed |
| Terminology drift | Same concept called different names across files (e.g., "task" vs "step" vs "phase" for the same thing) |
| Conflicting rules | File A says "always X", file B says "never X" for the same situation |
| Description overlap | Two skills/agents with descriptions similar enough to confuse trigger selection |
| Process conflicts | Different ordering of the same workflow steps across files |

### Cross-type overlap (agents vs skills vs commands)

Check every agent-skill, agent-command, and skill-command pair for:

| Check | Signal |
|-------|--------|
| Agent wraps a skill with no added value | Agent description matches a skill description and the agent body just says "follow the X skill." If the agent adds no unique perspective (specialized role, tool restrictions, output format), flag it. |
| Command duplicates skill process | Command restates the same phases/steps already defined in a skill instead of delegating. The command should be a thin orchestration wrapper; process knowledge belongs in the skill. |
| Agent duplicates command | Agent and command serve the same purpose with overlapping scope (e.g., both review code, both plan features). One should defer to the other with a clear scope boundary. |
| Undocumented relationships | Agent uses a skill but neither file cross-references the other. Both should document the relationship in their Integration section. |
| Trigger confusion | An agent and a skill have similar enough descriptions that the model may invoke the wrong one. Descriptions must clearly differentiate when to use each. |

### Structural

| Check | Signal |
|-------|--------|
| Missing sections | Skill without success criteria, constraints, or procedural content (per SkillsBench quality dimensions) |
| Unlinked references | Files in `references/` or `scripts/` not linked from SKILL.md |
| Stale references | Links to files, commands, agents, or skills that don't exist |
| Heading style | Title Case where sentence case expected (per md-docs), non-actionable headings |

### Reference validation (mechanical -- run these checks via grep/glob)

1. **Markdown links resolve:** For every `[text](path)` link in skills, agents, and commands, verify the target file exists at the resolved path (relative to the file's directory). Flag broken links.
2. **Backtick skill/agent names exist:** For every backtick reference like `` `skill-name` `` or `` `agent-name` `` followed by "skill", "agent", or "command", verify a matching file exists in `skills/*/SKILL.md`, `agents/**/*.md`, or `commands/**/*.md`. Flag names that don't match any component.
3. **Slash command references exist:** For every `/command-name` reference, verify a matching command file exists with that `name:` in frontmatter. Flag stale `/command` references.
4. **Reference directories fully linked:** For every skill with a `references/` or `scripts/` subdirectory, list all files in that directory and verify each is linked from SKILL.md. Flag orphaned files.
5. **README.md accuracy:** Verify component count table matches actual counts (`ls skills/*/SKILL.md | wc -l`, etc.). Verify every skill/agent/command is listed in the appropriate README table. Verify category headings match actual agent counts (e.g., "Review (10)"). Flag missing entries and stale counts.
6. **Hook patterns current:** Verify `hooks/skill-patterns.sh` total count comment matches actual skill count. Verify no patterns reference deleted skills.

### Writing style (per md-docs + writing skill)

| Check | Signal |
|-------|--------|
| Verbose preambles | "This skill provides...", "The purpose of this section is..." |
| Passive voice in instructions | "Tests should be run" instead of "Run tests" |
| Filler phrases | "It's worth noting", "In order to", "It is important to" |
| Emoji in non-Discord content | Emoji headers or decorations outside changelog context |

### Consolidation opportunities

Every skill, agent, and command exposed adds to the system prompt token budget. Actively look for ways to reduce the total count:

| Check | Signal |
|-------|--------|
| Merge candidates | Two skills/agents that cover adjacent topics and could be combined without losing specificity (e.g., separate skills for "writing tests" and "test-driven development" could be one skill with a TDD section) |
| Absorption candidates | A small skill (<300 tokens) whose content fits naturally as a section in a larger related skill |
| Low-value components | Skills/agents that restate what Claude already knows with no project-specific or opinionated content — candidates for removal |
| Description-only overlap | Two components whose descriptions load similar tokens into context but serve different purposes — tighten descriptions to reduce wasted trigger-matching tokens |
| Unused agents | Agents not referenced by any command, skill, or workflow — candidates for removal unless they serve a standalone purpose |

Present consolidation proposals separately from quality findings: "These N components could be merged/removed, saving ~X tokens from the system prompt."

## Phase 3: Present findings

Sort by impact. Single table:

```
| # | File | Check | Issue | Severity | Fix |
|---|------|-------|-------|----------|-----|
```

Severity levels:
- **HIGH** — actively degrades skill effectiveness (conflicting rules, stale refs, broken cross-references)
- **MEDIUM** — wastes tokens or reduces clarity (filler, redundancy, oversized examples)
- **LOW** — style nit (heading case, phrasing preference)

Cap at 40 findings. Group by file when multiple issues affect the same file.

## Phase 4: Stress-test findings

Before presenting, apply meta-prompting patterns to each HIGH/MEDIUM finding:

- **Adversarial** — "Argue against fixing this. What breaks or gets worse if we change it?" Drop findings where the fix is worse than the issue.
- **Assumptions** — "What assumption does this finding rest on? Is that assumption valid for this specific skill?" Drop findings based on false assumptions.
- **Tensions** — "Does this fix conflict with another finding or an existing rule?" Resolve conflicts before presenting.

This prevents recommending changes that sound right in isolation but degrade the skill in context. Only findings that survive stress-testing make the final report.

## Phase 5: Apply approved changes

Ask: "Which items should I fix? (all / by number / high-only / skip)"

For approved items:
- Read the full target file before editing
- Make surgical edits — fix the specific issue, don't restructure
- After all edits, run `python3 distillery/scripts/distiller.py validate <name>` on modified distilled skills
- Run `bash scripts/update-metadata.sh` if components were added/removed

## Phase 6: Verify changes

After applying fixes, run the verification chain (stop on first failure):

1. **Validate modified skills** — `python3 distillery/scripts/distiller.py validate <name>` for each changed distilled skill. All must pass 7/7 gates.
2. **JSON integrity** — `jq . .claude-plugin/marketplace.json && jq . plugins/compound-engineering/.claude-plugin/plugin.json`
3. **Cross-reference check** — grep all modified files for references to other skills/agents/commands. Verify each target exists.
4. **Token budget check** — `python3 distillery/scripts/distiller.py token-count <file>` for each modified skill. Flag any that crossed the 2K threshold.
5. **Diff review** — `git diff` on all modified files. Confirm changes match approved items only, no unintended edits.

Present verification report:

```
Validation:    [PASS/FAIL] (N skills checked)
JSON:          [PASS/FAIL]
Cross-refs:    [PASS/FAIL] (N refs verified)
Token budgets: [PASS/FAIL] (list any over 2K)
Diff review:   [N files changed, M insertions, K deletions]
```

Do not claim completion until all checks pass. If any fail, fix and re-verify.

## Constraints

- Read-only until explicit approval
- Never delete entire sections without asking
- Never restructure a working skill to match a theoretical ideal
- Prefer trimming over splitting (splitting adds cross-file complexity)
- Agent "You are a..." preambles are prompt engineering, not documentation — different rules apply
