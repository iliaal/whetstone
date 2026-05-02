# Whetstone

AI-powered development tools that get smarter with every use. Make each unit of engineering work easier than the last.

## Components

| Component | Count |
|-----------|-------|
| Agents | 21 |
| Commands | 22 |
| Skills | 29 |
| Hooks | 1 |
| MCP Servers | 1 |

## Agents

All agent files live flat under `agents/`. Categories below are editorial — grouped by purpose for easier discovery, not by filesystem layout.

### Review (9)

| Agent | Description |
|-------|-------------|
| [`ia-accessibility-tester`](agents/ia-accessibility-tester.md) | WCAG 2.1 accessibility audit: keyboard, screen reader, contrast, ARIA, forms |
| [`ia-architecture-strategist`](agents/ia-architecture-strategist.md) | Architecture, design patterns, naming conventions, and structural integrity |
| [`ia-cloud-architect`](agents/ia-cloud-architect.md) | Cloud infrastructure review, cost optimization, DR, migration strategies |
| [`ia-code-simplicity-reviewer`](agents/ia-code-simplicity-reviewer.md) | Final pass for simplicity and minimalism |
| [`ia-database-guardian`](agents/ia-database-guardian.md) | Database schema, constraints, and migration code validation |
| [`ia-kieran-reviewer`](agents/ia-kieran-reviewer.md) | Python and TypeScript code review with strict conventions |
| [`ia-performance-oracle`](agents/ia-performance-oracle.md) | Performance analysis and optimization |
| [`ia-security-sentinel`](agents/ia-security-sentinel.md) | Security audits and vulnerability assessments |
| [`ia-spec-flow-analyzer`](agents/ia-spec-flow-analyzer.md) | Analyze user flows and identify gaps in specifications |

### Research (4)

| Agent | Description |
|-------|-------------|
| [`ia-best-practices-researcher`](agents/ia-best-practices-researcher.md) | Best practices, framework docs, and implementation patterns |
| [`ia-git-history-analyzer`](agents/ia-git-history-analyzer.md) | Analyze git history and code evolution |
| [`ia-learnings-researcher`](agents/ia-learnings-researcher.md) | Search institutional learnings for relevant past solutions |
| [`ia-repo-research-analyst`](agents/ia-repo-research-analyst.md) | Research repository structure and conventions |

### Design (2)

| Agent | Description |
|-------|-------------|
| [`ia-design-iterator`](agents/ia-design-iterator.md) | Iteratively refine UI through systematic design iterations |
| [`ia-figma-design-sync`](agents/ia-figma-design-sync.md) | Compare UI against Figma designs, report discrepancies, and optionally implement fixes |

### Workflow (4)

| Agent | Description |
|-------|-------------|
| [`ia-bug-reproduction-validator`](agents/ia-bug-reproduction-validator.md) | Systematically reproduce and validate bug reports |
| [`ia-deployment-verification-agent`](agents/ia-deployment-verification-agent.md) | Create Go/No-Go deployment checklists for risky data changes |
| [`ia-infrastructure-engineer`](agents/ia-infrastructure-engineer.md) | CI/CD pipelines, Docker containerization, observability, and incident management |
| [`ia-pr-comment-resolver`](agents/ia-pr-comment-resolver.md) | Address PR comments and implement fixes |

## Commands

### Workflow Commands

Core workflow commands use `workflows:` prefix to avoid collisions with built-in commands:

| Command | Description |
|---------|-------------|
| `/ia-brainstorm` | Explore requirements and approaches before planning |
| `/ia-plan` | Create implementation plans |
| `/ia-review` | Run comprehensive code reviews |
| `/ia-work` | Execute work items systematically |
| `/ia-compound` | Document solved problems to compound team knowledge |
| `/ia-document-release` | Post-ship documentation sync across README/ARCHITECTURE/CONTRIBUTING/CHANGELOG |

### Utility Commands

| Command | Description |
|---------|-------------|
| `/ia-lfg` | Full autonomous engineering workflow (plan, build, review, ship). Use `--swarm` for parallel execution |
| `/ia-agent-native-audit` | Run agent-native architecture review with scored principles |
| `/ia-deepen-plan` | Enhance plans with parallel research agents for each section |
| `/ia-changelog` | Create engaging changelogs for recent merges |
| `/ia-report-bug` | Report a bug in the plugin |
| `/ia-reproduce-bug` | Reproduce bugs using logs and console |
| `/ia-resolve-todo-parallel` | Resolve todos from /todos/ directory in parallel |
| `/ia-setup` | Configure which review agents run for your project (auto-detects stack) |
| `/ia-triage` | Triage and prioritize issues |
| `/ia-test-browser` | Run browser tests on PR-affected pages |
| `/ia-feature-video` | Record video walkthroughs and add to PR description |
| `/ia-adr` | Create Architecture Decision Records with format selection and lifecycle management |
| `/ia-compound-refresh` | Review docs/solutions/ for stale learnings -- keep, update, replace, or archive |
| `/ia-ideate` | Generate ranked improvement ideas by scanning the codebase |
| `/resolve-pr-parallel` | Batch-resolve PR review comments via parallel subagents |
| `/ia-verify` | Pre-PR verification pipeline (build, types, lint, tests, security) |

## Skills

### Architecture & Design

| Skill | Description |
|-------|-------------|
| [`ia-agent-native-architecture`](skills/ia-agent-native-architecture/SKILL.md) | Build AI agents using prompt-native architecture |
| [`ia-frontend-design`](skills/ia-frontend-design/SKILL.md) | Create production-grade frontend interfaces |
| [`ia-react-frontend`](skills/ia-react-frontend/SKILL.md) | React, TypeScript, Next.js patterns, Vitest/RTL testing |
| [`ia-tailwind-css`](skills/ia-tailwind-css/SKILL.md) | Tailwind CSS v4 patterns, component variants, v3 migration |
| [`ia-simplifying-code`](skills/ia-simplifying-code/SKILL.md) | Simplify, polish, and declutter code |

