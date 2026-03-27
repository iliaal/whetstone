# Compounding Engineering Plugin

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

Agents are organized into categories for easier discovery.

### Review (10)

| Agent | Description |
|-------|-------------|
| [`accessibility-tester`](agents/review/accessibility-tester.md) | WCAG 2.1 accessibility audit: keyboard, screen reader, contrast, ARIA, forms |
| [`agent-native-reviewer`](agents/review/agent-native-reviewer.md) | Verify features are agent-native (action + context parity) |
| [`architecture-strategist`](agents/review/architecture-strategist.md) | Architecture, design patterns, naming conventions, and structural integrity |
| [`cloud-architect`](agents/review/cloud-architect.md) | Cloud infrastructure review, cost optimization, DR, migration strategies |
| [`code-simplicity-reviewer`](agents/review/code-simplicity-reviewer.md) | Final pass for simplicity and minimalism |
| [`database-guardian`](agents/review/database-guardian.md) | Database schema, constraints, and migration code validation |
| [`kieran-reviewer`](agents/review/kieran-reviewer.md) | Python and TypeScript code review with strict conventions |
| [`performance-oracle`](agents/review/performance-oracle.md) | Performance analysis and optimization |
| [`security-sentinel`](agents/review/security-sentinel.md) | Security audits and vulnerability assessments |
| [`spec-flow-analyzer`](agents/review/spec-flow-analyzer.md) | Analyze user flows and identify gaps in specifications |

### Research (4)

| Agent | Description |
|-------|-------------|
| [`best-practices-researcher`](agents/research/best-practices-researcher.md) | Best practices, framework docs, and implementation patterns |
| [`git-history-analyzer`](agents/research/git-history-analyzer.md) | Analyze git history and code evolution |
| [`learnings-researcher`](agents/research/learnings-researcher.md) | Search institutional learnings for relevant past solutions |
| [`repo-research-analyst`](agents/research/repo-research-analyst.md) | Research repository structure and conventions |

### Design (2)

| Agent | Description |
|-------|-------------|
| [`design-iterator`](agents/design/design-iterator.md) | Iteratively refine UI through systematic design iterations |
| [`figma-design-sync`](agents/design/figma-design-sync.md) | Compare UI against Figma designs, report discrepancies, and optionally implement fixes |

### Workflow (5)

| Agent | Description |
|-------|-------------|
| [`bug-reproduction-validator`](agents/workflow/bug-reproduction-validator.md) | Systematically reproduce and validate bug reports |
| [`deployment-engineer`](agents/workflow/deployment-engineer.md) | CI/CD pipeline design, deployment strategies, GitOps workflows |
| [`deployment-verification-agent`](agents/workflow/deployment-verification-agent.md) | Create Go/No-Go deployment checklists for risky data changes |
| [`devops-engineer`](agents/workflow/devops-engineer.md) | Docker containerization, monitoring/observability, incident management |
| [`pr-comment-resolver`](agents/workflow/pr-comment-resolver.md) | Address PR comments and implement fixes |

## Commands

### Workflow Commands

Core workflow commands use `workflows:` prefix to avoid collisions with built-in commands:

| Command | Description |
|---------|-------------|
| `/workflows:brainstorm` | Explore requirements and approaches before planning |
| `/workflows:plan` | Create implementation plans |
| `/workflows:review` | Run comprehensive code reviews |
| `/workflows:work` | Execute work items systematically |
| `/workflows:compound` | Document solved problems to compound team knowledge |
| `/workflows:document-release` | Post-ship documentation sync across README/ARCHITECTURE/CONTRIBUTING/CHANGELOG |

### Utility Commands

| Command | Description |
|---------|-------------|
| `/lfg` | Full autonomous engineering workflow (plan, build, review, ship). Use `--swarm` for parallel execution |
| `/agent-native-audit` | Run agent-native architecture review with scored principles |
| `/deepen-plan` | Enhance plans with parallel research agents for each section |
| `/changelog` | Create engaging changelogs for recent merges |
| `/report-bug` | Report a bug in the plugin |
| `/reproduce-bug` | Reproduce bugs using logs and console |
| `/resolve-todo-parallel` | Resolve todos from /todos/ directory in parallel |
| `/setup` | Configure which review agents run for your project (auto-detects stack) |
| `/triage` | Triage and prioritize issues |
| `/test-browser` | Run browser tests on PR-affected pages |
| `/feature-video` | Record video walkthroughs and add to PR description |
| `/adr` | Create Architecture Decision Records with format selection and lifecycle management |
| `/compound-refresh` | Review docs/solutions/ for stale learnings -- keep, update, replace, or archive |
| `/ideate` | Generate ranked improvement ideas by scanning the codebase |
| `/resolve-pr-parallel` | Batch-resolve PR review comments via parallel subagents |
| `/verify` | Pre-PR verification pipeline (build, types, lint, tests, security) |

