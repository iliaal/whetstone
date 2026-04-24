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
SYNC_LOG=docs/audit/audit-log.md
```

If `$ARGUMENTS` specifies a name or category, narrow to that. Otherwise audit everything.

**Reactive mode:** If invoked after a skill/agent failed during use, detect the failing component from conversation context and focus the audit on that component first.

## Phase 0: Pre-flight — read prior decision log

Read `$SYNC_LOG` in full before any checks run. Build an in-memory set of already-evaluated findings keyed by `(component, issue-signature)` across every run entry. Use it as a filter during Phase 3 presentation:

- **Previously applied, exact match** — drop silently.
- **Previously rejected, exact match** — drop silently unless new evidence contradicts the prior reason; if so, surface with a `RE-EVALUATE` flag and quote the prior rejection reason.
- **Previously deferred, exact match** — surface with a `PREVIOUSLY DEFERRED` tag and the original defer reason so the user can judge whether conditions have changed.
- **No match** — present normally.

While reading, also detect prune triggers and emit a one-line reminder at the end of Phase 3 if any fire:

- Any entry older than 30 days.
- Any entry referencing a component that no longer exists under `$PLUGIN_DIR`.
- Any entry whose reasoning has been superseded by a feedback-memory rule.

Reminder format: "Sync log has N prune candidates — run `/prune-sync-log`."

If `$SYNC_LOG` doesn't exist, note it and continue — the post-apply step in Phase 5b creates it.

## Phase 1: Mechanical validation (deterministic, no AI)

Run the full deterministic validation pass first. This replaces manual inventory, validation gates, anti-pattern detection, structural checks, and reference validation with a single script:

```bash
python3 distillery/scripts/distiller.py validate-plugin
python3 distillery/scripts/distiller.py test-triggers
```

`validate-plugin` checks every skill, agent, and command for:
- Frontmatter: exists, valid YAML, no inert fields, name format, description length (<80 tokens), "Use when" trigger phrase
- Anti-patterns: OVER_CONSTRAINED, BLOATED_SKILL, EMPTY_DESCRIPTION, MISSING_TRIGGER, VAGUE_DESCRIPTION, ORPHAN_REFERENCE, DEAD_CROSS_REF, DUPLICATE_TRIGGER, STALE_VERSION_PIN
- Structural: placeholder text, empty sections, missing headings
- Body size: skills >4K, agents >3K, commands >4K tokens
- Reference integrity: orphaned files in references/scripts dirs, backtick references to nonexistent components
- README and hook pattern count accuracy

The output is a structured JSON report with inventory counts and per-component findings sorted by severity. Include all findings in the Phase 3 presentation alongside AI-generated findings.

`test-triggers` runs the regex regression suite. Include any failing skills as HIGH severity.

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

Note: Many structural completeness checks (frontmatter, references) are already covered by Phase 1's `validate-plugin`. Focus PluginEval scoring on the qualitative dimensions that need AI judgment.

## Phase 2: Quality checks

Run these checks against every file. Use parallel subagents (model: sonnet) grouped by category to keep context manageable.

### Token efficiency

These checks require AI judgment. Inert frontmatter and body size are already covered by `validate-plugin`.

| Check | Signal |
|-------|--------|
| "Claude already knows this" | Content explaining what a technology is, how basic concepts work, or general programming knowledge that any LLM inherently knows |
| Redundant phrasing | Same idea stated twice in different words within the same file |
| Oversized examples | Code examples longer than needed to illustrate the pattern (>15 lines when 5 would suffice) |

### Directive quality

| Check | Signal |
|-------|--------|
| Vague directives | "write clean code", "follow best practices", "keep it simple" without measurable criteria |
| Naked negations | "don't do X" without "do Y instead" |
| Directive count | >10 discrete rules in one file — adherence drops at scale, consolidate |
| Second person | "you should..." instead of imperative form (skills only, not agents) |
| Unmeasurable success criteria | "ensure quality" instead of "all tests pass, no type errors" |

### Consistency

Cross-reference integrity and description overlap are already covered by `validate-plugin`. Focus AI analysis on semantic issues:

| Check | Signal |
|-------|--------|
| Terminology drift | Same concept called different names across files (e.g., "task" vs "step" vs "phase" for the same thing) |
| Conflicting rules | File A says "always X", file B says "never X" for the same situation |
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
| Injection misfires | Run `python3 distillery/scripts/distiller.py analyze-misfires` (uses eval data from Phase 0 harvest). Skills with misfire rate > 20% have overly broad patterns. Include misfire findings as HIGH severity with the skill name, misfire rate, irrelevant task samples, and suggested regex tightening. |
| Project-context anomalies | Run `python3 distillery/scripts/distiller.py analyze-outcomes`. Skills whose negative rate in a specific project exceeds the global average by >10pp are underperforming in that context. Include anomalies as MEDIUM severity with skill name, project, negative rate, global rate, and delta. Cross-reference with project-type constraints in `skill-patterns.sh` -- if a skill lacks a constraint that would prevent the misfire, recommend adding one. |
| Negative signal diagnosis | For skills with a high ratio of negative-signal sessions (>30% of examples), run `python3 distillery/scripts/distiller.py diagnose-negatives <skill>`. Include the diagnosed failure patterns and suggested skill text improvements as MEDIUM/HIGH findings. This catches skills that are injected correctly but produce poor output. |

### Structural (AI-only checks)

Orphan references, dead cross-refs, README counts, and hook pattern counts are already covered by `validate-plugin`. Focus AI analysis on semantic structural issues:

| Check | Signal |
|-------|--------|
| Missing sections | Skill without success criteria, constraints, or procedural content (per SkillsBench quality dimensions) |
| Heading style | Title Case where sentence case expected (per md-docs), non-actionable headings |

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

Show top 40 findings by severity. Group by file when multiple issues affect the same file. If more exist, state the count and ask: "N more findings below the cut. Show remaining? (yes / high-only / skip)"

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

## Phase 5b: Append to decision log

After applying changes (or deciding to skip everything), append one run entry to `$SYNC_LOG` under the `## Log` marker. Every finding presented in Phase 3 must land in exactly one bucket — applied, rejected, or deferred — with one-line reasoning. Rejection reasons (especially for false-positive validator findings and stress-test drops from Phase 4) are the most valuable forensic record.

