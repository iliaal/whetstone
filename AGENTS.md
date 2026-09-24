# Whetstone

Claude Code plugin for PHP/React/Python/JavaScript/TypeScript workflows. Includes the plugin (agents, commands, skills, hooks), a skill distillery, and a CLI for cross-tool conversion.

When you see a `<session-commands>` tag in hook context, briefly list those commands to the user at the start of your first response.

## Repository structure

```
whetstone/
├── .claude-plugin/
│   └── marketplace.json          # Marketplace catalog
├── distillery/                   # Skill distillery (generate skills from skills.sh)
│   ├── scripts/
│   │   ├── distiller.py          # Search, fetch, validate, eval, harvest, test
│   │   └── test_distiller.py     # pytest tests for distiller
│   └── generated-skills/         # Generated skill output directory
├── scripts/
│   ├── update-metadata.sh        # Update component counts in plugin.json + marketplace.json
│   ├── generate-skill-hooks.sh   # Generate hook patterns from SKILL.md frontmatter
│   ├── mirror-to-ai-skills.sh    # Mirror plugin skills to ai-skills public repo
│   ├── configure-codex-skill-sources.py # Disable duplicate direct sources in Codex
│   ├── install-codex-plugin.sh  # Install/enable plugin, then retire duplicate sources
│   ├── refresh-codex-plugin.sh  # Cachebust/reinstall Codex without dirtying release version
│   ├── sync-to-tools.sh          # Symlink skills to .agents/.kilocode; retire legacy Codex links
│   └── update-plugin.sh          # Update locally installed plugin to latest version
├── CHANGELOG.md                 # Version history
└── plugins/
    └── whetstone/     # The plugin
        ├── .codex-plugin/
        │   └── plugin.json      # Codex skills-plugin metadata
        ├── .claude-plugin/
        │   └── plugin.json      # Plugin metadata
        ├── agents/              # Agents (all `ia-<name>.md`, flat layout)
        ├── shared-references/   # Cross-agent reference content loaded by agents via Read
        ├── commands/            # Slash commands (all `ia-<name>.md`)
        │   └── references/      # Non-invocable reference content (not prefixed)
        ├── skills/              # Skills (all `ia-<name>/`)
        │   └── ia-<skill-name>/
        │       ├── SKILL.md        # Skill content
        │       ├── references/     # Optional supplementary docs
        │       └── scripts/        # Optional bundled scripts
        ├── hooks/               # 1 hook (inject-skills into subagents)
        └── README.md            # Plugin documentation
```

## Working agreement

- Do not delete or overwrite user data. Avoid destructive commands.
- Hyphens for all file naming (agents, skills, commands).
- Agents omit `model:` unless overriding (e.g., `model: haiku`).
- Agents reference skills (one-directional); skills stay generic and portable.
- **Read before claiming "new"**: Before presenting sync/improvement findings, read the target skill to verify the pattern isn't already covered. Saves round-trips.
- **Present changes one at a time** for review decisions. Batch presentation only when explicitly asked.
- **No off-stack content**: Skip or replace code examples, references, and patterns for languages/frameworks the team doesn't use (Ruby/Rails, Java, Swift, etc.). Use PHP, Python, or TypeScript equivalents. Generic SQL or framework-agnostic examples are fine when no specific stack fits.
- **No personal-machine paths in plugin files.** The plugin is published externally (mirrored to ai-skills, shipped to ClawHub, synced to `.agents`/`.codex`/`.kilocode`). Anything under `plugins/whetstone/` must be self-contained and runnable by a stranger — no references to `~/ai/wiki/`, `~/ai/repos/`, `/home/ilia/`, private Linear/Slack/Grafana URLs, or any other path specific to one machine or org. If a pattern's deep reference lives in `~/ai/wiki/`, embed enough actionable content inline that the skill works without the wiki; do not leave pointer lines like "see the wiki at ..." in published files. Use `git grep -n '~/ai/\|/home/' -- plugins/` before shipping to catch stragglers. Search tracked files only: a plain `grep -rn` also walks gitignored build artifacts (`evals/results/`, `__pycache__/`) that never ship, so it reports stragglers that do not exist. The tracked hits that remain are the `SPEC.md` lines documenting this rule.

