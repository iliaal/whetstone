# Compounding Engineering Plugin Development

## Versioning Requirements

**IMPORTANT**: Every change to this plugin MUST include:

1. **`.claude-plugin/plugin.json`** - Bump version using semver
2. **`../../.claude-plugin/marketplace.json`** - Bump version to match
3. **`../../CHANGELOG.md`** - Document changes using Keep a Changelog format
4. **`README.md`** - Verify/update component counts and tables

### Version Bumping Rules

- **MAJOR** (1.0.0 → 2.0.0): Breaking changes, major reorganization
- **MINOR** (1.0.0 → 1.1.0): New agents, commands, or skills
- **PATCH** (1.0.0 → 1.0.1): Bug fixes, doc updates, minor improvements

### Pre-Commit Checklist

Before committing ANY changes:

- [ ] Version bumped in `.claude-plugin/plugin.json` and `../../.claude-plugin/marketplace.json`
- [ ] `../../CHANGELOG.md` updated with changes
- [ ] README.md component counts verified
- [ ] README.md tables accurate (agents, commands, skills)
- [ ] `bash ../../scripts/update-metadata.sh` run (updates descriptions and counts)

### Directory Structure

```
agents/
├── review/     # Code review agents
├── research/   # Research and analysis agents
├── design/     # Design and UI agents
└── workflow/   # Workflow automation agents

commands/
├── workflows/  # Core workflow commands (workflows:plan, workflows:review, etc.)
└── *.md        # Utility commands

skills/
└── <skill-name>/
    ├── SKILL.md        # Skill content
    ├── references/     # Optional supplementary docs
    └── scripts/        # Optional bundled scripts
```

## Command Naming Convention

**Workflow commands** use `workflows:` prefix to avoid collisions with built-in commands:
- `/workflows:brainstorm` - Explore requirements and approaches before planning
- `/workflows:plan` - Create implementation plans
- `/workflows:review` - Run comprehensive code reviews
- `/workflows:work` - Execute work items systematically
- `/workflows:compound` - Document solved problems

**Why `workflows:`?** Claude Code has built-in `/plan` and `/review` commands. Using `name: workflows:plan` in frontmatter creates a unique `/workflows:plan` command with no collision.

## Skill Compliance Checklist

When adding or modifying skills, verify compliance:

### YAML Frontmatter (Required)

- [ ] `name:` present and matches directory name (lowercase-with-hyphens)
- [ ] `description:` present and describes **what it does and when to use it** (per official spec: "Explains code with diagrams. Use when exploring how code works.")

### Reference Links (Required if references/ exists)

- [ ] All files in `references/` are linked as `[filename.md](./references/filename.md)`
- [ ] All files in `assets/` are linked as `[filename](./assets/filename)`
- [ ] All files in `scripts/` are linked as `[filename](./scripts/filename)`
- [ ] No bare backtick references like `` `references/file.md` `` - use proper markdown links

### Writing Style

- [ ] Use imperative/infinitive form (verb-first instructions)
- [ ] Avoid second person ("you should") - use objective language ("To accomplish X, do Y")

### Quality Dimensions (SkillsBench arXiv:2602.12670)

- [ ] **Output format** — skill defines what it produces (report template, file path, code pattern)
- [ ] **Success criteria** — how the agent knows the skill completed correctly
- [ ] **Constraints** — what the skill must NOT do, stop conditions, boundaries
- [ ] **Procedural content** — numbered steps with action verbs, not just declarative rules
- [ ] **Optimal length** — SKILL.md body 2K-8K chars ideal. >15K hurts (-2.9pp). Overflow → `references/`

### Quick Validation Command

```bash
# Check for unlinked references in a skill
grep -E '`(references|assets|scripts)/[^`]+`' skills/*/SKILL.md
# Should return nothing if all refs are properly linked

# Check description format - should describe what + when
grep -E '^description:' skills/*/SKILL.md
```