Entry format:

```markdown
## [YYYY-MM-DD] audit | Scope: <full | component-name | category>

Run context: <reactive mode target or full-audit scope>

### Applied
- `<component>`: <fix> (severity: H|M|L) -- <brief reason if non-obvious>

### Rejected
- `<component>`: <proposed fix> -- <specific reason: false positive, fix worse than issue, invalid assumption, etc.>

### Deferred
- `<component>`: <proposed fix> -- <reason + revisit condition>
```

If a rejection reason generalizes to a reusable rule, propose promoting it to a feedback-memory entry (e.g., `feedback_audit_false_positives.md`) and reference the memory file from the log bullet rather than repeating the reasoning.

## Phase 6: Verify changes

After applying fixes, run the verification chain (stop on first failure):

1. **Validate modified skills** — `python3 distillery/scripts/distiller.py validate <name>` for each changed distilled skill. All must pass 7/7 gates.
2. **Trigger regression tests** — `python3 distillery/scripts/distiller.py test-triggers`. All skills must pass. If a pattern was modified, update fixtures in `distillery/tests/fixtures/triggers/<skill>.jsonl`.
3. **JSON integrity** — `jq . .claude-plugin/marketplace.json && jq . plugins/compound-engineering/.claude-plugin/plugin.json`
4. **Cross-reference check** — grep all modified files for references to other skills/agents/commands. Verify each target exists.
5. **Token budget check** — `python3 distillery/scripts/distiller.py token-count <file>` for each modified skill. Flag any above 4K tokens.
6. **Diff review** — `git diff` on all modified files. Confirm changes match approved items only, no unintended edits.

## Phase 7: Full test suite

After Phase 6 verification passes, re-run the complete test suite to catch any regressions introduced by the fixes:

```bash
python3 -m pytest distillery/scripts/test_distiller.py -x
python3 distillery/scripts/distiller.py test-triggers
python3 distillery/scripts/distiller.py test-semantic --max-tests 5
```

Pytest and test-triggers must pass. test-semantic failures are warnings -- review but don't block on them (model behavior varies between runs).

Present final report:

```
Validation:    [PASS/FAIL] (N skills checked)
Triggers:      [PASS/FAIL] (N skills, M test cases)
Semantic:      [PASS/WARN] (N passed, M failed, K inconclusive)
JSON:          [PASS/FAIL]
Cross-refs:    [PASS/FAIL] (N refs verified)
Token budgets: [PASS/FAIL] (list any over 4K)
Unit tests:    [PASS/FAIL] (N tests)
Diff review:   [N files changed, M insertions, K deletions]
```

Do not claim completion until all checks pass. If any fail, fix and re-verify.

## Constraints

- Read-only until explicit approval
- Never delete entire sections without asking
- Never restructure a working skill to match a theoretical ideal
- Prefer trimming over splitting (splitting adds cross-file complexity)
- Agent "You are a..." preambles are prompt engineering, not documentation — different rules apply
