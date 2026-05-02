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
PLUGIN_DIR=plugins/whetstone
SYNC_LOG=docs/audit/audit-log.md
```

## Phase 0: Pre-flight — read prior decision log

Read `$SYNC_LOG` in full before any analysis. Build an in-memory set of already-evaluated findings keyed by `(component, pattern-signature)` across every run entry. Use it as a filter during Phase 3 and Phase 4:

- **Previously applied, exact match** — drop silently.
- **Previously rejected, exact match** — drop silently unless new evidence contradicts the prior reason; if so, surface with a `RE-EVALUATE` flag and quote the prior rejection reason.
- **Previously deferred, exact match** — surface with a `PREVIOUSLY DEFERRED` tag and the original defer reason so the user can judge whether conditions have changed.
- **No match** — present normally.

While reading, also detect prune triggers. Emit a one-line reminder at the end of Phase 4 if any fire:

- Any entry older than 30 days.
- Any entry referencing a component that no longer exists under `$PLUGIN_DIR` (skill, agent, or command path missing).
- Any entry referencing an external repo no longer present in `$REPOS_DIR`.
- Any entry whose rejection reason duplicates a rule now in `MEMORY.md` (superseded).

Reminder format: "Sync log has N prune candidates (age: X, stale-ref: Y, abandoned-source: Z, superseded: W) — run `/prune-sync-log`."

If `$SYNC_LOG` doesn't exist, note it and continue — the post-apply step in Phase 5b creates it.

## Phase 1: Pull latest and refresh eval data

```bash
cd ~/ai/repos && bash pull-all.sh
```

If `pull-all.sh` doesn't exist, `git pull` each repo directory individually.

Launch `harvest-sessions` as a background subagent in parallel with Phase 2. This refreshes eval data so `discover-signals` (Phase 6) and `/audit-plugin` both operate on current session data.

```bash
python3 distillery/scripts/distiller.py harvest-sessions
```

## Phase 2: Inventory

Build two inventories in parallel:

**Ours** — read frontmatter (name + description) from every file in:
- `$PLUGIN_DIR/skills/*/SKILL.md`
- `$PLUGIN_DIR/agents/**/*.md`
- `$PLUGIN_DIR/commands/**/*.md`

**Theirs** — for EVERY repo in `$REPOS_DIR/`, find skill/agent/command content using parallel subagents (one per repo). Each subagent must:

1. **Discover all content files**: `SKILL.md`, `*.md` in `skills/`, `agents/`, `commands/`, `.claude/`, `.agents/`, `plugins/`, `categories/`, `specialized/`, `engineering/`, `strategy/`, `integrations/`, and any other non-standard directories. Also check root-level `.md` files (CLAUDE.md, AGENTS.md) for embedded rules and patterns.
2. **Read promising files in full** (not just first 50 lines). Read at minimum the 15-20 most substantial files per repo. For repos with fewer files, read all of them.
3. **Extract**: name, description, specific actionable patterns/rules/techniques, quality assessment, and whether it adds value over our existing content.
4. **Analyze agents and commands** with the same rigor as skills. Agent frontmatter patterns (tools, model, maxTurns, paths, memory), command orchestration workflows, and hook configurations are all in scope.
5. **Skip**: README, LICENSE, CONTRIBUTING, CHANGELOG, config files, and generic persona descriptions without actionable rules.

Every repo must be analyzed. Do not skip repos based on surface-level impressions. Repos that look simple may contain high-quality patterns in non-obvious locations.

**Loose notes at `$REPOS_DIR/` root** — also scan `*.md` files sitting directly in `$REPOS_DIR/` (not inside a repo subdirectory). These are reference docs Ilia dropped in for cross-repo harvesting. Read each in full, extract actionable patterns, and feed them into Phase 3 the same way as repo content. Source tag: `loose:<filename>`. Skip if the file is obviously not a reference doc (e.g., a stray export, a tarball listing).

If `$ARGUMENTS` specifies a skill or repo, narrow scope to that.

## Phase 2b: Skills.sh marketplace scan

For each existing skill in the plugin inventory, search for marketplace counterparts:

```bash
python3 distillery/scripts/distiller.py search "<skill-name>"
```

**Triage before fetching:** Same rules as repos -- scan descriptions, skip generic checklists and low-relevance matches. Only fetch sources that suggest genuinely new patterns for an existing skill.

For promising matches, fetch and stage:

```bash
python3 distillery/scripts/distiller.py fetch --skills '<JSON from search>'
```

Read the staged SKILL.md files. These feed into Phase 3 alongside repo findings -- same cross-reference analysis, same quality filters, same approval flow.

**Scope control:** If `$ARGUMENTS` specifies a skill name, only search marketplace for that skill. If running a full scan, cap at the top 3 marketplace results per skill to keep the analysis manageable.

**Cleanup after analysis:**

```bash
python3 distillery/scripts/distiller.py cleanup
```

## Phase 3: Cross-reference analysis

For each external skill, agent, command, or pattern found, classify:

### Additions (not covered by any existing component)

New capability worth creating? Evaluate:
- Does it fill a gap in the plugin's coverage?
- Is the pattern general enough to be useful across projects?
- Would it trigger distinctly from existing components (no description overlap)?
- What component type fits best? Skill (ambient behavior), command (explicit invocation), or agent (specialized persona for subagent dispatch)?

### Improvements (strengthens an existing skill, agent, or command)

Specific patterns, rules, or techniques from external sources that would improve an existing component. Evaluate:
- Is the content genuinely new (not already covered, even if worded differently)?
- Is it actionable and measurable (not generic advice)?
- Does it fit the component's scope without bloating it?
- Would it push the body over budget (skill > 4K tokens, agent > 3K, command > 4K)? If so, propose as a `references/` file instead.

**Agent-specific improvements** to look for:
- Better frontmatter patterns (model selection, tools restriction, maxTurns, paths)
- Persona design techniques (stronger role framing, output format constraints)
- Tool restriction patterns (read-only agents, scoped permissions)

**Command-specific improvements** to look for:
- Orchestration patterns (how commands coordinate agents and skills)
- Argument handling and mode detection
- File-based state machines for long-running workflows
- User approval gates between phases

### Cross-type analysis

External content often has implications beyond its own component type. A repo's skill may contain a workflow pattern that belongs in one of our commands. An agent's persona constraints may encode behavioral rules that strengthen a skill. A command's orchestration logic may reveal a reusable pattern worth capturing as a skill.

After classifying each external finding by its direct type match, also ask:
- Does this pattern apply to a component of a **different** type in our plugin?
- Could a skill's behavioral rule improve a command's orchestration (or vice versa)?
- Could an agent's persona technique or tool restriction inform a skill's constraints?
- Could a command's phased workflow reveal a general pattern worth embedding as ambient skill behavior?

When a cross-type insight exists, log it as a separate finding row with the actual target component, not the source type. Example: an external skill about code review contains a "present findings sorted by severity" pattern — if our `/ia-review` command doesn't do that, the finding targets the command, not our code-review skill.

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

External component that fully overlaps an existing skill, agent, or command with no new value. Note and skip.

## Phase 4: Present findings

Sort ALL findings by impact (highest first), not by category. Use a single table:

```
| # | Type | Component/Target | Finding | Source repo | Impact |
|---|------|-----------------|---------|-------------|--------|
| 1 | IMPROVE | code-review (skill) | [specific pattern] | gstack | HIGH |
| 2 | ADD | git-commit (command) | [what it does] | agent-skills | HIGH |
| 3 | IMPROVE | security-sentinel (agent) | [agent pattern] | agency-agents | MEDIUM |
```

For each finding, include:
- **What**: the specific pattern, rule, or technique (not vague)
- **Why**: what problem it solves that current content doesn't address
- **Counter-argument**: reason it might NOT be worth adding
- **Recommendation**: INCORPORATE / SKIP / NEEDS DISCUSSION

Show top 30 findings by impact. If more exist, state the count and ask: "N more findings below the cut. Show remaining? (yes / high-only / skip)"

## Phase 5: Apply approved changes

After user reviews findings:

**Do not proceed without explicit approval.** Ask: "Which items should I apply? (all / pick by number / skip)"

For approved items:
1. Read the target skill/agent/command fully before editing
2. Make surgical edits — add content, don't restructure
3. Validate against skill compliance checklist (CLAUDE.md) for skills; check agent frontmatter patterns for agents; verify command orchestration delegates to skills for commands
4. Run `bash scripts/update-metadata.sh` if components were added/removed

## Phase 5b: Append to decision log

After applying changes (or deciding to skip everything), append one run entry to `$SYNC_LOG` under the `## Log` marker. Every proposed finding from Phase 4 must land in exactly one bucket — applied, rejected, or deferred — with one-line reasoning. Rejection reasons are the most valuable part of this log; do not omit them.

