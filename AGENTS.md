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
│   ├── sync-to-tools.sh          # Symlink skills to .agents, .codex, .kilocode
│   └── update-plugin.sh          # Update locally installed plugin to latest version
├── CHANGELOG.md                 # Version history
└── plugins/
    └── whetstone/     # The plugin
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
- `model: inherit` removed from agents — only declare when overriding (e.g., `model: haiku`).
- Agents reference skills (one-directional); skills stay generic and portable.
- **Read before claiming "new"**: Before presenting sync/improvement findings, read the target skill to verify the pattern isn't already covered. Saves round-trips.
- **Present changes one at a time** for review decisions. Batch presentation only when explicitly asked.
- **No off-stack content**: Skip or replace code examples, references, and patterns for languages/frameworks the team doesn't use (Ruby/Rails, Java, Swift, etc.). Use PHP, Python, or TypeScript equivalents. Generic SQL or framework-agnostic examples are fine when no specific stack fits.
- **No personal-machine paths in plugin files.** The plugin is published externally (mirrored to ai-skills, shipped to ClawHub, synced to `.agents`/`.codex`/`.kilocode`). Anything under `plugins/whetstone/` must be self-contained and runnable by a stranger — no references to `~/ai/wiki/`, `~/ai/repos/`, `/home/ilia/`, private Linear/Slack/Grafana URLs, or any other path specific to one machine or org. If a pattern's deep reference lives in `~/ai/wiki/`, embed enough actionable content inline that the skill works without the wiki; do not leave pointer lines like "see the wiki at ..." in published files. Use `grep -rn '~/ai/\|/home/' plugins/` before shipping to catch stragglers.

## Versioning

**Version bumps, CHANGELOG entries, and README count updates happen during `/release`, not per-change.** Editing a skill, agent, or command does not trigger any version ceremony. Make the change, commit it with a descriptive message, move on. Let work accumulate across multiple commits until a release is cut.

Why this rule exists: per-change ceremony fragmented CHANGELOG.md into dozens of micro-entries and made "what actually shipped in v2.55" hard to reconstruct. Consolidating the bump into `/release` produces one clean summary per ship and makes individual edits cheap.

When `/release` runs, it:

1. Bumps the version in `plugins/whetstone/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`
2. Appends a CHANGELOG.md entry summarizing the commits since the last release
3. Updates README.md component counts and tables
4. Runs `bash scripts/update-metadata.sh` to sync descriptions and counts
5. Validates JSON and runs pre-commit gates (trigger tests, semantic tests)
6. Commits, pushes, mirrors to ai-skills, publishes to ClawHub, syncs to other tools

Semver rules applied by `/release`:
- **MAJOR** (1.0.0 → 2.0.0): breaking changes, major reorganization
- **MINOR** (1.0.0 → 1.1.0): new agents, commands, or skills since last release
- **PATCH** (1.0.0 → 1.0.1): bug fixes, doc updates, improvements to existing components

Enforcement:
- Do not touch `plugin.json`, `marketplace.json`, `CHANGELOG.md`, or README component counts on regular edits. Commit the actual change and stop.
- If a session-end summary says "bumped to vX.Y.Z" without the user invoking `/release`, that is a regression — back out the bump before handing off.
- Exception: if the user explicitly asks for a version bump outside `/release`, do it. Otherwise `/release` is the sole authority for version state.

## Naming convention

All skills, agents, and commands in the plugin carry an `ia-` prefix (introduced in v4.0.0). The prefix:

