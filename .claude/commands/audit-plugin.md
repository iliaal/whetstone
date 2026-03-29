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

## Phase 1b: PluginEval scoring

Score each component against these 10 weighted dimensions. Use the weights to prioritize findings -- issues in high-weight dimensions get higher severity.

| Dimension | Weight | What to measure |
|-----------|--------|-----------------|
| **Triggering accuracy** | 25% | Does the description cause correct activation? Check for missing synonyms, false-positive triggers, description/content mismatch |
| **Orchestration fitness** | 20% | Does the component compose well with others? Check cross-references, handoff clarity, scope boundaries |
| **Output quality** | 15% | Does the component define what it produces? Check for output format specs, templates, success criteria |
| **Scope calibration** | 12% | Does the component stay in its lane? Check for scope creep, overlap with adjacent components |
| **Progressive disclosure** | 10% | Does it load only what's needed? Check body size, references/ split, conditional sections |
| **Token efficiency** | 6% | Does it waste tokens? Check for "Claude already knows this" content, redundancy, verbose examples |
| **Robustness** | 5% | Does it handle edge cases? Check for missing error paths, ambiguous instructions |
| **Structural completeness** | 3% | Frontmatter correct? Required sections present? References linked? |
| **Code template quality** | 2% | Do bundled scripts work? Are they referenced correctly? |
| **Ecosystem coherence** | 2% | Consistent naming, tone, terminology with the rest of the plugin? |

### Named anti-patterns (auto-flag)

Flag these automatically during the audit. Each is a specific, testable condition:

| Anti-pattern | Detection | Severity |
|-------------|-----------|----------|
| **OVER_CONSTRAINED** | >15 MUST/ALWAYS/NEVER directives in one file | MEDIUM |
| **BLOATED_SKILL** | Skill body >800 lines with no references/ directory | HIGH |
| **EMPTY_DESCRIPTION** | Description <20 characters | HIGH |
| **MISSING_TRIGGER** | Skill description doesn't say "Use when..." | MEDIUM |
| **ORPHAN_REFERENCE** | File in references/ not linked from SKILL.md | MEDIUM |
| **DEAD_CROSS_REF** | Link to a skill/agent/command that doesn't exist | HIGH |
| **DUPLICATE_TRIGGER** | Two components with >70% description keyword overlap | MEDIUM |
| **STALE_VERSION_PIN** | Content says "as of v3.2" or "since 2024" without verification | LOW |

## Phase 2: Quality checks

Run these checks against every file. Use parallel subagents (model: sonnet) grouped by category to keep context manageable.

### Token efficiency

| Check | Signal |
|-------|--------|
| "Claude already knows this" | Content explaining what a technology is, how basic concepts work, or general programming knowledge that any LLM inherently knows |
| Redundant phrasing | Same idea stated twice in different words within the same file |
| Oversized examples | Code examples longer than needed to illustrate the pattern (>15 lines when 5 would suffice) |
| Inert frontmatter | Fields beyond `name` and `description` that Claude Code ignores (triggers, role, scope, domain, author, version, license) |
| Body over budget | Skill body > 2K tokens without `references/` split; agent > 3K tokens; command > 4K tokens |

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

### Agent-specific checks

| Check | Signal |
|-------|--------|
| Missing `model:` | Agent doesn't declare a model override. Review agents and research agents that don't need heavy reasoning should use `model: haiku` or `model: sonnet` to reduce cost. Only flag when a cheaper model would clearly suffice. |
| Persona without perspective | Agent body is generic instructions that any skill could provide. An agent must add a unique perspective (specialized role, constrained scope, output format, tool restrictions) beyond what the referenced skill already covers. |
| Overly broad tools | Purely analytical agents (reviewers, analyzers, researchers) that could work with read-only tools but inherit full write permissions. Flag agents whose job is analysis but who could accidentally write files. |
| Missing `description:` trigger phrases | Agent description doesn't clearly state when it should be invoked. Compare against similar agents for trigger differentiation. |
| Category misplacement | Agent filed under wrong category directory (e.g., a review agent in `workflow/` or a research agent in `review/`). |

### Command-specific checks

| Check | Signal |
|-------|--------|
| Inlined process logic | Command contains step-by-step process that should live in a skill. Commands should orchestrate (decide what to run, in what order), not instruct (how to do the work). |
| Missing argument handling | Command declares `argument-hint:` but body doesn't reference `$ARGUMENTS` or explain argument behavior. |
| No skill delegation | Command does all work inline without referencing or delegating to any skill. If the command's domain has a matching skill, the command should delegate. |
| Unclear output | Command doesn't specify where results go (file path, conversation, both) or what format they take. |

### Temporal accuracy

| Check | Signal |
|-------|--------|
| Version-pinned statements | "as of v3.2", "since 2024", "if using React 18" -- claims that may be outdated. Either remove the version qualifier to state the pattern as current default, or flag for manual verification. |
| Date-dependent advice | "recently added", "new in", "upcoming" -- relative time references that rot. Convert to absolute or remove. |
| Deprecated bifurcations | "if using old version, do X; if using new version, do Y" -- if the old version is no longer relevant, remove the fork and keep only the current path. |

### Trigger coverage

| Check | Signal |
|-------|--------|
| Description keyword gaps | Skill or command description missing obvious synonyms or alternate phrasings a user might say. Compare the description's trigger phrases against the component's actual domain. E.g., a "writing-tests" skill whose description says "tests" but not "specs", "assertions", "coverage", or "test suite". |
| Trigger pattern accuracy | For skills with patterns in `hooks/skill-patterns.sh`, run `python3 distillery/scripts/distiller.py eval-triggers <name>` with 3-5 should-trigger and 3-5 should-not-trigger queries. Flag patterns with F1 < 0.8. |

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
| Merge candidates | Two skills/agents/commands that cover adjacent topics and could be combined without losing specificity (e.g., separate skills for "writing tests" and "test-driven development" could be one skill with a TDD section) |
| Absorption candidates | A small component (<300 tokens) whose content fits naturally as a section in a larger related component |
| Low-value components | Skills/agents/commands that restate what Claude already knows with no project-specific or opinionated content — candidates for removal |
| Description-only overlap | Two components whose descriptions load similar tokens into context but serve different purposes — tighten descriptions to reduce wasted trigger-matching tokens |
| Unused agents | Agents not referenced by any command, skill, or workflow — candidates for removal unless they serve a standalone purpose |
| Bloated commands | Commands that inline process knowledge instead of delegating to skills. Commands should be thin orchestration wrappers — process logic belongs in skills. |

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

- **Mechanical verification** — For HIGH/MEDIUM findings that claim something is missing or broken (missing autoApprove, orphan reference, stale name), verify the claim by reading the actual file before including it. Subagent reports contain false positives.

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