Entry format:

```markdown
## [YYYY-MM-DD] sync | Scope: <full | skill-name | repo-name>

Run context: <external repos scanned or specific focus>

### Applied
- `<component>`: <what changed> (impact: H|M|L) -- <source>

### Rejected
- `<component>`: <proposed change> -- <specific reason>

### Deferred
- `<component>`: <proposed change> -- <reason + revisit condition>
```

If a rejection reason generalizes to "we never do X because Y", also propose promoting it to a feedback-memory entry and link to the memory file from the log bullet instead of repeating the reasoning.

## Phase 6: Discover new signals and outcome anomalies

Run signal discovery and outcome analysis on the freshly harvested data:

```bash
python3 distillery/scripts/distiller.py discover-signals --top 20
python3 distillery/scripts/distiller.py analyze-outcomes
```

**discover-signals**: Surfaces new patterns of user dissatisfaction not yet captured by `_NEGATIVE_SIGNAL_PATTERNS`. If candidates are found, present them for review. For confirmed patterns, promote to `_NEGATIVE_SIGNAL_PATTERNS` in `distiller.py` so future harvests classify them correctly.

**analyze-outcomes**: Surfaces (skill, project) pairs where negative rate exceeds the global average by >10pp. Cross-reference anomalies against project-type constraints in `skill-patterns.sh` -- if a domain skill is consistently negative in a project whose type doesn't match, recommend adding a `SKILL_PROJECT_TYPES` entry to prevent injection.

This runs after sync (not during audit) because both analyses benefit from the broadest possible session scan, and any new patterns or constraint recommendations need to be in place before the audit runs.

## Phase 7: Post-sync audit

After applying changes, recommend running the audit on modified components:

"Changes applied. Run `/audit-plugin [modified-skill-names]` to check for inconsistencies introduced by external content?"

External source changes are the most likely to introduce conflicting rules, terminology drift, or stale references. The audit catches what the sync's quality filters miss.

## Constraints

- Never delete existing content without asking
- Never create new skills/agents without approval — only propose them
- Never modify files outside the plugin directory without asking
- Every repo must get a deep pass — do not skip repos based on surface impressions. Use parallel subagents (one per repo) to keep analysis thorough without being slow.
- Triage happens AFTER reading, not before. Read the content, then decide if it's actionable. The exception: files that are clearly project-specific tooling (e.g., a company's deploy script) can be skipped on sight.
- Analyze skills, agents, AND commands with equal rigor. Agent frontmatter patterns (tools, model, maxTurns, paths), command orchestration workflows, and hook configurations are all in scope.
- If an external source is a generic checklist with no measurable criteria, note it as low-quality and move on
