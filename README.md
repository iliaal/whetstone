# Whetstone

[![Claude Code Plugin](https://img.shields.io/badge/Claude_Code-Plugin-blue?logo=anthropic&logoColor=white)](https://code.claude.com/docs/en/plugins)
[![Version](https://img.shields.io/github/v/release/iliaal/whetstone)](https://github.com/iliaal/whetstone/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Follow @iliaa](https://img.shields.io/badge/Follow-@iliaa-000000?style=flat&logo=x&logoColor=white)](https://x.com/intent/follow?screen_name=iliaa)

![Whetstone](images/whetstone-hero.jpg)

A Claude Code plugin that makes AI coding agents follow engineering discipline. Plan before coding. Verify before claiming done. Find root cause before patching. Review before merge. Skills activate based on file type and task signals, not manual toggling.

Bundles agents, skills, workflow commands, and a skill distillery for PHP, Python, TypeScript, React, and infrastructure workflows.

## Who this is for

**Teams using Claude Code for real work.** You build with PHP, Python, TypeScript, or React and want the agent to plan before building, verify before shipping, and debug from evidence.

**Solo developers who want consistency.** Bash tasks receive guidance on strict mode and ShellCheck; Laravel tasks receive strict-type and thin-controller patterns. Skills guide the agent; only checks actually run can establish compliance.

**Anyone building with AI agents.** Includes skills for multi-agent orchestration, agent-native architecture design, and a distillery that generates new skills from top-rated community sources.

## The problem

AI coding agents skip planning, claim "done" without verifying, patch symptoms over root causes, and forget what they learned when context resets. The output looks polished even when the process behind it is missing.

The long-form argument is at [AI Agents Don't Lack Capability. They Lack Process.](https://ilia.ws/blog/ai-agents-dont-lack-capability-they-lack-process). This plugin supplies that process as instructions and supporting tools.

## 🚀 Install

### Claude Code (recommended)

```bash
/plugin marketplace add https://github.com/iliaal/whetstone
/plugin install whetstone@iliaal-marketplace
/reload-plugins
```

### Standalone skills (any AI coding agent)

Individual skills work with Claude Code, Cursor, Codex, Gemini CLI, Copilot CLI, OpenCode, and [35+ other agents](https://agentskills.io) via the [ai-skills](https://github.com/iliaal/ai-skills) repo:

```bash
# All skills
npx skills add iliaal/ai-skills

# Single skill
npx skills add iliaal/ai-skills -s code-review

# Target a specific agent
npx skills add iliaal/ai-skills -a cursor
```

### Codex

Install Whetstone's portable skills and Context7 integration through the repository's native Codex marketplace:

```bash
git clone https://github.com/iliaal/whetstone
cd whetstone
bash scripts/install-codex-plugin.sh
```

Start a new Codex thread after installation or update. The native package includes Whetstone's cross-harness skills and Context7 MCP server. Claude-specific agents, slash commands, and hooks remain available only through the Claude Code plugin.

No shipped skill carries Claude's `disable-model-invocation` flag or its Codex twin, `allow_implicit_invocation: false` in `agents/openai.yaml`. Commands reach skills through explicit `Skill()` tool calls, which the harness treats as model invocation, so either flag makes that call fail. Trigger control lives in each skill's `description`. `scripts/test-codex-plugin.sh` asserts the set of flagged skills stays empty.

Normal Whetstone releases refresh the local Codex plugin before publication when `codex` is on `PATH`. For source edits between releases, use the wrapper that applies a temporary cachebuster, reinstalls, and restores the tracked release version:

```bash
bash scripts/refresh-codex-plugin.sh
```

The legacy converter remains available for OpenCode and other non-plugin targets.

In this checkout, Codex also discovers the 12 repository commands and `skill-distiller` through `.agents/skills/`. Invoke them as `$release`, `$audit-plugin`, `$write-skill`, or `$skill-distiller`, with arguments after the name. Command wrappers read the maintained `.claude/commands/` sources. If an existing session has not refreshed its skill list, start a new Codex session. These repository workflows are separate from the distributed plugin skills.

### OpenCode

OpenCode reads skills from its per-project config. The converter translates the plugin's `SKILL.md` format into OpenCode's expected shape and writes output into the current project (override with `--output <dir>`).

Command-based `PreToolUse` and `PostToolUse` hooks use a bundled adapter; unsupported hook events and types cause conversion to fail. Whetstone's injection hook requires Bash and `jq` on PATH. The installed bundle includes its scripts and skill files, so it does not depend on the source checkout.

```bash
bun run src/index.ts install ./plugins/whetstone --to opencode
```

Cleanup for OpenCode (and other targets) uses the same command:

```bash
bun run src/index.ts cleanup --target opencode
bun run src/index.ts cleanup --target kilocode
bun run src/index.ts cleanup --target agents
```

Use `cleanup --target opencode --output <dir>` for a custom installation. Default OpenCode cleanup checks the current project and legacy global locations. Cleanup backs up individually identified Whetstone artifacts and preserves unrelated or customized files; files whose ownership cannot be established require manual review.

### Additional targets (symlink-based)

For tools that read skills directly from `~/.agents/skills` or `~/.kilocode/skills`, `scripts/sync-to-tools.sh` symlinks the plugin's skill directory into each path so edits land immediately without re-conversion. It removes legacy Whetstone-owned links from `~/.codex/skills` and adds managed Codex exclusions for the same skills discovered through `~/.agents/skills`; the native plugin remains Codex's single source.

```bash
bash scripts/sync-to-tools.sh              # symlink into shared non-Codex tool dirs
bash scripts/sync-to-tools.sh --dry-run    # preview changes
```

## 🔗 Works well with

- **[codesage](https://github.com/iliaal/codesage)** adds structural code intelligence (find symbols, references, dependencies, blast-radius analysis) as an MCP server. Whetstone supplies process guidance; CodeSage supplies codebase structure for applying it.
- **[ai-skills](https://github.com/iliaal/ai-skills)** is the read-only mirror of this plugin's skills for agents without native Whetstone plugin support.

## 🛠️ The workflow

Five commands form a loop: explore the problem, plan the solution, build it, review it, document what you learned. Each pass makes the next one faster because solutions accumulate as searchable docs.

| Command | What it does |
|---------|-------------|
| `/ia-brainstorm` | Interviews you one question at a time to surface hidden requirements. Produces 2-3 named approaches with trade-offs. No code until a design doc is approved. |
| `/ia-plan` | Turns a brainstorm or feature idea into a file-based plan with atomic tasks, specific file paths, and phased delivery in vertical slices. |
| `/ia-work` | Executes a plan with task tracking, worktree isolation, and verification gates. Each task runs through build/test before marking complete. |
| `/ia-review` | Multi-agent code review: scope-drift detection, spec compliance, code quality, security, performance. Auto-escalates to deep mode on complex diffs. |

Each command also works on its own: `/ia-review` as a pre-merge check, `/ia-plan` for scoping.

![Without the plugin vs with the plugin](images/compound-before-after.png)

## ✨ Skills

Skills are instructions selected for the task. They guide procedures and identify anti-patterns; they are not runtime enforcement of the agent's decisions.

### Architecture & design

| Skill | Description |
|-------|------------|
| [ia-agent-native-architecture](plugins/whetstone/skills/ia-agent-native-architecture/SKILL.md) | 15-area architecture checklist for systems where AI agents are primary actors: tool design, execution patterns, context injection, approval gates, audit trails. For designing agent systems or MCP tools. |
| [ia-frontend-design](plugins/whetstone/skills/ia-frontend-design/SKILL.md) | Requires a design philosophy statement before code, detects existing design systems to match, and bans AI design cliches (purple-to-blue gradients, Space Grotesk, three-card hero layouts). Calibrates output via variance, motion, and density parameters. For work where visual identity matters. |
| [ia-simplifying-code](plugins/whetstone/skills/ia-simplifying-code/SKILL.md) | Declutters code without changing behavior. Targets AI slop: redundant comments, unnecessary defensive checks, over-abstraction, verbose stdlib reimplementations. Applies changes in priority order and stops before touching public APIs. For cleanup after AI generation or accumulated complexity. |

### Language & framework

| Skill | Description |
|-------|------------|
| [ia-react-frontend](plugins/whetstone/skills/ia-react-frontend/SKILL.md) | Decision tree routing most "should I use an effect?" questions to non-effect solutions. Separates state tools by purpose (Zustand for client, React Query for server, nuqs for URL). Enforces React 19 patterns, App Router server/client boundaries, and flags that Server Actions are public endpoints. For React, Next.js, and Vitest/RTL testing. |
| [ia-nodejs-backend](plugins/whetstone/skills/ia-nodejs-backend/SKILL.md) | Strict layered architecture (routes > services > repos) with no cross-layer HTTP imports. Contract-first API design using Zod schemas as the single source of truth. Requires production patterns such as circuit breakers and load shedding. For Express, Fastify, Hono, or NestJS backends. |
| [ia-python-services](plugins/whetstone/skills/ia-python-services/SKILL.md) | Mandates modern tooling (uv, ruff, ty) over legacy equivalents. Structured concurrency via `asyncio.TaskGroup`, idempotent background jobs, and structured JSON logging with correlation IDs via `contextvars`. For Python CLI tools, FastAPI services, async workers, or new project setup. |
| [ia-php-laravel](plugins/whetstone/skills/ia-php-laravel/SKILL.md) | `declare(strict_types=1)` everywhere, PHPStan level 8+, fat models / thin controllers, Form Requests with `toDto()`, event-driven side effects. Prevents N+1 by disabling lazy loading in dev. Defaults to feature tests through the full HTTP stack. For Laravel codebases. |
| [ia-rust-systems](plugins/whetstone/skills/ia-rust-systems/SKILL.md) | Edition 2024, workspace layout with inward-only deps, `thiserror` in libraries / `anyhow` in binaries, no `unwrap`/`expect` outside `main` and tests, every `unsafe` block needs a `// SAFETY:` comment. Tokio patterns (JoinSet, CancellationToken, bounded mpsc) and axum service layout. For Rust CLIs, axum services, or cargo workspaces. |
| [ia-c-systems](plugins/whetstone/skills/ia-c-systems/SKILL.md) | Repo conventions outrank the skill, so it defers on tabs, `goto cleanup`, and macros that return rather than fighting established C. Function altitudes (orchestrator / leaf / adapter) gated behind a name test that stops over-decomposition, status enums with one producer per error value, public-validates / internal-asserts boundaries. Separate references for memory safety (sanitizers, overflow-checked allocation, recursion to bounded worklists) and PHP extension C. For C11 and later, native extensions, and systems code. |
| [ia-cpp-systems](plugins/whetstone/skills/ia-cpp-systems/SKILL.md) | Rule of zero by default and rule of five once a destructor appears, since a user-declared destructor silently suppresses moves. `unique_ptr` first and `shared_ptr` third. API rules that break callers when ignored: decide `explicit` at introduction, keep the narrow overload, delete rather than silently ignore. Separate references for ABI boundaries (exceptions must not cross `extern "C"`, PIMPL, visibility) and CMake tooling. For C++17 and later libraries and services. |
| [ia-pinescript](plugins/whetstone/skills/ia-pinescript/SKILL.md) | Guides Pine Script v6 syntax, platform limits, signal stability checks, and walk-forward validation. Distinguishes historical indexing from future outcomes and chart-bar confirmation from requested-timeframe confirmation. |

### Infrastructure

| Skill | Description |
|-------|------------|
| [ia-postgresql](plugins/whetstone/skills/ia-postgresql/SKILL.md) | BIGINT GENERATED ALWAYS AS IDENTITY over SERIAL, TIMESTAMPTZ over TIMESTAMP, indexes on every FK (Postgres doesn't auto-create them). Includes an unindexed FK detection query and mandates `EXPLAIN (ANALYZE, BUFFERS)` before any optimization claim. For schema design, query tuning, RLS, or partitioning. |
| [ia-terraform](plugins/whetstone/skills/ia-terraform/SKILL.md) | Specific file organization, `for_each` over `count` to prevent recreation on reordering, remote state with locking, `moved` blocks for renames, and four-tier testing (validate > tflint > plan tests > integration). For Terraform or OpenTofu. |
| [ia-linux-bash-scripting](plugins/whetstone/skills/ia-linux-bash-scripting/SKILL.md) | `set -Eeuo pipefail` as foundation, EXIT traps for cleanup, `printf` over `echo`, arrays over eval, `local` separated from assignment. Production templates for atomic writes, retry with backoff, and script locking. For any Bash script meant for production. |

### Testing & quality

| Skill | Description |
|-------|------------|
| [ia-writing-tests](plugins/whetstone/skills/ia-writing-tests/SKILL.md) | DAMP over DRY, test cases from user journeys not implementation details, real objects over mocks (mocks only at system boundaries). Requires red-green cycles for bug fix tests. Includes a 13-excuse Rationalization Table for when you're tempted to skip tests. Works with any language. |
| [ia-code-review](plugins/whetstone/skills/ia-code-review/SKILL.md) | Checks specification compliance before code quality, tracks selected-file coverage, and ranks findings by severity and evidence. Selects deep review when 3+ risk signals apply. Reports suggested action routes without editing during review-only work. For PR reviews and code audits. |
| [ia-receiving-code-review](plugins/whetstone/skills/ia-receiving-code-review/SKILL.md) | Verify-before-implement for every comment. Different skepticism levels by source: maximum for automated agents, trusted-but-verified for project owners. Requires evidence when pushing back. Prohibits performative agreement. For processing review feedback on your code. |
| [ia-debugging](plugins/whetstone/skills/ia-debugging/SKILL.md) | Reproduces the reported symptom, tests evidence-backed hypotheses, and verifies permanent repairs with regressions. Distinguishes authorized incident mitigation from root-cause repair and preserves diagnosis-only scope. Reassesses after 3 failed cycles without imposing a fixed tracing depth. |
| [ia-verification-before-completion](plugins/whetstone/skills/ia-verification-before-completion/SKILL.md) | Requires fresh evidence through Identify, Run, Read, Verify, Claim. Checks the actual revision and entry point, reports missing coverage, and distinguishes fixtures from live proof. Accepts a clean review when its coverage supports the conclusion. |
| [ia-planning](plugins/whetstone/skills/ia-planning/SKILL.md) | Chooses a durable plan, inline list, or direct implementation from dependencies, recovery needs, and unresolved decisions. File counts are signals rather than automatic triggers. Plans name concrete tasks, ownership, verification, and runnable phase outcomes. |

### Content & workflow

| Skill | Description |
|-------|------------|
| [ia-brainstorming](plugins/whetstone/skills/ia-brainstorming/SKILL.md) | Hard gate: no code until a design doc is approved. Reads the codebase first, interviews one question at a time, proposes 2-3 named approaches with trade-offs, saves a structured doc to `docs/brainstorms/`. For vague requirements or multiple valid interpretations. |
| [ia-document-review](plugins/whetstone/skills/ia-document-review/SKILL.md) | Activates specialized lenses (Product, Design, Security, Scope Guardian, Adversarial) based on document signals. Scores on four criteria, identifies one critical improvement, and can dispatch a fresh-eyes sub-agent. For polishing specs or brainstorms before handing them to planning. |
| [ia-writing](plugins/whetstone/skills/ia-writing/SKILL.md) | Edits prose while preserving meaning, facts, and voice. Treats vocabulary and structural tells as contextual signals, with separate edit and detect-only modes and guidance for publication surfaces. For blog posts, PR descriptions, docs, and changelogs. |
| [ia-git-worktree](plugins/whetstone/skills/ia-git-worktree/SKILL.md) | Routes all operations through a manager script handling `.env` copying, `.gitignore` updates, and dependency installation. Detects execution context and adapts. For parallel feature development or isolated reviews. |
| [ia-md-docs](plugins/whetstone/skills/ia-md-docs/SKILL.md) | Treats AGENTS.md as the canonical context file. Verifies every factual claim against the actual codebase before writing. For project documentation that's stale, missing, or needs initialization. |

### AI & prompting

| Skill | Description |
|-------|------------|
| [ia-meta-prompting](plugins/whetstone/skills/ia-meta-prompting/SKILL.md) | Decision modifiers through natural language or prompt markers: `/verify-think` challenges an answer, `/adversarial` ranks counterarguments, `/edge` explores failure scenarios, and `/confidence` scores claims. Distinct from the `/ia-verify` command's pre-PR checks. |
| [ia-reflect](plugins/whetstone/skills/ia-reflect/SKILL.md) | Scans the full conversation for mistakes, friction, and wins, citing specific exchanges. Proposes ranked improvements and audits skills used in the session for token efficiency. For end-of-session lessons learned. |

### Multi-agent orchestration

| Skill | Description |
|-------|------------|
| [ia-orchestrating-swarms](plugins/whetstone/skills/ia-orchestrating-swarms/SKILL.md) | Coordinates independent agents with explicit scope, file ownership, and verification assignments. Uses worktrees or a shared-tree workflow with exclusive writes and parent-owned integration. Defines worker recovery, independent review, and four status signals. |

## 🤖 Agents

Specialized subagents dispatched by the main agent or by workflow commands. Each runs in isolation with its own tools and context.

### Review

| Agent | Description |
|-------|------------|
| [ia-accessibility-tester](plugins/whetstone/agents/ia-accessibility-tester.md) | WCAG 2.1 audit across keyboard navigation, screen reader compatibility, contrast ratios, ARIA attributes, and form accessibility. For compliance checks before launch. |
| [ia-architecture-strategist](plugins/whetstone/agents/ia-architecture-strategist.md) | Evaluates architectural soundness, design pattern compliance, and structural consistency. For service additions, refactors, or codebase pattern audits. |
| [ia-cloud-architect](plugins/whetstone/agents/ia-cloud-architect.md) | Analyzes infrastructure against Well-Architected Framework principles: cost optimization, scalability, disaster recovery across AWS, Azure, and GCP. |
| [ia-code-simplicity-reviewer](plugins/whetstone/agents/ia-code-simplicity-reviewer.md) | Produces a simplification report (no code changes) identifying YAGNI violations and over-engineering. For post-implementation analysis. |
| [ia-database-guardian](plugins/whetstone/agents/ia-database-guardian.md) | Validates migration safety, referential constraints, and data integrity. For PRs touching migrations, backfills, or data transformations. |
| [ia-kieran-reviewer](plugins/whetstone/agents/ia-kieran-reviewer.md) | Opinionated Python and TypeScript review with a high bar for type safety, naming clarity, and modern patterns. |
| [ia-performance-oracle](plugins/whetstone/agents/ia-performance-oracle.md) | Identifies bottlenecks in algorithmic complexity, database queries, memory usage, and scalability limits. |
| [ia-security-sentinel](plugins/whetstone/agents/ia-security-sentinel.md) | Threat modeling and vulnerability scanning across authentication, input validation, secrets management, and OWASP categories. |
| [ia-spec-flow-analyzer](plugins/whetstone/agents/ia-spec-flow-analyzer.md) | Maps user flows through specifications to surface edge cases, missing clarifications, and completeness gaps before implementation. |

### Research

| Agent | Description |
|-------|------------|
| [ia-best-practices-researcher](plugins/whetstone/agents/ia-best-practices-researcher.md) | Gathers official framework docs, version-specific best practices, and industry standards for any technology. |
| [ia-git-history-analyzer](plugins/whetstone/agents/ia-git-history-analyzer.md) | Excavates git history to explain code evolution: traces commits, authors, and context around decisions. |
| [ia-repo-research-analyst](plugins/whetstone/agents/ia-repo-research-analyst.md) | Analyzes repository architecture, naming conventions, and implementation patterns. For onboarding or understanding project conventions. |

### Design

| Agent | Description |
|-------|------------|
| [ia-design-iterator](plugins/whetstone/agents/ia-design-iterator.md) | Iterative UI refinement through screenshot-analyze-improve cycles. For when initial design changes produce mediocre results. |
| [ia-figma-design-sync](plugins/whetstone/agents/ia-figma-design-sync.md) | Compares implemented UI against Figma designs, reports discrepancies, and optionally applies fixes. |

### Workflow

| Agent | Description |
|-------|------------|
| [ia-bug-reproduction-validator](plugins/whetstone/agents/ia-bug-reproduction-validator.md) | Reproduces bug reports and identifies root causes without applying fixes. Validates whether reports are genuine bugs before engineers invest. |
| [ia-deployment-verification-agent](plugins/whetstone/agents/ia-deployment-verification-agent.md) | Generates Go/No-Go deployment runbooks with SQL verification queries, rollback procedures, and monitoring plans for high-risk changes. Runs after database-guardian validates migration code. |
| [ia-infrastructure-engineer](plugins/whetstone/agents/ia-infrastructure-engineer.md) | Full deployment-lifecycle coverage: CI/CD pipelines (blue-green, canary, rolling, feature flags), Docker and containerization, observability stacks (metrics/logs/traces), and incident management. Not for DB migration verification (use deployment-verification-agent). |
| [ia-pr-comment-resolver](plugins/whetstone/agents/ia-pr-comment-resolver.md) | Implements a single pre-triaged PR comment where the action is already agreed on. For mechanical fixes, not judgment calls. |

## ⚡ Commands

All commands carry the `ia-` prefix to avoid collisions with Claude Code built-ins and sibling plugins.

### Workflow commands

| Command | Description |
|---------|------------|
| `/ia-brainstorm` | Explore requirements and approaches through one-at-a-time interviews before planning. |
| `/ia-plan` | Turn feature ideas into file-based implementation plans with atomic tasks and vertical slices. |
| `/ia-work` | Execute plans with task tracking, worktree isolation, and verification gates. |
| `/ia-review` | Multi-agent code review: scope-drift detection, spec compliance, code quality, security, performance. |
| `/ia-document-release` | Post-ship documentation sync across README, ARCHITECTURE, CONTRIBUTING, and CHANGELOG. |

### Utility commands

| Command | Description |
|---------|------------|
| `/ia-lfg` | Full autonomous workflow: plan, build, review, ship. Use `--swarm` for parallel execution. |
| `/ia-verify` | Pre-PR verification pipeline: build, types, lint, tests, security scan, diff review. |
| `/ia-resolve-pr` | Batch-resolve PR review comments via cluster analysis and parallel agents. |
| `/ia-deepen-plan` | Enhance an existing plan with parallel research agents for each section. |
| `/ia-ideate` | Generate ranked improvement ideas by scanning the codebase, then divergent ideation and adversarial critique. |
| `/ia-setup` | Auto-detect project stack and configure which review agents run. |
| `/ia-adr` | Create Architecture Decision Records with format selection and lifecycle management. |
| `/ia-refine-prompt` | Rewrite a vague prompt into specification language against a six-element checklist, within 0.75x-1.5x of the original length. |
| `/ia-test-browser` | Run browser tests on pages affected by the current PR or branch. |
| `/ia-feature-video` | Record a video walkthrough of a feature and add it to the PR description. |
| `/ia-changelog` | Build changelogs from recent merges. |
| `/ia-reproduce-bug` | Reproduce bugs using logs and console output. |
| `/ia-report-bug` | Report a bug in the plugin. |
| `/ia-agent-native-audit` | Run agent-native architecture review with scored principles. |

## Design

Every token a skill spends is one the agent can't use on your code, so the skills are kept short:

- **Aim below 1K body tokens; 2K hard cap.** Generated and shipped skill validators use the same budget estimator (`cl100k_base`, or characters/4 when unavailable). Keep operative scope and verification rules inline; move detailed topic guidance to conditionally loaded `references/` files.
- **Front-loaded.** Critical rules come first because model attention drops off with length.
- **Actions, not explanations.** Tell the agent what to do, not what things are. Skip anything the model already knows.
- **Every "don't" has a "do instead."** Bare prohibitions leave the agent guessing. Alternatives give it a clear path.
- **Keyword-rich descriptions.** Only the description loads at startup. The agent uses it to decide whether to activate a skill, so it carries the phrases developers type. The body loads when the skill triggers.

## Skill distillery

The `distillery/` directory is a pipeline for generating, evaluating, and evolving skills. It fetches top-rated community skills, analyzes overlapping advice, strips filler, resolves contradictions, and synthesizes one focused instruction set per topic.

Beyond generation, the distillery mines Claude Code session logs to build evaluation datasets, scores skill effectiveness via LLM-as-judge, and evolves skills through DSPy optimization. Skills that pass evaluation get promoted to the plugin.

```bash
python3 distillery/scripts/distiller.py search "react"     # Find source skills
python3 distillery/scripts/distiller.py harvest-sessions    # Mine session logs for eval data
python3 distillery/scripts/distiller.py dspy-eval <skill>   # Score via LLM-as-judge
python3 distillery/scripts/distiller.py evolve <skill>      # Optimize via DSPy
python3 distillery/scripts/distiller.py test-triggers       # Regression test trigger patterns
```

## Repository structure

```
whetstone/
├── plugins/whetstone/   # The plugin
│   ├── agents/                     # 19 specialized subagents
│   ├── commands/                   # 22 slash commands
│   ├── skills/                     # 32 skills
│   ├── hooks/                      # Skill injection into subagents
│   └── README.md                   # Full component reference
├── distillery/                     # Skill generation, eval, and evolution
│   ├── scripts/                    # distiller.py + tests
│   └── generated-skills/           # Generated skill output
├── scripts/                        # Repo maintenance
└── src/                            # Bun/TS CLI for OpenCode/Codex conversion
```

## Acknowledgements

Two projects informed the shape of this plugin:

- **[EveryInc/compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin)**: the original "compound engineering" framing (each unit of engineering work should make the next one easier), the brainstorm > plan > work > review > compound loop, and the multi-target install model for Codex / OpenCode / Copilot / Gemini / Kiro / Pi.
- **[ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills)**: curated catalog of Claude skills the distillery mines for source material, alongside skills.sh.

## License

MIT

---

[Follow @iliaa on X](https://x.com/iliaa) • [Blog](https://ilia.ws) • If this improved your AI workflow, ⭐ star it!
