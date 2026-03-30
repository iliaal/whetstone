# Compound Engineering Plugin

Claude Code plugin for PHP/React/Python/JavaScript/TypeScript workflows. Includes the plugin (agents, commands, skills, hooks), a skill distillery, and a CLI for cross-tool conversion.

When you see a `<session-commands>` tag in hook context, briefly list those commands to the user at the start of your first response.

## Repository structure

```
compound-engineering-plugin/
├── .claude-plugin/
│   └── marketplace.json          # Marketplace catalog
├── distillery/                   # Skill distillery (generate skills from skills.sh)
│   ├── scripts/
│   │   ├── distiller.py          # Search, fetch, validate, test, A/B eval
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
    └── compound-engineering/     # The plugin
        ├── .claude-plugin/
        │   └── plugin.json      # Plugin metadata
        ├── agents/              # 23 agents (review, research, design, workflow)
        │   ├── review/          # Code review agents
        │   ├── research/        # Research and analysis agents
        │   ├── design/          # Design and UI agents
        │   └── workflow/        # Workflow automation agents
        ├── commands/            # 18 slash commands
        │   ├── workflows/       # Core workflow commands (workflows:plan, etc.)
        │   └── *.md             # Utility commands
        ├── skills/              # 30 skills (all native)
        │   └── <skill-name>/
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

## Versioning

Every change MUST include:

1. **Version bump** in `plugins/compound-engineering/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`
2. **CHANGELOG.md** entry using Keep a Changelog format
3. **README.md** — verify/update component counts and tables
4. **`bash scripts/update-metadata.sh`** — updates descriptions and counts

Semver rules:
- **MAJOR** (1.0.0 → 2.0.0): Breaking changes, major reorganization
- **MINOR** (1.0.0 → 1.1.0): New agents, commands, or skills
- **PATCH** (1.0.0 → 1.0.1): Bug fixes, doc updates, minor improvements

Pre-commit checklist:

- [ ] Version bumped in both JSON files
- [ ] CHANGELOG.md updated
- [ ] README.md component counts verified
- [ ] README.md tables accurate (agents, commands, skills)
- [ ] `bash scripts/update-metadata.sh` run
- [ ] `jq . .claude-plugin/marketplace.json && jq . plugins/compound-engineering/.claude-plugin/plugin.json`

## Command naming convention

Workflow commands use `workflows:` prefix to avoid collisions with built-in commands:
- `/workflows:brainstorm` — explore requirements and approaches before planning
- `/workflows:plan` — create implementation plans
- `/workflows:review` — run comprehensive code reviews
- `/workflows:work` — execute work items systematically
- `/workflows:compound` — document solved problems

Why `workflows:`? Claude Code has built-in `/plan` and `/review`. Using `name: workflows:plan` in frontmatter creates a unique command with no collision.

## Skill compliance checklist

When adding or modifying skills, verify:

### YAML Frontmatter (Required)

- [ ] `name:` present and matches directory name (lowercase-with-hyphens)
- [ ] `description:` describes **what it does and when to use it** (e.g., "Explains code with diagrams. Use when exploring how code works.")

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

1. Create `plugins/compound-engineering/agents/<category>/new-agent.md`
2. Run `bash scripts/update-metadata.sh`
3. Update README tables
4. Test with `claude agent new-agent "test"`

### Adding a new command

1. Create `plugins/compound-engineering/commands/new-command.md`
2. Run `bash scripts/update-metadata.sh`
3. Update README tables
4. Test with `claude /new-command`

### Adding a new skill

1. Create `plugins/compound-engineering/skills/skill-name/SKILL.md`
2. Run `bash scripts/update-metadata.sh`
3. Update README tables and `hooks/skill-patterns.sh` (add trigger pattern)
4. Test with `claude skill skill-name`

### Adding a new hook

1. Add hook entry to `plugins/compound-engineering/hooks/hooks.json`
2. Create hook script in `plugins/compound-engineering/hooks/`
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
cp -r distillery/generated-skills/<name> plugins/compound-engineering/skills/<name>
bash scripts/update-metadata.sh

# Mirror to ai-skills (read-only public distribution)
bash scripts/mirror-to-ai-skills.sh
```

## Session harvesting and eval

The distillery includes tools for mining Claude Code session logs to build skill evaluation datasets, score skill effectiveness, and build golden eval datasets.

```bash
# Harvest per-skill eval datasets from ~/.claude/projects/
python3 distillery/scripts/distiller.py harvest-sessions [--project <name>] [--skill <name>]

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
python3 distillery/scripts/distiller.py analyze-misfires [--min-examples 30]

# Analyze negative-signal sessions to find failure patterns and suggest skill fixes
python3 distillery/scripts/distiller.py diagnose-negatives <skill> [--max-examples 10]
```

Run `discover-signals` periodically (before releases or after heavy usage periods) to surface new user dissatisfaction patterns from session history. Review the candidates, promote confirmed patterns to `_NEGATIVE_SIGNAL_PATTERNS` in `distiller.py`, then re-harvest to update eval data.

The practical skill improvement loop is: `analyze-misfires` to tighten injection patterns, then `diagnose-negatives` per skill to read real failures and get concrete fix suggestions. This is more effective than DSPy evolution for mature skills because it addresses the actual problems (wrong injection, missing guidance) rather than trying to auto-rewrite text.

## Scripts

| Script | Purpose | When to run |
|--------|---------|-------------|
| `scripts/update-metadata.sh` | Count components, update `plugin.json` + `marketplace.json` descriptions | After any component change |
| `scripts/mirror-to-ai-skills.sh` | Mirror plugin skills to `~/ai/ai-skills` (read-only distribution) | After editing or adding skills |
| `scripts/generate-skill-hooks.sh` | Generate draft `hooks/skill-patterns.sh` from SKILL.md frontmatter | After adding/removing skills (hand-tune regex after) |
| `scripts/sync-to-tools.sh` | Symlink plugin skills to `~/.agents/skills`, `~/.codex/skills`, `~/.kilocode/skills` | After editing or adding skills |
| `scripts/update-plugin.sh` | Update locally installed plugin to latest pushed version | After pushing a new version to GitHub |

## Marketplace.json spec

Only include fields from the official Claude Code spec:

- Required: `name`, `owner`, `plugins`
- Optional: `metadata` (with description and version)
- Plugin entries: `name`, `description`, `version`, `author`, `homepage`, `tags`, `source`

Do not add custom fields (`downloads`, `stars`, `rating`, `categories`, etc.).

## Resources

- [Claude Code Plugin Documentation](https://code.claude.com/en/docs/claude-code/plugins)
- [Plugin Marketplace Documentation](https://code.claude.com/en/docs/claude-code/plugin-marketplaces)
- [Plugin Reference](https://code.claude.com/en/docs/claude-code/plugins-reference)