## Skills

### Architecture & Design

| Skill | Description |
|-------|-------------|
| [`agent-native-architecture`](skills/agent-native-architecture/SKILL.md) | Build AI agents using prompt-native architecture |
| [`frontend-design`](skills/frontend-design/SKILL.md) | Create production-grade frontend interfaces |
| [`react-frontend`](skills/react-frontend/SKILL.md) | React, TypeScript, Next.js patterns, Vitest/RTL testing |
| [`tailwind-css`](skills/tailwind-css/SKILL.md) | Tailwind CSS v4 patterns, component variants, v3 migration |
| [`simplifying-code`](skills/simplifying-code/SKILL.md) | Simplify, polish, and declutter code |

### Language & Framework

| Skill | Description |
|-------|-------------|
| [`nodejs-backend`](skills/nodejs-backend/SKILL.md) | Node.js backend patterns: Express/Fastify, TypeScript, validation |
| [`php-laravel`](skills/php-laravel/SKILL.md) | Modern PHP 8.4 and Laravel patterns, PHPUnit testing |
| [`python-services`](skills/python-services/SKILL.md) | Python CLI tools, async parallelism, FastAPI services |
| [`terraform`](skills/terraform/SKILL.md) | Terraform/OpenTofu configuration, modules, testing, state |
| [`postgresql`](skills/postgresql/SKILL.md) | PostgreSQL schema design, query optimization, indexing |
| [`pinescript`](skills/pinescript/SKILL.md) | Pine Script v6 patterns for TradingView |
| [`linux-bash-scripting`](skills/linux-bash-scripting/SKILL.md) | Defensive Bash scripting for Linux |

### Testing

| Skill | Description |
|-------|-------------|
| [`writing-tests`](skills/writing-tests/SKILL.md) | Generic test discipline: quality, anti-patterns, rationalization resistance |

### Code Quality & Review

| Skill | Description |
|-------|-------------|
| [`code-review`](skills/code-review/SKILL.md) | Two-stage code reviews with severity-ranked findings |
| [`receiving-code-review`](skills/receiving-code-review/SKILL.md) | Process review feedback critically: verify, push back, no blind agreement |
| [`debugging`](skills/debugging/SKILL.md) | Systematic root-cause debugging with anti-rationalization patterns |
| [`verification-before-completion`](skills/verification-before-completion/SKILL.md) | Fresh verification evidence before any completion claim |
| [`planning`](skills/planning/SKILL.md) | Software implementation planning with file persistence |

### Content & Workflow

| Skill | Description |
|-------|-------------|
| [`brainstorming`](skills/brainstorming/SKILL.md) | Explore requirements and approaches through dialogue |
| [`compound-docs`](skills/compound-docs/SKILL.md) | Capture solved problems as categorized documentation |
| [`document-review`](skills/document-review/SKILL.md) | Improve documents through structured self-review |
| [`file-todos`](skills/file-todos/SKILL.md) | File-based todo tracking system |
| [`git-worktree`](skills/git-worktree/SKILL.md) | Manage Git worktrees for parallel development |
| [`md-docs`](skills/md-docs/SKILL.md) | Manages project documentation: AGENTS.md, README.md |
| [`writing`](skills/writing/SKILL.md) | Prose editing, rewriting, and humanizing text |

### AI & Prompting

| Skill | Description |
|-------|-------------|
| [`meta-prompting`](skills/meta-prompting/SKILL.md) | Enhanced reasoning patterns via slash commands |
| [`refine-prompt`](skills/refine-prompt/SKILL.md) | Transform vague prompts into precise instructions |
| [`reflect`](skills/reflect/SKILL.md) | Session retrospective and skill audit |

### Multi-Agent Orchestration

| Skill | Description |
|-------|-------------|
| [`orchestrating-swarms`](skills/orchestrating-swarms/SKILL.md) | Comprehensive guide to multi-agent swarm orchestration |


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
claude /plugin install compound-engineering
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