### Language & Framework

| Skill | Description |
|-------|-------------|
| [`ia-nodejs-backend`](skills/ia-nodejs-backend/SKILL.md) | Node.js backend patterns: Express/Fastify, TypeScript, validation |
| [`ia-php-laravel`](skills/ia-php-laravel/SKILL.md) | Modern PHP 8.4 and Laravel patterns, PHPUnit testing |
| [`ia-python-services`](skills/ia-python-services/SKILL.md) | Python CLI tools, async parallelism, FastAPI services |
| [`ia-terraform`](skills/ia-terraform/SKILL.md) | Terraform/OpenTofu configuration, modules, testing, state |
| [`ia-postgresql`](skills/ia-postgresql/SKILL.md) | PostgreSQL schema design, query optimization, indexing |
| [`ia-pinescript`](skills/ia-pinescript/SKILL.md) | Pine Script v6 patterns for TradingView |
| [`ia-linux-bash-scripting`](skills/ia-linux-bash-scripting/SKILL.md) | Defensive Bash scripting for Linux |

### Testing

| Skill | Description |
|-------|-------------|
| [`ia-writing-tests`](skills/ia-writing-tests/SKILL.md) | Generic test discipline: quality, anti-patterns, rationalization resistance |

### Code Quality & Review

| Skill | Description |
|-------|-------------|
| [`ia-code-review`](skills/ia-code-review/SKILL.md) | Two-stage code reviews with severity-ranked findings |
| [`ia-receiving-code-review`](skills/ia-receiving-code-review/SKILL.md) | Process review feedback critically: verify, push back, no blind agreement |
| [`ia-debugging`](skills/ia-debugging/SKILL.md) | Systematic root-cause debugging with anti-rationalization patterns |
| [`ia-verification-before-completion`](skills/ia-verification-before-completion/SKILL.md) | Fresh verification evidence before any completion claim |
| [`ia-planning`](skills/ia-planning/SKILL.md) | Software implementation planning with file persistence |

### Content & Workflow

| Skill | Description |
|-------|-------------|
| [`ia-brainstorming`](skills/ia-brainstorming/SKILL.md) | Explore requirements and approaches through dialogue |
| [`ia-compound-docs`](skills/ia-compound-docs/SKILL.md) | Capture solved problems as categorized documentation |
| [`ia-document-review`](skills/ia-document-review/SKILL.md) | Improve documents through structured self-review |
| [`ia-file-todos`](skills/ia-file-todos/SKILL.md) | File-based todo tracking system |
| [`ia-git-worktree`](skills/ia-git-worktree/SKILL.md) | Manage Git worktrees for parallel development |
| [`ia-md-docs`](skills/ia-md-docs/SKILL.md) | Manages project documentation: AGENTS.md, README.md |
| [`ia-writing`](skills/ia-writing/SKILL.md) | Prose editing, rewriting, and humanizing text |

### AI & Prompting

| Skill | Description |
|-------|-------------|
| [`ia-meta-prompting`](skills/ia-meta-prompting/SKILL.md) | Enhanced reasoning patterns via slash commands |
| [`ia-refine-prompt`](skills/ia-refine-prompt/SKILL.md) | Transform vague prompts into precise instructions |
| [`ia-reflect`](skills/ia-reflect/SKILL.md) | Session retrospective and skill audit |

### Multi-Agent Orchestration

| Skill | Description |
|-------|-------------|
| [`ia-orchestrating-swarms`](skills/ia-orchestrating-swarms/SKILL.md) | Comprehensive guide to multi-agent swarm orchestration |


## Hooks

| Hook | Event | Description |
|------|-------|-------------|
| `inject-skills` | PreToolUse (Task) | Injects relevant skill instructions into subagent prompts |

When the main agent spawns a subagent via the Task tool, this hook analyzes the subagent's prompt and identifies matching skills based on trigger keywords. It prepends "Read these SKILL.md files" instructions to the prompt so subagents follow the same methodology as the main agent.

Skills are matched using a 3-tier priority system:
1. **Methodology** (planning, debugging, code-review, etc.) -- process skills, matched first
2. **Domain** (php-laravel, react-frontend, terraform, etc.) -- language/framework skills
3. **Supporting** (writing, md-docs, reflect, etc.) -- workflow skills

Up to 5 matching skills are injected per subagent call, prioritized by tier. Subagent types without file read access (e.g., Bash) are skipped.

## MCP Servers

| Server | Description |
|--------|-------------|
| `docfork` | Framework and library documentation lookup via Docfork |

### Docfork

**Tools provided:**
- `search_docs` - Search documentation for a framework/library
- `fetch_doc` - Fetch full markdown content from a documentation URL

9,000+ libraries with daily updates. Free tier: 1,000 requests/month.

MCP servers start automatically when the plugin is enabled.

## Installation

```bash
claude /plugin install whetstone
```

## Known Issues

### MCP Server Setup

**Issue:** The bundled Docfork MCP server may not load automatically when the plugin is installed.

**Setup:** Add to your project's `.claude/settings.json` (or `~/.claude/settings.json` for all projects):

```json
{
  "mcpServers": {
    "docfork": {
      "type": "http",
      "url": "https://mcp.docfork.com/mcp"
    }
  }
}
```

No API key required. Free tier includes 1,000 requests/month.

## Version History

See [CHANGELOG.md](../../CHANGELOG.md) for detailed version history.

## License

MIT