- Prevents collisions with Claude Code built-ins (`/plan`, `/review`) and with sibling plugins (EveryInc's `ce-` family).
- Groups plugin artifacts visibly in shared tool directories (`~/.codex/skills/`, `~/.agents/skills/`).
- Keeps command invocations short and consistent: `/ia-plan`, `/ia-review`, `/ia-brainstorm`, `/ia-work`, `/ia-compound`.

The old `workflows:` command namespace was dropped as part of the rename — previous `/workflows:plan` is now `/ia-plan`. See CHANGELOG 4.0.0 migration note.

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
| `language` | Stack-specific patterns: a language, framework, or service the skill wraps. | `ia-php-laravel`, `ia-react-frontend`, `ia-postgresql`, `ia-tailwind-css` |
| `discipline` | Engineering practices not tied to one stack: how to do X well in any project. | `ia-debugging`, `ia-code-review`, `ia-writing-tests`, `ia-simplifying-code` |
| `workflow` | Multi-step processes with phases and outputs. | `ia-planning`, `ia-brainstorming`, `ia-md-docs`, `ia-orchestrating-swarms` |
| `meta` | About prompts, agents, design itself. The skill's subject is AI-native work. | `ia-meta-prompting`, `ia-refine-prompt`, `ia-agent-native-architecture`, `ia-frontend-design` |
| `tool` | Niche utilities — narrow, scoped to a single capability. | `ia-git-worktree`, `ia-file-todos`, `ia-reflect` |

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

**Description-as-shortcut failure mode (documented evidence):** a skill whose description summarizes the procedure will be *followed* instead of *read*. Observed case from external test runs: a skill with a two-stage flowchart (spec-compliance review, then quality review) had its description paraphrased as "code review between tasks." Claude ran ONE review, not TWO, because the description compressed the workflow. The fix is always the same: description = trigger conditions only. Process lives in the body. If you find yourself writing "this skill does X, then Y, then Z" in the description, you are writing a procedure shortcut and the body will be skipped.

### Reference Links (Required if references/ exists)

- [ ] All files in `references/` linked as `[filename.md](./references/filename.md)`
- [ ] All files in `assets/` linked as `[filename](./assets/filename)`
- [ ] All files in `scripts/` linked as `[filename](./scripts/filename)`
- [ ] No bare backtick references like `` `references/file.md` `` — use proper markdown links

### Writing Style

- [ ] Imperative/infinitive form (verb-first instructions)
- [ ] No second person ("you should") — use objective language ("To accomplish X, do Y")

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

### Adding a new agent

1. Create `plugins/whetstone/agents/ia-new-agent.md` (flat layout)
2. Run `bash scripts/update-metadata.sh`
3. Update README tables
4. Test with `claude agent new-agent "test"`

### Adding a new command

1. Create `plugins/whetstone/commands/new-command.md`
2. Run `bash scripts/update-metadata.sh`
3. Update README tables
4. Test with `claude /new-command`

### Adding a new skill

1. Create `plugins/whetstone/skills/skill-name/SKILL.md`
2. Run `bash scripts/update-metadata.sh`
3. Update README tables and `hooks/skill-patterns.sh` (add trigger pattern)
4. Add trigger regression fixtures to `distillery/tests/fixtures/triggers/skill-name.jsonl`
5. Run `python3 distillery/scripts/distiller.py test-triggers --skill skill-name` to verify
6. Test with `claude skill skill-name`

### Adding a new hook

1. Add hook entry to `plugins/whetstone/hooks/hooks.json`
2. Create hook script in `plugins/whetstone/hooks/`
3. Run `bash scripts/update-metadata.sh`
4. Update README tables

## Skill distillery

The `distillery/` directory generates skills from top-rated skills on skills.sh. Use the `skill-distiller` project-level skill (`.claude/skills/skill-distiller/SKILL.md`) for the full workflow.

```
# Generate a new skill
python3 distillery/scripts/distiller.py search "react"
python3 distillery/scripts/distiller.py fetch --skills '<json>'
# ... analyze, synthesize, validate → distillery/generated-skills/<name>/

# Promote to plugin
cp -r distillery/generated-skills/<name> plugins/whetstone/skills/<name>
bash scripts/update-metadata.sh

# Mirror to ai-skills (read-only public distribution)
bash scripts/mirror-to-ai-skills.sh
```

### SkillOpt optimizer (offline)

`distillery/skillopt/` is a vendored [microsoft/SkillOpt](https://github.com/microsoft/SkillOpt) (MIT, see its `VENDORED.md`) plus a whetstone env that optimizes a process `SKILL.md` by running the target model **agentically** (Claude Code via `claude_code_exec`) against curated fixtures, with a hybrid reward: deterministic `hard` (fixture test red→green) + a per-skill process rubric `soft`. It is the **Tier 3** rung of the skill-optimization ladder (`eval-skills` → `evolve` → SkillOpt) — the higher-fidelity, higher-cost path for process skills whose value is agentic, reached when the single-turn DSPy `evolve` plateaus.

**Validated recipe** (full procedure in [SKILLOPT-RUNBOOK.md](distillery/skillopt/SKILLOPT-RUNBOOK.md)): optimize for the **weaker model that actually runs the skill** (capable models saturate `hard`; the process gap is in the weak model), and **blend `soft` into the gate** via `SKILLOPT_SOFT_WEIGHT` (keep `λ < 1/n_val` to preserve the deterministic floor) — a process skill cannot be optimized by the `hard`-only gate.

**Safety:** the rollout drives a `bypassPermissions` agent with its bash sandbox off, so it can reach the host filesystem. Run it **from a bare terminal, never nested in a Claude Code session**, `git`-checkpoint first, keep fixtures tracked, and OS-sandbox anything beyond your own curated fixtures.

**Offline only: not mirrored, not in the release pipeline; `best_skill.md` promotion stays manual and gated by `test-triggers`.** See `distillery/skillopt/README.md` and the runbook.

## Session harvesting and eval

The distillery includes tools for mining Claude Code session logs to build skill evaluation datasets, score skill effectiveness, and build golden eval datasets.

```bash
# Harvest per-skill eval datasets from ~/.claude/projects/
# Excludes stale examples (from before skill was last changed) by default
python3 distillery/scripts/distiller.py harvest-sessions [--project <name>] [--skill <name>] [--include-stale]

# Discover new negative signal patterns not yet in _NEGATIVE_SIGNAL_PATTERNS
python3 distillery/scripts/distiller.py discover-signals [--top 30]

# Score a skill via LLM-as-judge (default: Sonnet 4.6 via claude -p)
python3 distillery/scripts/distiller.py dspy-eval <skill> [--max-examples 20] [--backend claude-cli|openrouter]

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

# Analyze negative-signal sessions to find failure patterns and suggest skill fixes
python3 distillery/scripts/distiller.py diagnose-negatives <skill> [--max-examples 10] [--include-stale]

# Record or check per-skill resource budget (turn count + tool variety; catches silent skill bloat)
python3 distillery/scripts/distiller.py budget <skill> --record       # baseline current aggregates
python3 distillery/scripts/distiller.py budget <skill>                # check vs baseline (default)
python3 distillery/scripts/distiller.py budget --check-all            # scan every skill with a baseline

# Run regex trigger regression tests (release gate)
python3 distillery/scripts/distiller.py test-triggers [--skill <name>]

# Run semantic injection tests via claude CLI (costs tokens)
python3 distillery/scripts/distiller.py test-semantic [--max-tests 5]

# Generate/update skill change manifest (tracks when skills and patterns last changed)
python3 scripts/generate-manifest.py
```

These commands are integrated into the release pipeline (`/sync-from-repos` > `/audit-plugin` > `/release` > `/announce`):

- `harvest-sessions` runs in `/sync-from-repos` Phase 1 (background, parallel with inventory)
- `discover-signals` and `analyze-outcomes` run in `/sync-from-repos` Phase 6 (surfaces new patterns and project-context anomalies before audit)
- `analyze-misfires`, `analyze-outcomes`, and `diagnose-negatives` run in `/audit-plugin` Phase 2 (trigger coverage checks)
- `test-triggers` and `test-semantic` run in `/audit-plugin` Phase 7 and `/release` pre-commit gates

All commands can also be run standalone for targeted analysis.

Staleness filtering: `harvest-sessions`, `analyze-misfires`, `analyze-outcomes`, and `diagnose-negatives` exclude examples that predate the skill/pattern or ran on a retired runtime model. The manifest at `distillery/.skill-versions.json` tracks content/pattern hashes per skill plus a top-level `model_baseline_prefixes` list (current: opus-4.7 main + haiku-4.5 subagents + sonnet-4.6). Update `MODEL_BASELINE_PREFIXES` in `scripts/generate-manifest.py` when the runtime model family changes, or override per-run with `SKILL_MODEL_BASELINE=prefix1,prefix2`. Use `--include-stale` to override when you need historical analysis.

Every trigger pattern fix should add a regression test case to `distillery/tests/fixtures/triggers/<skill>.jsonl` to prevent regressions.

## Scripts

| Script | Purpose | When to run |
|--------|---------|-------------|
| `scripts/update-metadata.sh` | Count components, update `plugin.json` + `marketplace.json` descriptions | After any component change |
| `scripts/generate-spec.py` | Generate starter `SPEC.md` per skill from SKILL.md + fixture; skips skills that already have one | When adding a new skill, or after `class:` taxonomy refresh |
| `scripts/generate-manifest.py` | Update `distillery/.skill-versions.json` with current skill/pattern hashes | Automatically during release |
| `scripts/mirror-to-ai-skills.sh` | Mirror plugin skills to `~/ai/ai-skills` (read-only distribution) | After editing or adding skills |
| `scripts/generate-skill-hooks.sh` | Generate draft `hooks/skill-patterns.sh` from SKILL.md frontmatter | After adding/removing skills (hand-tune regex after) |
| `scripts/publish-clawhub.sh` | Publish skills to clawhub.ai registry (handles rate limits, skips existing versions) | During release (automatic) or manually |
| `scripts/sync-to-tools.sh` | Symlink plugin skills to `~/.agents/skills`, `~/.codex/skills`, `~/.kilocode/skills` | After editing or adding skills |
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