## Versioning

**Version bumps, CHANGELOG entries, and README count updates happen during `/release`, not per-change.** Editing a skill, agent, or command does not trigger any version ceremony. Make the change, commit it with a descriptive message, move on. Let work accumulate across multiple commits until a release is cut.

One CHANGELOG entry per release keeps what shipped reconstructable; per-change entries fragment it.

When `/release` runs, it:

1. Bumps the version in `plugins/whetstone/.claude-plugin/plugin.json`, `plugins/whetstone/.codex-plugin/plugin.json`, and `.claude-plugin/marketplace.json`
2. Appends a CHANGELOG.md entry summarizing the commits since the last release
3. Updates README.md component counts and tables
4. Runs `bash scripts/update-metadata.sh` to sync descriptions and counts
5. Validates JSON, then runs the pre-commit gates in order with these blocking statuses:
   - `update-metadata.sh --check` — **BLOCKING** (metadata/count drift)
   - `validate-plugin` — **BLOCKING on HIGH** findings (machine-path leaks, dead cross-refs, phantom agents, orphan references)
   - `validate-cross-refs.sh` — **BLOCKING** (broken reference links; also rejects path-style links to a sibling skill, which resolve locally but break in the ai-skills mirror)
   - native Codex plugin regression (`test-codex-plugin.sh`) — **BLOCKING**
   - trigger regression tests (`test-triggers`) — **BLOCKING**
   - Tier-1 prompt-injection corpus scan — **BLOCKING on HIGH** findings
   - Tier-2 prompt-injection attestation verify — **BLOCKING**; **skipped with a WARNING** when no previous `v*` tag exists
   - skill-injection hook tests (`test-semantic`) — **NON-BLOCKING** (WARNING only; these are hook-firing tests, not the prompt-injection scan)
   - skill manifest regeneration (baseline reset to the last-released manifest first)
6. Commits, refreshes the native Codex plugin before push, mirrors to ai-skills, publishes to ClawHub, and syncs shared skill directories

Semver rules applied by `/release`:
- **MAJOR** (1.0.0 → 2.0.0): breaking changes, major reorganization
- **MINOR** (1.0.0 → 1.1.0): new agents, commands, or skills since last release
- **PATCH** (1.0.0 → 1.0.1): bug fixes, doc updates, improvements to existing components

Enforcement:
- Do not touch release versions, `CHANGELOG.md`, or README component counts on regular edits. Commit the actual change and stop.
- If a session-end summary says "bumped to vX.Y.Z" without the user invoking `/release`, that is a regression — back out the bump before handing off.
- Exception: if the user explicitly asks for a version bump outside `/release`, do it. Otherwise `/release` is the sole authority for version state.

## Naming convention

All skills, agents, and commands in the plugin carry an `ia-` prefix. The prefix:

- Prevents collisions with Claude Code built-ins (`/plan`, `/review`) and with sibling plugins (EveryInc's `ce-` family).
- Groups plugin artifacts visibly in shared tool directories (`~/.codex/skills/`, `~/.agents/skills/`).
- Keeps command invocations short and consistent: `/ia-plan`, `/ia-review`, `/ia-brainstorm`, `/ia-work`.

Rules:
- Every directory under `plugins/whetstone/skills/` starts with `ia-`.
- Every agent file under `plugins/whetstone/agents/` starts with `ia-` (flat layout, no category subdirectories).
- Every command file under `plugins/whetstone/commands/` starts with `ia-`.
- The `name:` frontmatter field matches the directory/file stem exactly.
- Trigger regex patterns in `hooks/skill-patterns.sh` do NOT change — they match user speech, not skill names. Only the array keys (`SKILL_PATTERNS[ia-debugging]`) carry the prefix.
- Reference files (`*/references/*.md`) are NOT prefixed — they're content, not invocable components.

## Skill class taxonomy

Every shipped skill declares a `class:` field in frontmatter. Five values, chosen by the dominant lookup need a user has when they reach for the skill:

| Class | What lives here | Examples |
|---|---|---|
| `language` | Stack-specific patterns: a language, framework, or service the skill wraps. | `ia-php-laravel`, `ia-react-frontend`, `ia-postgresql`, `ia-terraform` |
| `discipline` | Engineering practices not tied to one stack: how to do X well in any project. | `ia-debugging`, `ia-code-review`, `ia-writing-tests`, `ia-simplifying-code` |
| `workflow` | Multi-step processes with phases and outputs. | `ia-planning`, `ia-brainstorming`, `ia-md-docs`, `ia-orchestrating-swarms` |
| `meta` | About prompts, agents, design itself. The skill's subject is AI-native work. | `ia-meta-prompting`, `ia-agent-native-architecture`, `ia-frontend-design` |
| `tool` | Niche utilities — narrow, scoped to a single capability. | `ia-git-worktree`, `ia-reflect` |

Picking a class:
- If the skill content reads like a stack reference (install, config, idioms, migrations), it's `language`.
- If the content is "how to do X well" without naming a stack, it's `discipline`.
- If the content is a phased process producing artifacts, it's `workflow`.
- If the subject of the skill is agents, prompts, or skills themselves, it's `meta`.
- Default to `tool` only if none of the above fit and the scope is genuinely narrow.

The validator (`validate-plugin`) requires the field and rejects unknown values. `/write-skill` asks for the class up front when scaffolding a new skill.

## Skill compliance checklist

The master reference for what can/cannot/should/should not be used in skills is https://code.claude.com/docs/en/skills -- consult it when uncertain about frontmatter fields, supported features, or behavioral constraints.

When adding or modifying skills, verify:

### YAML Frontmatter (Required)

- [ ] `name:` present and matches directory name (lowercase-with-hyphens)
- [ ] `description:` describes **what it does and when to use it** (e.g., "Explains code with diagrams. Use when exploring how code works.")
- [ ] `description:` describes *when* to invoke the skill (trigger conditions); never *how* the skill proceeds step-by-step. Restating the body's procedure in the description causes Claude to follow the description and skip the skill content.
- [ ] `description:` sentence 1 names the distinctive mechanism (what a sibling skill would not produce), not a category label ("code review", "optimization loops"). Route neighbors with "Use `<sibling>` for <that job>" rather than restating their scope. Quoted-utterance or slash-name catalogs belong only in descriptions of user-invoked skills.
- [ ] No `disable-model-invocation: true` on a skill that another skill or command invokes through an explicit `Skill()` call; the flag makes that call fail (`cannot be used with Skill tool`). Tighten the description's trigger instead.

**Description-as-shortcut failure mode:** a description that summarizes the procedure gets *followed* instead of the body being *read*. Observed case: a skill with a two-stage flowchart (spec-compliance review, then quality review) described as "code review between tasks" ran one review, not two. A description of the form "does X, then Y, then Z" is a procedure shortcut; keep process in the body.

### Reference Links (Required if references/ exists)

- [ ] All files in `references/` linked as `[filename.md](./references/filename.md)`
- [ ] All files in `assets/` linked as `[filename](./assets/filename)`
- [ ] All files in `scripts/` linked as `[filename](./scripts/filename)`
- [ ] No bare backtick references like `` `references/file.md` `` — use proper markdown links

### Writing Style

- [ ] Imperative/infinitive form (verb-first instructions)
- [ ] No second person ("you should") — use objective language ("To accomplish X, do Y")
- [ ] When a skill must block on a user question, name the harness tool — `AskUserQuestion` in Claude Code (call `ToolSearch` with `select:AskUserQuestion` first if its schema isn't loaded), `request_user_input` in Codex — and fall back to numbered options in chat only when no blocking tool exists. The plugin ships cross-harness (Codex/.agents/.kilocode), so a bare "ask the user" silently degrades to chat off-Claude
- [ ] No bare `/ia-x` slash commands in skill bodies. Only `skills/` ships to Codex/.agents/.kilocode (`.codex-plugin/plugin.json` declares `"skills"` and no commands key), so a slash command printed there resolves to nothing on three of four distribution targets. Reference a sibling component by skill name (`ia-planning`); where a user is genuinely told to invoke something, scope it — "planning (`/ia-plan` in Claude Code)". Descriptive mentions inside a conditional ("when invoked via `/ia-lfg`") are fine
- [ ] No model-specific workarounds. A step that cannot be justified without naming a model, a model version, or one agent's private tool name is an issue to file, not skill content. The plugin ships to four harnesses across model families, so a step written to route around one model's failure is a tax on every other reader. Describe the capability the step needs, not the mechanism one model happens to require
- [ ] No literal `$1`-`$9` or `$ARGUMENTS` in a SKILL.md body. Substitution applies to the skill's markdown content and to bash rules in `allowed-tools` frontmatter; it does **not** apply to `references/*.md`. A Postgres placeholder or shell positional written in the body is rewritten before the model sees it — put such examples in a reference file, or use `?`-style placeholders in the body

### Bundled scripts

A skill referencing its own bundled files picks one of three tiers:

1. **Read-time relative path** — `[init-plan.sh](./scripts/init-plan.sh)`. No variable, no shell. Default choice.
2. **Prose pointer** — "read `scripts/init-plan.sh` from this skill's directory". Use when the reader resolves the path, not a tool.
3. **Executed shell** — a model-filled `SKILL_DIR` variable. Two non-obvious constraints apply:
   - The assignment line needs a **trailing `;`**. Some hosts flatten the newline into a space, and without the separator `$SKILL_DIR` expands before the assignment runs.
   - Claude Code's permission checker evaluates **every subcommand** of a compound command, so wrapping a pinned `bash ".../foo.sh"` call in `if [ -f ... ]; then ...; fi` defeats a narrow `Bash(bash *foo.sh)` allow-rule. A model-filled path is dynamic anyway and will not match a static pin.

Avoid `${CLAUDE_SKILL_DIR}`: it is empty outside Claude Code, and every skill here ships cross-harness.

### Quality Dimensions (SkillsBench arXiv:2602.12670)

- [ ] **Output format** — skill defines what it produces (report template, file path, code pattern)
- [ ] **Success criteria** — how the agent knows the skill completed correctly
- [ ] **Constraints** — what the skill must NOT do, stop conditions, boundaries
- [ ] **Procedural content** — numbered steps with action verbs, not just declarative rules
- [ ] **Optimal length** — SKILL.md body 2K-8K chars ideal. >15K hurts (-2.9pp). Overflow → `references/`

### Quick Validation

```bash
# Check for unlinked references in a skill
grep -E '`(references|assets|scripts)/[^`]+`' skills/*/SKILL.md
# Should return nothing if all refs are properly linked

# Check description format - should describe what + when
grep -E '^description:' skills/*/SKILL.md
```

## Common tasks

Keep component edits separate from release bookkeeping. Defer version changes, metadata/count regeneration, README component tables, mirroring, and publishing to `/release`.

### Adding a new agent

1. Create `plugins/whetstone/agents/ia-new-agent.md` (flat layout)
2. Validate the agent's references and exercise it through the installed Claude Code delegation interface.

### Adding a new command

1. Create `plugins/whetstone/commands/ia-new-command.md`.
2. Validate references and invoke `/ia-new-command` in an installed Claude Code session.

### Adding a new skill

1. Create `plugins/whetstone/skills/ia-skill-name/SKILL.md` with the required frontmatter.
2. Add its trigger pattern to `plugins/whetstone/hooks/skill-patterns.sh`.
3. Add trigger regression fixtures to `distillery/tests/fixtures/triggers/ia-skill-name.jsonl`.
4. Run `python3 distillery/scripts/distiller.py test-triggers --skill ia-skill-name`.
5. Exercise the skill through a matching task in the intended installed harness.

### Adding a new hook

1. Add hook entry to `plugins/whetstone/hooks/hooks.json`
2. Create hook script in `plugins/whetstone/hooks/`
3. Test the hook's emitted protocol and intended caller behavior.

## Skill distillery

The `distillery/` directory generates skills from top-rated skills on skills.sh. Use the `skill-distiller` project-level skill (`.claude/skills/skill-distiller/SKILL.md`) for the full workflow.

```
# Generate a new skill
python3 distillery/scripts/distiller.py search "react"
python3 distillery/scripts/distiller.py fetch --skills '<json>'
# ... analyze, synthesize, validate → distillery/generated-skills/<name>/

# Promote to plugin
cp -r distillery/generated-skills/<name> plugins/whetstone/skills/<name>
# Metadata and distribution run during /release.

# Mirror to ai-skills (read-only public distribution)
bash scripts/mirror-to-ai-skills.sh
```

### SkillOpt optimizer (offline)

`distillery/skillopt/` is a vendored [microsoft/SkillOpt](https://github.com/microsoft/SkillOpt) (MIT, see its `VENDORED.md`) plus a whetstone env that optimizes a process `SKILL.md` by running the target model **agentically** (Claude Code via `claude_code_exec`) against curated fixtures, with a hybrid reward: deterministic `hard` (fixture test red→green) + a per-skill process rubric `soft`. It is the **Tier 3** rung of the skill-optimization ladder (`eval-skills` → `evolve` → SkillOpt) — the higher-fidelity, higher-cost path for process skills whose value is agentic, reached when the single-turn DSPy `evolve` plateaus.

**Validated recipe** (full procedure in [SKILLOPT-RUNBOOK.md](distillery/skillopt/SKILLOPT-RUNBOOK.md)): optimize for the **weaker model that actually runs the skill** (capable models saturate `hard`; the process gap is in the weak model), and **blend `soft` into the gate** via `SKILLOPT_SOFT_WEIGHT` (keep `λ < 1/n_val` to preserve the deterministic floor) — a process skill cannot be optimized by the `hard`-only gate.

**Safety:** the rollout drives a `bypassPermissions` agent with its bash sandbox off, so it can reach the host filesystem. Run it **from a bare terminal, never nested in a Claude Code session**, `git`-checkpoint first, keep fixtures tracked, and OS-sandbox anything beyond your own curated fixtures.

**Offline only: not mirrored, not in the release pipeline; `best_skill.md` promotion stays manual and gated by `test-triggers`.** See `distillery/skillopt/README.md` and the runbook.

## Session harvesting and eval

The distillery mines Claude Code session logs to build skill evaluation and golden datasets and to score skill effectiveness.

```bash
# Harvest per-skill eval datasets from ~/.claude/projects/
# Excludes stale examples (from before skill was last changed) by default
python3 distillery/scripts/distiller.py harvest-sessions [--project <name>] [--skill <name>] [--include-stale]

# Discover new negative signal patterns not yet in _NEGATIVE_SIGNAL_PATTERNS
python3 distillery/scripts/distiller.py discover-signals [--top 30]

# Score a skill via LLM-as-judge. Direct backend (default: claude -p, billed) OR
# in-session sub-agents (no API cost): --emit-tasks (save the manifest) -> dispatch judge sub-agents
# -> --score-from-verdicts @<file> --manifest @<manifest>. Verdicts carry only {index, response};
# signal/session_id/skill_version come from the manifest, never from the judge's self-report.
python3 distillery/scripts/distiller.py dspy-eval <skill> [--max-examples 20] [--backend claude-cli|openrouter] [--emit-tasks | --score-from-verdicts @<file> --manifest @<manifest>]

# Find skills whose trigger regex may be too narrow (sessions that matched a skill's
# keywords but never fired it). Keyword overlap, so rows are candidates for review, not a miss rate.
python3 distillery/scripts/distiller.py analyze-undertriggers [--skill <name>] [--min-examples 5] [--overlap 6] [--include-stale]

# Build golden eval dataset from harvested sessions
python3 distillery/scripts/distiller.py build-golden <skill> [--top 20] [--auto]
# Review candidates.jsonl, set labels to positive/negative/skip, then:
python3 distillery/scripts/distiller.py approve-golden <skill>

# Evolve a skill via DSPy GEPA/MIPROv2 (outputs diff for review, requires: pip install dspy)
python3 distillery/scripts/distiller.py evolve <skill> [--optimizer gepa|mipro|bootstrap] [--iterations 5] [--save]

# Identify skills injected into tasks where they're not needed (misfire detection)
python3 distillery/scripts/distiller.py analyze-misfires [--min-examples 30] [--include-stale]

# Analyze skill injection outcomes by project context (surface anomalies)
python3 distillery/scripts/distiller.py analyze-outcomes [--min-examples 5] [--include-stale]

# Analyze negative-signal sessions to find failure patterns and suggest skill fixes.
# Direct (claude -p, billed) OR sub-agent: --emit-prompt -> dispatch 1 sub-agent -> --format-result --response @<file>
python3 distillery/scripts/distiller.py diagnose-negatives <skill> [--max-examples 10] [--include-stale] [--emit-prompt | --format-result --response @<file>]

# Record or check per-skill resource budget (turn count + tool variety; catches silent skill bloat)
python3 distillery/scripts/distiller.py budget <skill> --record       # baseline current aggregates
python3 distillery/scripts/distiller.py budget <skill>                # check vs baseline (default)
python3 distillery/scripts/distiller.py budget --check-all            # scan every skill with a baseline

# Run regex trigger regression tests (release gate)
python3 distillery/scripts/distiller.py test-triggers [--skill <name>]

# Run skill-injection hook tests (deterministic; drives inject-skills.sh directly, no API cost)
python3 distillery/scripts/distiller.py test-semantic [--max-tests 5]

# Generate/update skill change manifest (tracks when skills and patterns last changed)
python3 scripts/generate-manifest.py
```

These commands are integrated into the release pipeline (`/sync-from-repos` > `/audit-plugin` > `/release` > `/announce`):

- `harvest-sessions` runs in `/sync-from-repos` Phase 1 (background, parallel with inventory)
- `analyze-outcomes` runs in `/sync-from-repos` Phase 6 (surfaces project-context anomalies before audit); `discover-signals` is manual-only and not in the pipeline
- `analyze-misfires`, `analyze-outcomes`, and `diagnose-negatives` run in `/audit-plugin` Phase 2 (trigger coverage checks)
- `test-triggers` and `test-semantic` run in `/audit-plugin` Phase 7 and `/release` pre-commit gates

All commands can also be run standalone for targeted analysis.

Staleness filtering: `harvest-sessions`, `analyze-misfires`, `analyze-outcomes`, and `diagnose-negatives` exclude examples that predate the skill/pattern or ran on a retired runtime model. The manifest at `distillery/.skill-versions.json` tracks content/pattern hashes per skill plus a top-level `model_baseline_prefixes` list (current: opus-4.8 main + haiku-4.5 subagents + sonnet-4.6). Update `MODEL_BASELINE_PREFIXES` in `scripts/generate-manifest.py` when the runtime model family changes, or override per-run with `SKILL_MODEL_BASELINE=prefix1,prefix2`. Use `--include-stale` to override when you need historical analysis.

Every trigger pattern fix should add a regression test case to `distillery/tests/fixtures/triggers/<skill>.jsonl` to prevent regressions.

## Scripts

| Script | Purpose | When to run |
|--------|---------|-------------|
| `scripts/update-metadata.sh` | Count components, update `plugin.json` + `marketplace.json` descriptions; `--check` fails on metadata/version drift (a `/release` gate) | During `/release` |
| `scripts/check-trigger-overlap.py` | Advisory Jaccard report on trigger-regex vocabulary; surfaces skill pairs competing for the same phrases (`[same-tier]` = expected stack family) | During `/audit-plugin`, or after adding/editing skill triggers |
| `scripts/generate-spec.py` | Generate starter `SPEC.md` per skill from SKILL.md + fixture; skips skills that already have one | When adding a new skill, or after `class:` taxonomy refresh |
| `scripts/generate-manifest.py` | Update `distillery/.skill-versions.json` with current skill/pattern hashes | Automatically during release |
| `scripts/mirror-to-ai-skills.sh` | Mirror plugin skills to `~/ai/ai-skills` (read-only distribution) | During `/release`, or when explicitly requested |
| `scripts/generate-skill-hooks.sh` | Generate draft `hooks/skill-patterns.sh` from SKILL.md frontmatter | After adding/removing skills (hand-tune regex after) |
| `scripts/publish-clawhub.sh` | Publish skills to clawhub.ai registry (handles rate limits, skips existing versions) | During release (automatic) or manually |
| `scripts/sync-to-tools.sh` | Symlink skills to shared directories; remove legacy Codex links and configure duplicate-source exclusions | After editing or adding skills |
| `scripts/install-codex-plugin.sh` | Install and verify the native Codex plugin before retiring duplicate direct sources | Initial install and release refresh |
| `scripts/refresh-codex-plugin.sh` | Reinstall local Codex source edits with a temporary, trap-restored cachebuster | During between-release Codex plugin development |
| `scripts/update-plugin.sh` | Update locally installed plugin to latest pushed version | After pushing a new version to GitHub |
| `scripts/post-thread.py` | Post tweet threads to X via Playwright CDP to Edge | After `/announce` drafts are approved |

## Marketplace.json spec

Only include fields from the official Claude Code spec:

- Required: `name`, `owner`, `plugins`
- Optional: `metadata` (with description and version)
- Plugin entries: `name`, `description`, `version`, `author`, `homepage`, `tags`, `source`

Do not add custom fields (`downloads`, `stars`, `rating`, `categories`, etc.).

## Resources

- [Skills Reference](https://code.claude.com/docs/en/skills) -- master reference for skill frontmatter, features, and constraints
- [Plugin Documentation](https://code.claude.com/en/docs/claude-code/plugins)
- [Plugin Marketplace Documentation](https://code.claude.com/en/docs/claude-code/plugin-marketplaces)
- [Plugin Reference](https://code.claude.com/en/docs/claude-code/plugins-reference)

<!-- BEGIN beads-managed (br v6) -->
## Beads ledger (`br`)

This repo is onboarded to the central `br` ledger. A PATH wrapper routes every
`br` call from here into a private store under `~/ai/beads/<slug>/`; this work tree
carries **no** `.beads` artifacts (do not create any). Full protocol lives in
`~/ai/wiki/tools/beads-review-ledger.md`.

**Allowed commands** (the wrapper denies everything else): `create update comments
close reopen list show count stats search where info`, `doctor health`,
`sync --import-only|--status`, `config get|list`. Never pass `--db`,
`--no-auto-flush`, `--no-auto-import`, `--no-db`, `--allow-stale`, or `--prefix`.

**JSON envelopes**: `br list --json` → `{issues, total}`; `br show ID --json` →
a one-element array with comments under `.[0].comments`. Pipe `br` JSON to `jq`
only as `rtk proxy br … | rtk proxy jq …` (raw, unfiltered output).

**Finding schema** (review-cycle records):
- Native status `open`/`closed` only — `in_progress` is banned (it silently
  disappears from `--status open`). Priority is severity: P0 critical, P1
  important, P2 minor.
- Exactly one `type:{security|correctness|memory|perf|build|test|style}` label and
  one `cycle:<id>` label. Open findings carry exactly one
  `state:{proposed|disputed|fixed|needs-human}`; closed findings carry no `state:*`
  and a `close_reason` of `fixed|false-positive|wont-fix|duplicate`.
- Description first line is `file: <path>:<line>`, repo-relative.
- Attribution: `br create --actor <id>`, `br comments add --author <id>`.
- Closing is two steps (0.2.19 refuses a terminal status in `update`): first
  `br update ID` clearing `state:*` and the assignee, then `br close ID --reason <r>`.
- Never `--set-labels` (it erases other labels); use `--add-label`/`--remove-label`.

**Human gate** — create as `state:needs-human` and get pre-change approval for: P0,
`type:security`, `type:memory`, destructive operations, schema/data migrations, or
public API changes.
<!-- END beads-managed (br v6) -->
