# Changelog

All notable changes to the compound-engineering plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.49.1] - 2026-03-27

### Changed

- **Migrated `resolve-pr-parallel` from skill to command** -- was already `disable-model-invocation: true` with `argument-hint`, now properly lives in `commands/` with `$ARGUMENTS` interpolation and `receiving-code-review` skill delegation
- Scripts moved to `commands/scripts/`; cross-references updated in code-review, pr-comment-resolver, file-todos

## [2.49.0] - 2026-03-27

### Added

- **Security detection patterns** reference (`code-review/references/security-patterns.md`) covering 11 vulnerability classes with grep-able signatures: deployment entrypoints, config/secrets, auth/authz, CSRF, XSS, cache, file handling, SQL/NoSQL injection, SSRF, open redirects, CORS
- **Review dispatch templates** for orchestrating-swarms: Stage 1 (spec compliance) and Stage 2 (code quality) prompt templates for subagent review handoffs
- **Core principles reference** for agent-native-architecture: moved 95-line prose to `references/core-principles.md`, replaced with summary table (saves ~320 tokens per invocation)
- 3 missing commands added to README tables: `/adr`, `/compound-refresh`, `/ideate`

### Changed

- **Cross-repo sync improvements** across 30 skills, 12 agents, 8 commands:
  - Skill descriptions: removed workflow leaks from 5 skills (CSO pattern from superpowers) -- descriptions now contain only trigger conditions
  - Research verification triggers added to react-frontend, tailwind-css, nodejs-backend, pinescript (search current docs before implementing version-sensitive patterns)
  - Writing skill: 5 new anti-slop sections (lazy extremes, negative listing, performative emphasis, telling-instead-of-showing, rhythm rules)
  - Code review: findings now require `quoted code` for Critical/Important severity
  - Planning: anti-gold-plating rule, ADR cross-reference for architectural decisions
  - Brainstorming: deep interview layer now selective (not blanket "always runs"), design doc template collapsed from 30 lines to 3
  - Orchestrating swarms: status signals now instructed (not just expected) in teammate prompts
  - Review deduplication made specific: same file:line + same issue class = merge, keep higher severity
  - Compound docs: trigger synonyms added (post-mortem, lessons learned, knowledge base)
  - File todos: trigger synonyms added (task tracking, backlog)
- **Agent category corrections**: cloud-architect moved to review/, deployment-verification-agent to workflow/, spec-flow-analyzer to review/
- **Agent quality**: 5 agents fixed from "you will:" to imperative style; pr-comment-resolver Example 2 fixed (was multi-comment, contradicted single-comment description); design-iterator and figma-design-sync now reference verification-before-completion; deployment-engineer and devops-engineer descriptions now exclude each other's domains; best-practices-researcher Example 4 fixed (was debugging question); repo-research-analyst raw `rg` reference replaced with Grep tool; agent-native-reviewer duplicated TypeScript block replaced with skill reference
- **Command fixes**: `$ARGUMENTS` interpolation added to adr, changelog, triage, resolve_todo_parallel (all had argument-hint but never used the value); workflows:compound Phase 2 now delegates to compound-docs skill instead of reimplementing; triage inline naming conventions removed (delegates to file-todos skill); workflows:plan now references planning skill; agent-native-audit persists report to docs/audits/; reproduce-bug and bug-reproduction-validator descriptions differentiated
- **Skill refinements**: debugging anti-patterns table rendering bug fixed (blank line splitting table); document-review naked negations replaced with paired constraints; pinescript anti-patterns restricted to coding patterns (trading advice removed); postgresql stale PG11/PG12 version markers removed
- README command count corrected: 18 -> 21
- Global CLAUDE.md: output completeness rule added (banned placeholder comments in code)

## [2.48.0] - 2026-03-22

### Added

- **Deep interview protocol** in brainstorming, planning, and deepen-plan -- probes assumptions, second-order effects, research-backed challenges with citations, contradiction tracking, completeness assessment
- **User context calibration** in brainstorming -- reads vocabulary/framing signals to adapt question style
- **Decision authority principle** in planning -- Claude decides technical implementation, user decides experience-affecting tradeoffs
- **Experiential progress framing** in workflows:work -- milestones reported as user-visible changes, not technical diffs
- **Post-research interview** in deepen-plan (Step 6.5) -- surfaces agent contradictions with cited evidence before enhancing the plan
- **Skills.sh marketplace scan** in sync-from-repos (Phase 2b) -- cross-references existing skills against marketplace for improvements
- **Post-sync audit recommendation** in sync-from-repos (Phase 6) -- suggests running audit after applying external changes
- **Three audit checks** from distiller: temporal accuracy (stale version pins), description keyword gaps, trigger pattern accuracy
- **Language review profiles** for code-review -- TypeScript, Python, PHP, Shell, Config, Data Formats, Security, LLM Trust Boundaries in references/language-profiles.md
- **Four-level severity** in code-review -- added Medium between Important and Minor for maintainability issues
- **Orchestration best practices** #9-13 -- two-stage per-task review, implementer status signals (DONE/BLOCKED/NEEDS_CONTEXT), worktree-based parallel dispatch, post-integration verification, context provision
- **File structure table** in planning template -- map all files before defining tasks
- **pytest patterns** in python-services -- flags, fixtures, conftest, autospec, markers, Protocol typing, context managers, project layout
- **Routing + migrations** sections in php-laravel -- scoped model binding, anonymous migrations, JSON response envelope
- **Security hardening** in php-laravel ecosystem reference -- session hardening, security headers middleware, encrypted casts, signed URLs, composer audit
- **ESLint integration** in tailwind-css -- eslint-plugin-better-tailwindcss rules
- **CSS Modules + animate patterns** in tailwind-css -- @reference "#tailwind", z-index tokens, tw-animate-css
- **Circuit breaker** in nodejs-backend -- opossum for outbound service calls, Clean Architecture dependency rule
- **Double-bezel depth technique** in frontend-design -- nested container pattern, blur scroll entry, staggered --index reveals, IntersectionObserver mandate
- **Button-in-button CTA pattern** + hero construction + content register + eyebrow tags in frontend-design
- **Five anti-slop checks** in writing -- cut quotables, Wh-word openers, meta-joiners, same-length sentence detection, one-liner variation
- **Common mistakes table** + approved response templates in receiving-code-review
- **Output contract** in simplifying-code -- scope, key changes, verification, residual risks

### Improved

- **brainstorming** -- explore project context before questions, isolation/clarity design principles in Phase 3, collapsed redundant YAGNI/Incremental Validation/Integration sections
- **debugging** -- under-pressure inoculation in Iron Law, trimmed Common Patterns to 3 non-obvious entries, removed duplicate anti-pattern row
- **verification-before-completion** -- "I'm tired" and spirit-over-letter rationalization rows
- **receiving-code-review** -- deleted redundant Forbidden Responses (covered by Common Mistakes table)
- **planning** -- zero-context engineer framing for tasks, merged Relationship + Integration sections
- **postgresql** -- pg_stat_statements slow-query detection, table bloat check
- **php-laravel** -- DatabaseTransactions/DatabaseMigrations distinction, Http::fake(), Gate::forUser(), coverage target, dropped stale "since Laravel 9" pin, fixed Kernel.php framing for Laravel 11+

### Fixed

- Em dashes replaced with double hyphens across all 82 plugin markdown files (skills, references, agents, commands)
- Stale `/doc-fix` reference replaced with `/workflows:compound`
- PHP 8.2+ version pin in md-docs init template updated to 8.4+
- Duplicate `workflows:work` entry in verification-before-completion Integration merged
- bug-reproduction-validator description updated to match body (includes RCA, not "reproduction only")
- Description overlap disambiguated for frontend-design/react-frontend and document-review/brainstorming pairs

## [2.47.2] - 2026-03-21

### Improved

- **code-review** — scope drift check integrated into review process step 1, search-before-recommending anti-pattern
- **debugging** — sanitize-before-search rule, scope lock on hypothesis, structured debug report format, recurring fix site detection
- **writing** — changelog voice section (sell test, contributor subsection, verb tense)
- **verification-before-completion** — review staleness check, merged Red Flags into Rationalization Prevention
- **planning** — scope challenge trigger (8+ files or 2+ new classes)
- **nodejs-backend** — new `references/api-design.md` (cursor pagination, filtering, sorting, deprecation)
- **react-frontend** — flaky test quarantine workflow in e2e-testing reference
- **simplifying-code** — placeholder stub bans in AI Slop Removal
- **frontend-design** — extracted Creative Arsenal and Redesigning to references
- **agent-native-architecture** — extracted quick-start template to references, flattened reference index
- **linux-bash-scripting** — added output format definition

### Fixed

- Stale `agent-browser` skill references in feature-video and test-browser commands
- `refine-prompt` now asks before writing to `.ai/PROMPT.md`
- README MCP tool names corrected (`search_docs`/`fetch_doc`)
- Invalid JSON in meta-prompting `/json` schema
- Removed incorrect `disable-model-invocation: true` from orchestrating-swarms
- `workflows:review` step numbering fixed (1-6), file-todos duplication cut (~137 lines)
- `workflows:plan` templates extracted to `references/plan-templates.md` (~277 lines)
- `triage` file-todos duplication cut (~100 lines)
- `deepen-plan` agent-filtering clarified, MCP references updated context7 → docfork
- `resolve_todo_parallel` agent scope fixed (general-purpose instead of pr-comment-resolver)
- Cross-references added between 6 component pairs
- `code-simplicity-reviewer` and `agent-native-reviewer` agents trimmed of duplicated skill content
- Removed inert frontmatter (`color:`, `license:`) from 4 files
- Stale `spec-reviewer` → `spec-flow-analyzer` in brainstorming skill and brainstorm command
- Removed orphaned `tailwind-css/manifest.json` and `compound-docs/schema.yaml`
- `best-practices-researcher` MCP reference updated context7 → docfork

## [2.47.1] - 2026-03-18

### Fixed

- README component counts (23 agents, 18 commands, 30 skills), Review heading (10 not 11), added missing `/workflows:document-release` to commands table
- Stale "LFG/SLFG" references in `workflows:plan` -- replaced with "LFG"
- Added Before/After Screenshots table to `workflows:work` PR template
- Updated `skill-patterns.sh` total count comment

## [2.47.0] - 2026-03-18

### Changed

- **Merged `/lfg` + `/slfg`** into single `/lfg` command with `--swarm` flag for parallel execution
- **Absorbed `finishing-branch` skill** into `workflows:work` Phase 4 -- PR template, safety rules, and ship options now inline. Saves 1542 tokens per session.
- **Moved `setup` from skill to command** -- invoked explicitly via `/setup`, no longer in trigger-matching pool. Saves 1257 tokens per session.
- **`reproduce-bug` command** -- added Playwright MCP availability guard

### Removed

- **`/slfg` command** -- merged into `/lfg --swarm`
- **`/generate_command` command** -- generic scaffold with project-specific refs, Claude handles this natively
- **`/heal-skill` command** -- reactive skill fixing absorbed into `/audit-plugin`
- **`finishing-branch` skill** -- absorbed into `workflows:work`
- **`setup` skill** -- moved to `/setup` command (still available, just not a skill)

## [2.46.0] - 2026-03-18

### Changed

- **Merged `kieran-python-reviewer` + `kieran-typescript-reviewer`** into single `kieran-reviewer` agent -- ~1400 tokens saved, 50% shared content deduplicated
- **Disambiguated trigger descriptions** -- pr-comment-resolver vs resolve-pr-parallel, code-simplicity-reviewer vs simplifying-code, architecture-strategist vs code-review, bug-reproduction-validator vs debugging now have clearly distinct descriptions
- **design-iterator agent** -- removed false "skill auto-loaded" claims, collapsed duplicate screenshot sections
- **agent-native-reviewer agent** -- replaced inline anti-pattern examples with skill reference, ~40% token reduction
- **learnings-researcher agent** -- moved schema to external reference, removed duplicate efficiency guidelines
- **pr-comment-resolver agent** -- aligned description and body to "pre-triaged mechanical" scope
- **agent-native-architecture skill** -- removed "Why Now" filler block, fixed second-person heading
- **frontend-design skill** -- added Verify section, removed preamble restating frontmatter
- **Trimmed filler** across compound-docs, file-todos, git-worktree, orchestrating-swarms (removed preambles restating frontmatter, redundant prose, stale timestamps)
- **php-laravel skill** -- added missing verify command to Discipline section

## [2.45.9] - 2026-03-18

### Changed

- **reproduce-bug command** — made generic (removed project-specific rails/appsignal agent refs, uses debugging skill methodology)
- **workflows:brainstorm command** — trimmed to thin orchestration wrapper, delegates process knowledge to brainstorming skill
- **changelog command** — replaced stale EVERY_WRITE_STYLE.md reference with writing skill, documented intentional emoji override
- **agent-native-audit command** — added cross-reference to agent-native-reviewer agent
- **brainstorming skill** — trimmed verbose preamble
- **agent-native-architecture skill** — removed second person ("you should")
- **setup skill** — removed dead `plan_review_agents` config field
- **skill-distiller** — added triage-before-fetch step and manual npx fallback for fetch failures

## [2.45.8] - 2026-03-18

### Changed

- **code-review skill** — Fix-First Heuristic: classify findings as AUTO-FIX (mechanical) or ASK (judgment), batch-apply safe fixes. Added suppression list (things NOT to flag), LLM trust boundary checks, enum/value completeness tracing, evidence confidence levels, doc staleness detection
- **debugging skill** — formalized multi-component boundary instrumentation (enter/exit/verify at each layer), defined "attempt" for three-fix threshold, deepened root cause evidence requirement (two levels deep)
- **planning skill** — task granularity to 2-5 minutes with exact commands/code, subagent-based plan review loop (max 3 iterations), completeness rule (don't defer tests/edge cases)
- **brainstorming skill** — scope decomposition gate for multi-subsystem requests, spec review loop with subagent before user approval
- **writing-tests skill** — complete mock data structure rule, test pollution bisection technique, user journey-driven test case derivation
- **verification-before-completion skill** — ordered verification chain (build->types->lint->test->security, stop on first failure), periodic checkpoints during long sessions
- **simplifying-code skill** — explicit async/sync conversion prohibition, domain-step preservation rule, impact prioritization (control flow->naming->duplication->types)
- **receiving-code-review skill** — prescriptive YAGNI grep-before-implementing workflow
- **finishing-branch skill** — post-merge test failure recovery (revert merge, keep branch, diagnose)
- **writing skill** — person rules clarified (you/we/I usage, avoid third-person passive)

### Fixed

- **brainstorming/planning conflict** — explicit handoff: brainstorm outputs approved spec to `docs/brainstorms/`, planning takes it as input
- **code-review** — prior comments instruction bolded and repositioned for visibility
- **planning skill** — clarified `.plan/` (ephemeral working state) vs `docs/plans/` (committed formal plans) distinction
- **debugging skill** — added `bug-reproduction-validator` agent and `reproduce-bug` command to integration section

### Removed

- **`/resolve_parallel` command** — merged into `/resolve_todo_parallel` (was a near-duplicate)
- Stale references: `/technical_review` -> `/workflows:review` in deepen-plan and workflows:plan commands
- Stale references: `cora-test-reviewer` agent removed from workflows:compound (agent doesn't exist)
- Stale reference: `/compound command` -> `/workflows:compound` in compound-docs skill

## [2.45.7] - 2026-03-18

### Added

- **`/workflows:document-release` command** — post-ship documentation sync. After code ships and a PR exists, cross-references every doc file against the diff and brings README, ARCHITECTURE, CONTRIBUTING, CLAUDE.md/AGENTS.md up to date. Polishes CHANGELOG voice, cleans up completed TODOs, and asks about version bumps. Auto-applies factual updates; stops to ask only for narrative or risky changes. Commits modified docs as a single `docs:` commit and updates the PR body with a per-file change summary.

## [2.45.6] - 2026-03-18

### Changed

- **writing skill** — added False Agency section (inanimate actors → name the person), narrator-from-a-distance principle, throat-clearing openers and emphasis crutches to banned phrases, scoring rubric (Directness/Rhythm/Trust/Authenticity/Density, target 35/50) to self-check
- **writing skill** — added `references/phrases.md` (extended jargon table, adverb list, meta-commentary, sentence starters to avoid) and `references/examples.md` (7 before/after transformations)
- **frontend-design skill** — added dependency check policy (verify package.json before any import), explicit no-emoji rule, form layout rule (label above, error below), GSAP/Framer Motion separation guidance, Creative Arsenal section (navigation, layout, card, typography, micro-interaction patterns)

## [2.45.5] - 2026-03-17

### Changed

- **code-review skill** — fetch MR/PR discussions before writing findings to avoid re-raising resolved issues
- **code-review skill** — use diff content directly for added files instead of reading from working tree on remote branches

## [2.45.4] - 2026-03-14

### Changed

- **meta-prompting skill** — added output format awareness to intro line (pattern results now marked inline)
- **writing skill** — converted Self-Check from prose to 4-step procedural checklist with done definition
- **pinescript skill** — added Workflow section with 4-step development cycle and overfit detection
- **linux-bash-scripting skill** — added Verify section (shellcheck + shfmt + edge case testing)
- **nodejs-backend skill** — added verify line to Discipline section (tsc + npm test)
- **postgresql skill** — added Verify section (EXPLAIN ANALYZE + unindexed FK check)
- **python-services skill** — added verify line to Discipline section (pytest + ruff)

### Added

- **CLAUDE.md** — added SkillsBench Quality Dimensions checklist (output format, success criteria, constraints, procedural content, optimal length)
- **md-docs init-agents.md** — added SkillsBench quality rules for generated AGENTS.md files
- **distiller.py** — added `token-budget` command with SkillsBench effectiveness rating (OPTIMAL/VERBOSE/OVER_BUDGET)

## [2.45.3] - 2026-03-14

### Changed

- **code-review skill** — added untracked files to scope resolution fallback chain (new files were invisible to review)
- **receiving-code-review skill** — added `gh api` reply command for inline PR thread replies
- **brainstorming skill** — added trivially-scoped escape hatch and multi-subsystem decomposition signal
- **planning skill** — added execution handoff line pointing to `workflows:work`
- **simplifying-code skill** — added dense transform chain pattern to Smell-to-Fix table
- **frontend-design skill** — added Motion library performance guardrails (useMotionValue, leaf client components), strengthened Tailwind version check in redesign section
- **tailwind-css skill** — expanded border radius v3-to-v4 rename table (5 explicit mappings replacing 1 vague row)
- **refine-prompt skill** — added missing-context sub-checklist to Context assessment row
- **verification-before-completion skill** — added verification phase order (build, typecheck, lint, test, diff)
- **react-frontend skill** — added RSC safety rules to App Router decision section

## [2.45.2] - 2026-03-10

### Fixed

- **php-laravel skill** — tightened trigger pattern to stop false positives on bare "PHP" mentions (php-src, prose about PHP). Removed standalone `\bphp\b` match; now requires Laravel/framework context (eloquent, blade, artisan, phpunit, phpstan, "php controller", etc.). Updated skill description to exclude PHP internals.

## [2.45.1] - 2026-03-08

### Changed

- **frontend-design skill** — enriched with anti-slop rules from taste-skill research: forbidden AI patterns (no pure black, no Inter, no 3-card rows, no AI purple), content realism rules (organic data, no generic names/brands/cliches), performance guardrails (transform/opacity only, z-index discipline), interactivity requirements (skeleton loaders, empty states, tactile feedback), and a prioritized 7-step redesign audit checklist for upgrading existing interfaces

## [2.45.0] - 2026-03-07

### Added

- **`/verify` command** — pre-PR verification pipeline with 4 modes (quick, full, pre-commit, pre-pr). Runs build, types, lint, tests, security scan, and diff review. Produces structured READY/NOT READY report.
- **`scripts/validate-cross-refs.sh`** — CI validation script that checks agents, commands, skills, and README for broken cross-references to nonexistent components. Strips code blocks to avoid false positives.

### Changed

- **writing skill** — added explicit banned phrases list ("In today's rapidly evolving landscape", "game-changer", "Moreover" as sentence starter, etc.) with "delete and rewrite on sight" instruction
- **best-practices-researcher agent** — merged `framework-docs-researcher` into this agent. Now covers best practices, framework docs, source code analysis, and deprecation checks in one agent.
- **architecture-strategist agent** — merged `pattern-recognition-specialist` into this agent. Now covers architecture, design patterns, naming conventions, and structural integrity.
- **design-iterator agent** — removed verbatim `frontend-design` skill aesthetics block; now references the skill instead of duplicating it
- **figma-design-sync agent** — removed 80+ lines of Tailwind CSS patterns and Rails ERB examples; now references the `tailwind-css` skill
- **design-implementation-reviewer agent** — removed persona filler, added `tailwind-css` skill reference
- **performance-oracle agent** — removed hardcoded benchmarks (200ms API, 5KB bundle), removed persona filler, added `postgresql` and `react-frontend` skill references
- **pr-comment-resolver agent** — added references to `receiving-code-review` and `verification-before-completion` skills, removed generic professional conduct filler
- **bug-reproduction-validator agent** — stripped persona filler ("meticulous Bug Reproduction Specialist"), now opens with mission statement
- **spec-flow-analyzer agent** — stripped persona filler ("elite User Experience Flow Analyst"), kept scope/mission
- **security-sentinel agent** — stripped persona opener and motivational closer, replaced with direct instructions
- **data-integrity-guardian agent** — stripped persona filler, kept mission statement

### Fixed

- **kieran-python-reviewer agent** — fixed malformed example block (two assistant responses in one example)
- **kieran-typescript-reviewer agent** — fixed malformed example block (same issue)
- **bug-reproduction-validator agent** — fixed duplicate section numbering (two sections numbered "6.")
- **git-history-analyzer agent** — rewritten with concrete step-by-step methodology, explicit Bash tool usage, structured output template, and scope boundaries
- **All 21 read-only agents** — added `autoApprove: read` for frictionless file access during reviews and research
- **4 agents** (`deployment-engineer`, `devops-engineer`, `cloud-architect`, `accessibility-tester`) — added missing `<examples>` blocks for better routing

### Removed

- **framework-docs-researcher agent** — merged into `best-practices-researcher`
- **pattern-recognition-specialist agent** — merged into `architecture-strategist`

## [2.44.0] - 2026-03-07

### Changed

- **code-review skill** — added SOLID smell patterns (God classes, leaky abstractions), next-steps action menu, behavior-vs-implementation test check
- **brainstorming skill** — added non-goals topic, solution-first detection, 3-5 bullet summary gate before Phase 2, convergence loop cap
- **git-worktree skill** — auto-detect and install dependencies after worktree creation, `git worktree prune` guidance
- **python-services skill** — added `asyncio.TaskGroup` for structured concurrency, `lru_cache`/`cache` memoization, connection pooling mandate
- **md-docs skill** — actionable heading style, collapsible `<details>` depth pattern, README anti-patterns section
- **react-frontend skill** — Server Action auth/authz security warning, `<Activity>` component, `template.tsx`/`default.tsx` conventions, metadata templates, `after()` API, module-level I/O hoisting, `content-visibility: auto`, defer state reads
- **nodejs-backend skill** — Piscina for worker threads, new Production Resilience section (Redis caching, load shedding, response schema serialization)
- **php-laravel skill** — query scopes, `withCount`/`withExists`, `when()` conditional queries, `DB::transaction()`, `upsert()`, model pruning, Form Request `toDto()`, conditional validation rules
- **postgresql skill** — safe schema evolution, `NULLS NOT DISTINCT`, `jsonb_path_ops`, materialized views, `fillfactor`, approximate counts, `pg_try_advisory_lock`
- **meta-prompting skill** — steelmanning in `/adversarial`, new `/premortem` pattern, synthesis requirement for combos
- **agent-native-architecture skill** — governance checklist (approval gates, audit trail, scope boundaries), VBR pattern, context durability/WAL pattern
- **linux-bash-scripting skill** — `main()` + source guard, `PS4` debug tracing, named exit codes, `PIPESTATUS`, input validation, `umask 077`, signal traps
- **terraform skill** — `moved` blocks, troubleshooting section (force-unlock, refresh-only, replace, import), `state_key` for parallel tests, Stacks awareness, `cidrsubnet()`, multi-region provider aliases
- **resolve-pr-parallel skill** — severity classification, bot-comment filtering, batch commit strategy

## [2.43.0] - 2026-03-07

### Added

- **tailwind-css skill** — new skill for Tailwind CSS v4: CSS-first configuration (`@theme`, `@utility`, `@custom-variant`), v3→v4 breaking changes, coding rules, class merging with `cn()`, component variants (`tailwind-variants`/CVA), common errors, dark mode patterns. Includes reference files for component patterns and layout patterns. Distilled from 8 skills.sh sources.

### Changed

- **code-review skill** — added scope resolution fallback chain, language-specific checks (TypeScript, Python, PHP, security), verification step, confidence levels, merge-readiness verdict
- **verification-before-completion skill** — added "letter vs spirit" clause, broader trigger conditions, rationalization prevention table
- **debugging skill** — added architectural problem indicators, expanded pattern comparison, 2 new anti-patterns
- **receiving-code-review skill** — added "can't verify" escape hatch, 3 concrete good/bad examples
- **writing-tests skill** — explicit verify steps for bug-fix-first testing, "test passes immediately" heuristic
- **brainstorming skill** — hard gate blocking implementation until design approval, git commit for design docs
- **simplifying-code skill** — stop conditions, 2 new constraints against scope creep
- **git-worktree skill** — safety verification with `git check-ignore`, baseline test verification
- **refine-prompt skill** — persistence section for saving prompts to `.ai/PROMPT.md`
- **finishing-branch skill** — concise options, inline worktree cleanup
- **md-docs skill** — CONTRIBUTING.md auto-detection, DOCS.md awareness

## [2.42.2] - 2026-02-28

### Fixed

- **postgresql skill** — pgvector dimensions now model-agnostic instead of hardcoding OpenAI ada-002's 1536
- **php-laravel, react-frontend skills** — removed duplicated "tests expose bugs" directive, added cross-reference to `writing-tests` skill
- **code-review skill** — description clarified for performing reviews (vs receiving feedback)
- **receiving-code-review skill** — description clarified for responding to review comments
- **devops-engineer, cloud-architect agents** — "Use for" → "Use when" for consistent trigger phrasing
- **agent-native-reviewer agent** — added cross-reference to `agent-native-architecture` skill
- **bug-reproduction-validator agent** — added cross-references to `writing-tests` and `debugging` skills
- **4 research agents** — removed hardcoded "2026" year note (redundant with system context)

## [2.42.1] - 2026-02-27

### Changed

- **postgresql skill** — re-distilled from upstream sources (Supabase, PlanetScale, postgres-patterns). Added RLS, concurrency patterns (UPSERT, deadlock prevention, N+1, queue processing), connection pooling, unindexed FK detection. Split operations and full-text search into `references/` for progressive disclosure.
- **code-review skill** — added test coverage and resource cleanup review steps, expanded security terms (CSRF, SSRF, path traversal, unsafe deserialization), large diff handling guidance, clean review output.
- **planning skill** — added flat-list planning tier for medium tasks, session recovery with `git diff --stat` reconciliation.
- **debugging skill** — added stale state pattern, pattern comparison technique, explicit "no root cause found" escape hatch.

## [2.42.0] - 2026-02-27

### Added

- **Skill distillery** — absorbed `~/ai/skills` repo into `distillery/`. Skills are now generated, validated, and A/B tested directly in the plugin repo. Eliminates the 3-repo pipeline.
- **mirror-to-ai-skills.sh** — new script to mirror plugin skills to the `ai-skills` public repo (reverse of old bundle-skills.sh direction)
- **skill-distiller skill** — project-level skill (`.claude/skills/skill-distiller/`) for distillery workflow

### Removed

- **bundle-skills.sh** — replaced by direct skill editing + mirror-to-ai-skills.sh
- **.bundle-manifest.json** — all skills are now native; no native/bundled distinction

## [2.41.0] - 2026-02-27

### Added

- **planning skill** — bundled `scripts/init-plan.sh` to scaffold `.plan/` directory with pre-populated template files (task_plan.md, findings.md, progress.md) and auto-gitignore. Replaces inline bash snippets with a deterministic script.
- **debugging skill** — bundled `scripts/collect-diagnostics.sh` to gather environment diagnostics (system info, language versions, git state, project files, environment variables). Supports differential analysis of working vs broken environments.
- **compound-docs skill** — bundled `scripts/validate-frontmatter.sh` to validate solution doc YAML frontmatter against the schema (required fields, enum values, date format, array constraints). Replaces LLM-based validation with deterministic checking.

### Changed

- **frontend-design skill** — added "Design Philosophy (Write First, Code Second)" section requiring a 3-sentence design philosophy (Intent, Signature, Constraint) before implementation for full pages/apps. Small components skip the philosophy and match surrounding design. Inspired by Anthropic's philosophy-first pattern in algorithmic-art/canvas-design skills.

## [2.40.0] - 2026-02-24

### Changed

- **Skill consolidation (33 → 31 skills)** — absorbed `testing-laravel` into `php-laravel` and `testing-react` into `react-frontend`. Testing content moved to `references/` for progressive disclosure. Hook trigger patterns merged into parent skills.
- **Description trimming (23 skills)** — reduced system prompt overhead by trimming skill descriptions across 23 skills. Collapsed redundant quoted trigger phrases into concise keyword lists. Removed filler phrasing ("This skill should be used when"). Preserved all meaningful trigger keywords and behavioral anchors.
- **MR/merge request triggers** — added MR trigger coverage to `code-review` and `receiving-code-review` for GitLab workflows
- **planning skill** — added cross-references to `brainstorming` (for ambiguous requirements) and `writing` (for humanizing plan prose)
- **writing-tests skill** — updated cross-references from deleted `testing-laravel`/`testing-react` to `php-laravel`/`react-frontend`

### Fixed

- **update-metadata.sh** — fixed broken jq query for hook counting after hooks.json restructure (`[.[] | .[].hooks | length]` → `[.hooks[][] | .hooks | length]`)

### Removed

- **`testing-laravel` skill** — absorbed into `php-laravel` with testing content as references
- **`testing-react` skill** — absorbed into `react-frontend` with testing content as references

## [2.39.3] - 2026-02-24

### Fixed

- **inject-skills hook** — preserve all original `tool_input` fields in `updatedInput` response. `updatedInput` is a full replacement, not a merge; returning only `{prompt}` dropped `subagent_type`, `description`, and other Task fields, causing "Agent type 'undefined' not found" errors whenever skill patterns matched a subagent prompt.

## [2.39.2] - 2026-02-23

### Fixed

- **inject-skills hook** — added missing `hookEventName: "PreToolUse"` discriminator to hook JSON output, fixing schema validation failure that silently prevented skill injection into subagents

## [2.39.1] - 2026-02-22

### Fixed

- **hooks.json** — added missing top-level `hooks` wrapper key, fixing plugin hook loading error

## [2.39.0] - 2026-02-22

### Added

- **`verification-before-completion` skill** (native) — enforces fresh verification evidence before any completion claim, commit, or PR. 5-step gate function, red flags list, agent delegation rules. Prevents the most common AI failure mode: asserting success without proof.
- **`receiving-code-review` skill** (native) — process code review feedback critically: verify before implementing, push back on incorrect suggestions, no performative agreement. Source-specific handling for user, agents, and external reviewers.
- **`finishing-branch` skill** (native) — workflow closer presenting 4 options (merge locally, push+PR, keep, discard) with safety checks. Handles worktree cleanup. Explicit final step in the workflow chain.
- **`writing-tests` skill** (native) — generic test writing discipline: test quality, real assertions over mocks, anti-patterns, rationalization table. Complements tech-specific testing-laravel and testing-react skills.

### Changed

- **`debugging` skill** — added anti-rationalization framework (merged anti-patterns + red flags into single table), "signals you're off track" section, trivially obvious bug escape with cause-vs-symptom criteria, Integration section
- **`brainstorming` skill** — added workflow chain diagram (canonical source), mkdir instruction for output dir, standardized Integration header
- **`planning` skill** — moved planning files from project root to `.plan/` directory (auto-gitignored), replaced duplicate workflow chain with Integration section
- **`workflows:work` command** — replaced TodoWrite with TaskCreate/TaskUpdate/TaskList, added Phase 2.5 verification gate, delegated Phase 4 shipping to `finishing-branch`, removed stale references (linting-agent, agent-browser skill, imgup skill), removed Co-Authored-By per global rules
- **`code-review` skill** — added Integration section cross-referencing `receiving-code-review`, `workflows:review`, and `resolve-pr-parallel`
- **`verification-before-completion` skill** — softened "exit code 0" to handle pre-existing failures, added `writing-tests` to Integration

### Fixed

- **`finishing-branch` skill** — added guard against default branch invocation, added no-remote guard (disables push/PR when no remote), aligned prerequisites with verification-before-completion for test-free projects, added commit step before options, expanded PR template, delegated worktree cleanup to `git-worktree` skill
- **`receiving-code-review` skill** — added scope table distinguishing from `pr-comment-resolver` agent, fixed triage-then-implement ordering
- **`verification-before-completion` skill** — fixed "in this message" ambiguity to "immediately before the claim", added "When No Verification Command Exists" and "When Verification Fails" sections
- **`writing-tests` skill** — added framework test-double exception (Laravel facade fakes, React providers), added "Tests expose bugs, not the reverse" principle, added Integration section
- **`resolve-pr-parallel` skill** — fixed frontmatter name from underscores to hyphens per naming convention
- **Trigger patterns** — tightened `verification-before-completion` (removed overly broad `before.*(commit|push)`), deduplicated review skill triple-match, fixed `finishing-branch` merge collision, moved `finishing-branch` to Tier 1

---

## [2.38.0] - 2026-02-22

### Added

- **`inject-skills` hook** — PreToolUse hook that intercepts Task tool calls and injects relevant SKILL.md file paths into subagent prompts via `updatedInput`, ensuring subagents follow skill methodology instead of working manually
- **Skill pattern matching** — 29 skills mapped to regex trigger patterns with 3-tier priority system (methodology > domain > supporting), capped at 5 skills per injection
- **`scripts/generate-skill-hooks.sh`** — generation script that extracts trigger keywords from SKILL.md frontmatter to produce `hooks/skill-patterns.sh` as a draft for hand-tuning

---

## [2.37.3] - 2026-02-22

### Fixed

- **MCP server** — removed legacy `.mcp.json` that was installing Context7 MCP alongside Docfork; Docfork is now the sole MCP server, declared in `plugin.json` only
- **Docfork** — no API key required by default (1,000 free requests/month); API keys only needed for team Cabinets and shared indexes

## [2.37.2] - 2026-02-22

### Changed

- **MCP server** — replace Context7 with Docfork (9,000+ libraries, 1,000 free req/month, daily updates)
- **testing-laravel**, **testing-react** — add "review tests" and "check tests" trigger keywords

## [2.37.1] - 2026-02-22

### Fixed

- **H1: Review agent → skill scope clarity** — Added scope notes to security-sentinel, performance-oracle, pattern-recognition-specialist, architecture-strategist clarifying they provide deep specialized analysis while code-review skill handles general review workflows
- **H2: Data agent disambiguation** — Added mutual scope boundaries to data-integrity-guardian (schema/constraints), data-migration-expert (migration code validation), and deployment-verification-agent (deployment checklists) to prevent overlap confusion
- **H3: design-iterator boilerplate** — Replaced verbose generic boilerplate with one-line design-specific instruction
- **H4: php-laravel testing framework** — Changed from Pest to PHPUnit syntax (`test()`/`it()` → `TestCase` extends) to match project conventions
- **H5: Phantom skill reference** — Removed nonexistent `swiss-design` skill reference from design-iterator

## [2.37.0] - 2026-02-22

### Added

- **Bundle infrastructure** — `scripts/bundle-skills.sh` and `.bundle-manifest.json` for syncing generic skills from ai-skills repo into the plugin for distribution
- **19 bundled skills** — code-review, debugging, linux-bash-scripting, md-docs, meta-prompting, nodejs-backend, php-laravel, pinescript, planning, postgresql, python-services, react-frontend, refine-prompt, reflect, simplifying-code, terraform, testing-laravel, testing-react, writing
- **`accessibility-tester` agent** — WCAG 2.1 audit: keyboard navigation, screen reader, contrast, ARIA, forms, cognitive accessibility
- **`cloud-architect` agent** — Cloud infrastructure design: Well-Architected Framework, cost optimization, DR, migration strategies, secrets management
- **`deployment-engineer` agent** — CI/CD pipeline design, deployment strategies (blue-green, canary, rolling, feature flags), GitOps workflows
- **`devops-engineer` agent** — Docker containerization, monitoring/observability (RED/USE methods, OpenTelemetry), incident management
- **External agents analysis** — `docs/external-agents-analysis.md` documenting evaluation of 14 external agents (4 imported, 10 skipped with rationale)

### Changed

- **Agent/skill overlap resolution** — Resolved 6 overlap pairs between agents and skills with clear delegation boundaries (code-simplicity-reviewer→simplifying-code, kieran-typescript-reviewer→domain skills, bug-reproduction-validator→debugging, security-sentinel→nodejs-backend, and more)
- **`php-laravel` skill** — Updated to PHP 8.4 (property hooks, asymmetric visibility, array_find/any/all), added PHPStan level 8+, production performance section (OPcache, JIT, preloading), new `references/laravel-ecosystem.md` (Notifications, Task Scheduling, Custom Casts)
- **`debugging` skill** — Expanded concurrency coverage (deadlocks, async race conditions, pool exhaustion), added Postmortem template
- **`compound-docs` skill** — Generalized all Rails/CORA-specific schema enums, field names, and examples to be stack-agnostic
- **`orchestrating-swarms` skill** — Removed Rails-specific examples from prompts
- **`file-todos` skill** — Generalized Rails Todo model reference

---

## [2.36.0] - 2026-02-21

### Removed

- **Ruby/Rails agents** — Removed `dhh-rails-reviewer`, `kieran-rails-reviewer`, `schema-drift-detector`, `lint`, and `ankane-readme-writer` agents
- **Ruby/Rails skills** — Removed `dhh-rails-style`, `dspy-ruby`, and `andrew-kane-gem-writer` skills
- **Skill creation** — Removed `create-agent-skills` and `skill-creator` skills, and `/create-agent-skill` command
- **Xcode** — Removed `/xcode-test` command
- **Utility skills** — Removed `rclone`, `agent-browser`, and `gemini-imagegen` skills
- **Company-specific** — Removed `every-style-editor` agent and skill
- **Rails-specific** — Removed `julik-frontend-races-reviewer` agent (Hotwire/Turbo/Stimulus focused)
- **Keywords** — Removed `rails`, `ruby`, `image-generation`, `agent-browser`, `browser-automation` from plugin keywords

---

## [2.35.2] - 2026-02-20

### Changed

- **`/workflows:plan` brainstorm integration** — When plan finds a brainstorm document, it now heavily references it throughout. Added `origin:` frontmatter field to plan templates, brainstorm cross-check in final review, and "Sources" section at the bottom of all three plan templates (MINIMAL, MORE, A LOT). Brainstorm decisions are carried forward with explicit references (`see brainstorm: <path>`) and a mandatory scan before finalizing ensures nothing is dropped.

---

## [2.35.1] - 2026-02-18

### Changed

- **`/workflows:work` system-wide test check** — Added "System-Wide Test Check" to the task execution loop. Before marking a task done, forces five questions: what callbacks/middleware fire when this runs? Do tests exercise the real chain or just mocked isolation? Can failure leave orphaned state? What other interfaces need the same change? Do error strategies align across layers? Includes skip criteria for leaf-node changes. Also added integration test guidance to the "Test Continuously" section.
- **`/workflows:plan` system-wide impact templates** — Added "System-Wide Impact" section to MORE and A LOT plan templates (interaction graph, error propagation, state lifecycle, API surface parity, integration test scenarios) as lightweight prompts to flag risks during planning.

---

## [2.35.0] - 2026-02-17

### Fixed

- **`/lfg` and `/slfg` first-run failures** — Made ralph-loop step optional with graceful fallback when `ralph-wiggum` skill is not installed (#154). Added explicit "do not stop" instruction across all steps (#134).
- **`/workflows:plan` not writing file in pipeline** — Added mandatory "Write Plan File" step with explicit Write tool instructions before Post-Generation Options. The file is now always written to disk before any interactive prompts (#155). Also adds pipeline-mode note to skip AskUserQuestion calls when invoked from LFG/SLFG (#134).
- **Agent namespace typo in `/workflows:plan`** — `Task spec-flow-analyzer(...)` now uses the full qualified name `Task compound-engineering:workflow:spec-flow-analyzer(...)` to prevent Claude from prepending the wrong `workflows:` prefix (#193).

---

## [2.34.0] - 2026-02-14

### Added

- **Gemini CLI target** — New converter target for [Gemini CLI](https://github.com/google-gemini/gemini-cli). Install with `--to gemini` to convert agents to `.gemini/skills/*/SKILL.md`, commands to `.gemini/commands/*.toml` (TOML format with `description` + `prompt`), and MCP servers to `.gemini/settings.json`. Skills pass through unchanged (identical SKILL.md standard). Namespaced commands create directory structure (`workflows:plan` → `commands/workflows/plan.toml`). 29 new tests. ([#190](https://github.com/EveryInc/compound-engineering-plugin/pull/190))

---

## [2.33.1] - 2026-02-13

### Changed

- **`/workflows:plan` command** - All plan templates now include `status: active` in YAML frontmatter. Plans are created with `status: active` and marked `status: completed` when work finishes.
- **`/workflows:work` command** - Phase 4 now updates plan frontmatter from `status: active` to `status: completed` after shipping. Agents can grep for status to distinguish current vs historical plans.

---

## [2.33.0] - 2026-02-12

### Added

- **`setup` skill** — Interactive configurator for review agents
  - Auto-detects project type (Rails, Python, TypeScript, etc.)
  - Two paths: "Auto-configure" (one click) or "Customize" (pick stack, focus areas, depth)
  - Writes `compound-engineering.local.md` in project root (tool-agnostic — works for Claude, Codex, OpenCode)
  - Invoked automatically by `/workflows:review` when no settings file exists
- **`learnings-researcher` in `/workflows:review`** — Always-run agent that searches `docs/solutions/` for past issues related to the PR
- **`schema-drift-detector` wired into `/workflows:review`** — Conditional agent for PRs with migrations

### Changed

- **`/workflows:review`** — Now reads review agents from `compound-engineering.local.md` settings file. Falls back to invoking setup skill if no file exists.
- **`/workflows:work`** — Review agents now configurable via settings file
- **`/release-docs` command** — Moved from plugin to local `.claude/commands/` (repo maintenance, not distributed)

### Removed

- **`/technical_review` command** — Superseded by configurable review agents

---

## [2.32.0] - 2026-02-11

### Added

- **Factory Droid target** — New converter target for [Factory Droid](https://docs.factory.ai). Install with `--to droid` to output agents, commands, and skills to `~/.factory/`. Includes tool name mapping (Claude → Factory), namespace prefix stripping, Task syntax conversion, and agent reference rewriting. 13 new tests (9 converter + 4 writer). ([#174](https://github.com/EveryInc/compound-engineering-plugin/pull/174))

---

## [2.31.1] - 2026-02-09

### Changed

- **`dspy-ruby` skill** — Complete rewrite to DSPy.rb v0.34.3 API: `.call()` / `result.field` patterns, `T::Enum` classes, `DSPy::Tools::Base` / `Toolset`. Added events system, lifecycle callbacks, fiber-local LM context, GEPA optimization, evaluation framework, typed context pattern, BAML/TOON schema formats, storage system, score reporting, RubyLLM adapter. 5 reference files (2 new: toolsets, observability), 3 asset templates rewritten.

## [2.31.0] - 2026-02-08

### Added

- **`document-review` skill** — Brainstorm and plan refinement through structured review ([@Trevin Chow](https://github.com/trevin))
- **`/sync` command** — Sync Claude Code personal config across machines ([@Terry Li](https://github.com/terryli))

### Changed

- **Context token optimization (79% reduction)** — Plugin was consuming 316% of the context description budget, causing Claude Code to silently exclude components. Now at 65% with room to grow:
  - All 29 agent descriptions trimmed from ~1,400 to ~180 chars avg (examples moved to agent body)
  - 18 manual commands marked `disable-model-invocation: true` (side-effect commands like `/lfg`, `/deploy-docs`, `/triage`, etc.)
  - 6 manual skills marked `disable-model-invocation: true` (`orchestrating-swarms`, `git-worktree`, `skill-creator`, `compound-docs`, `file-todos`, `resolve-pr-parallel`)
- **git-worktree**: Remove confirmation prompt for worktree creation ([@Sam Xie](https://github.com/samxie))
- **Prevent subagents from writing intermediary files** in compound workflow ([@Trevin Chow](https://github.com/trevin))

### Fixed

- Fix crash when hook entries have no matcher ([@Roberto Mello](https://github.com/robertomello))
- Fix git-worktree detection where `.git` is a file, not a directory ([@David Alley](https://github.com/davidalley))
- Backup existing config files before overwriting in sync ([@Zac Williams](https://github.com/zacwilliams))
- Note new repository URL ([@Aarni Koskela](https://github.com/aarnikoskela))
- Plugin component counts corrected: 29 agents, 24 commands, 18 skills

---

## [2.30.0] - 2026-02-05

### Added

- **`orchestrating-swarms` skill** - Comprehensive guide to multi-agent orchestration
  - Covers primitives: Agent, Team, Teammate, Leader, Task, Inbox, Message, Backend
  - Documents two spawning methods: subagents vs teammates
  - Explains all 13 TeammateTool operations
  - Includes orchestration patterns: Parallel Specialists, Pipeline, Self-Organizing Swarm
  - Details spawn backends: in-process, tmux, iterm2
  - Provides complete workflow examples
- **`/slfg` command** - Swarm-enabled variant of `/lfg` that uses swarm mode for parallel execution

### Changed

- **`/workflows:work` command** - Added optional Swarm Mode section for parallel execution with coordinated agents

---

## [2.29.0] - 2026-02-04

### Added

- **`schema-drift-detector` agent** - Detects unrelated schema.rb changes in PRs
  - Compares schema.rb diff against migrations in the PR
  - Catches columns, indexes, and tables from other branches
  - Prevents accidental inclusion of local database state
  - Provides clear fix instructions (checkout + migrate)
  - Essential pre-merge check for any PR with database changes

---

## [2.28.0] - 2026-01-21

### Added

- **`/workflows:brainstorm` command** - Guided ideation flow to expand options quickly (#101)

### Changed

- **`/workflows:plan` command** - Smarter research decision logic before deep dives (#100)
- **Research checks** - Mandatory API deprecation validation in research flows (#102)
- **Docs** - Call out experimental OpenCode/Codex providers and install defaults
- **CLI defaults** - `install` pulls from GitHub by default and writes OpenCode/Codex output to global locations

### Merged PRs

- [#102](https://github.com/EveryInc/compound-engineering-plugin/pull/102) feat(research): add mandatory API deprecation validation
- [#101](https://github.com/EveryInc/compound-engineering-plugin/pull/101) feat: Add /workflows:brainstorm command and skill
- [#100](https://github.com/EveryInc/compound-engineering-plugin/pull/100) feat(workflows:plan): Add smart research decision logic

### Contributors

Huge thanks to the community contributors who made this release possible! 🙌

- **[@tmchow](https://github.com/tmchow)** - Brainstorm workflow, research decision logic (2 PRs)
- **[@jaredmorgenstern](https://github.com/jaredmorgenstern)** - API deprecation validation

---

## [2.27.0] - 2026-01-20

### Added

- **`/workflows:plan` command** - Interactive Q&A refinement phase (#88)
  - After generating initial plan, now offers to refine with targeted questions
  - Asks up to 5 questions about ambiguous requirements, edge cases, or technical decisions
  - Incorporates answers to strengthen the plan before finalization

### Changed

- **`/workflows:work` command** - Incremental commits and branch safety (#93)
  - Now commits after each completed task instead of batching at end
  - Added branch protection checks before starting work
  - Better progress tracking with per-task commits

### Fixed

- **`dhh-rails-style` skill** - Fixed broken markdown table formatting (#96)
- **Documentation** - Updated hardcoded year references from 2025 to 2026 (#86, #91)

### Contributors

Huge thanks to the community contributors who made this release possible! 🙌

- **[@tmchow](https://github.com/tmchow)** - Interactive Q&A for plans, incremental commits, year updates (3 PRs!)
- **[@ashwin47](https://github.com/ashwin47)** - Markdown table fix
- **[@rbouschery](https://github.com/rbouschery)** - Documentation year update

### Summary

- 27 agents, 23 commands, 14 skills, 1 MCP server

---

## [2.26.5] - 2026-01-18

### Changed

- **`/workflows:work` command** - Now marks off checkboxes in plan document as tasks complete
  - Added step to update original plan file (`[ ]` → `[x]`) after each task
  - Ensures no checkboxes are left unchecked when work is done
  - Keeps plan as living document showing progress

---

## [2.26.4] - 2026-01-15

### Changed

- **`/workflows:work` command** - PRs now include Compound Engineered badge
  - Updated PR template to include badge at bottom linking to plugin repo
  - Added badge requirement to quality checklist
  - Badge provides attribution and link to the plugin that created the PR

---

## [2.26.3] - 2026-01-14

### Changed

- **`design-iterator` agent** - Now auto-loads design skills at start of iterations
  - Added "Step 0: Discover and Load Design Skills (MANDATORY)" section
  - Discovers skills from ~/.claude/skills/, .claude/skills/, and plugin cache
  - Maps user context to relevant skills (Swiss design → swiss-design skill, etc.)
  - Reads SKILL.md files to load principles into context before iterating
  - Extracts key principles: grid specs, typography rules, color philosophy, layout principles
  - Skills are applied throughout ALL iterations for consistent design language

---

## [2.26.2] - 2026-01-14

### Changed

- **`/test-browser` command** - Clarified to use agent-browser CLI exclusively
  - Added explicit "CRITICAL: Use agent-browser CLI Only" section
  - Added warning: "DO NOT use Chrome MCP tools (mcp__claude-in-chrome__*)"
  - Added Step 0: Verify agent-browser installation before testing
  - Added full CLI reference section at bottom
  - Added Next.js route mapping patterns

---

## [2.26.1] - 2026-01-14

### Changed

- **`best-practices-researcher` agent** - Now checks skills before going online
  - Phase 1: Discovers and reads relevant SKILL.md files from plugin, global, and project directories
  - Phase 2: Only goes online for additional best practices if skills don't provide enough coverage
  - Phase 3: Synthesizes all findings with clear source attribution (skill-based > official docs > community)
  - Skill mappings: Rails → dhh-rails-style, Frontend → frontend-design, AI → agent-native-architecture, etc.
  - Prioritizes curated skill knowledge over external sources for trivial/common patterns

---

## [2.26.0] - 2026-01-14

### Added

- **`/lfg` command** - Full autonomous engineering workflow
  - Orchestrates complete feature development from plan to PR
  - Runs: plan → deepen-plan → work → review → resolve todos → test-browser → feature-video
  - Uses ralph-loop for autonomous completion
  - Migrated from local command, updated to use `/test-browser` instead of `/playwright-test`

### Summary

- 27 agents, 21 commands, 14 skills, 1 MCP server

---

## [2.25.0] - 2026-01-14

### Added

- **`agent-browser` skill** - Browser automation using Vercel's agent-browser CLI
  - Navigate, click, fill forms, take screenshots
  - Uses ref-based element selection (simpler than Playwright)
  - Works in headed or headless mode

### Changed

- **Replaced Playwright MCP with agent-browser** - Simpler browser automation across all browser-related features:
  - `/test-browser` command - Now uses agent-browser CLI with headed/headless mode option
  - `/feature-video` command - Uses agent-browser for screenshots
  - `design-iterator` agent - Browser automation via agent-browser
  - `design-implementation-reviewer` agent - Screenshot comparison
  - `figma-design-sync` agent - Design verification
  - `bug-reproduction-validator` agent - Bug reproduction
  - `/review` workflow - Screenshot capabilities
  - `/work` workflow - Browser testing

- **`/test-browser` command** - Added "Step 0" to ask user if they want headed (visible) or headless browser mode

### Removed

- **Playwright MCP server** - Replaced by agent-browser CLI (simpler, no MCP overhead)
- **`/playwright-test` command** - Renamed to `/test-browser`

### Summary

- 27 agents, 20 commands, 14 skills, 1 MCP server

---

## [2.23.2] - 2026-01-09

### Changed

- **`/reproduce-bug` command** - Enhanced with Playwright visual reproduction:
  - Added Phase 2 for visual bug reproduction using browser automation
  - Step-by-step guide for navigating to affected areas
  - Screenshot capture at each reproduction step
  - Console error checking
  - User flow reproduction with clicks, typing, and snapshots
  - Better documentation structure with 4 clear phases

### Summary

- 27 agents, 21 commands, 13 skills, 2 MCP servers

---

## [2.23.1] - 2026-01-08

### Changed

- **Agent model inheritance** - All 26 agents now use `model: inherit` so they match the user's configured model. Only `lint` keeps `model: haiku` for cost efficiency. (fixes #69)

### Summary

- 27 agents, 21 commands, 13 skills, 2 MCP servers

---

## [2.23.0] - 2026-01-08

### Added

- **`/agent-native-audit` command** - Comprehensive agent-native architecture review
  - Launches 8 parallel sub-agents, one per core principle
  - Principles: Action Parity, Tools as Primitives, Context Injection, Shared Workspace, CRUD Completeness, UI Integration, Capability Discovery, Prompt-Native Features
  - Each agent produces specific score (X/Y format with percentage)
  - Generates summary report with overall score and top 10 recommendations
  - Supports single principle audit via argument

### Summary

- 27 agents, 21 commands, 13 skills, 2 MCP servers

---

## [2.22.0] - 2026-01-05

### Added

- **`rclone` skill** - Upload files to S3, Cloudflare R2, Backblaze B2, and other cloud storage providers

### Changed

- **`/feature-video` command** - Enhanced with:
  - Better ffmpeg commands for video/GIF creation (proper scaling, framerate control)
  - rclone integration for cloud uploads
  - Screenshot copying to project folder
  - Improved upload options workflow

### Summary

- 27 agents, 20 commands, 13 skills, 2 MCP servers

---

## [2.21.0] - 2026-01-05

### Fixed

- Version history cleanup after merge conflict resolution

### Summary

This release consolidates all recent work:
- `/feature-video` command for recording PR demos
- `/deepen-plan` command for enhanced planning
- `create-agent-skills` skill rewrite (official spec compliance)
- `agent-native-architecture` skill major expansion
- `dhh-rails-style` skill consolidation (merged dhh-ruby-style)
- 27 agents, 20 commands, 12 skills, 2 MCP servers

---

## [2.20.0] - 2026-01-05

### Added

- **`/feature-video` command** - Record video walkthroughs of features using Playwright

### Changed

- **`create-agent-skills` skill** - Complete rewrite to match Anthropic's official skill specification

### Removed

- **`dhh-ruby-style` skill** - Merged into `dhh-rails-style` skill

---

## [2.19.0] - 2025-12-31

### Added

- **`/deepen-plan` command** - Power enhancement for plans. Takes an existing plan and runs parallel research sub-agents for each major section to add:
  - Best practices and industry patterns
  - Performance optimizations
  - UI/UX improvements (if applicable)
  - Quality enhancements and edge cases
  - Real-world implementation examples

  The result is a deeply grounded, production-ready plan with concrete implementation details.

### Changed

- **`/workflows:plan` command** - Added `/deepen-plan` as option 2 in post-generation menu. Added note: if running with ultrathink enabled, automatically run deepen-plan for maximum depth.

## [2.18.0] - 2025-12-25

### Added

- **`agent-native-architecture` skill** - Added **Dynamic Capability Discovery** pattern and **Architecture Review Checklist**:

  **New Patterns in mcp-tool-design.md:**
  - **Dynamic Capability Discovery** - For external APIs (HealthKit, HomeKit, GraphQL), build a discovery tool (`list_*`) that returns available capabilities at runtime, plus a generic access tool that takes strings (not enums). The API validates, not your code. This means agents can use new API capabilities without code changes.
  - **CRUD Completeness** - Every entity the agent can create must also be readable, updatable, and deletable. Incomplete CRUD = broken action parity.

  **New in SKILL.md:**
  - **Architecture Review Checklist** - Pushes reviewer findings earlier into the design phase. Covers tool design (dynamic vs static, CRUD completeness), action parity (capability map, edit/delete), UI integration (agent → UI communication), and context injection.
  - **Option 11: API Integration** - New intake option for connecting to external APIs like HealthKit, HomeKit, GraphQL
  - **New anti-patterns:** Static Tool Mapping (building individual tools for each API endpoint), Incomplete CRUD (create-only tools)
  - **Tool Design Criteria** section added to success criteria checklist

  **New in shared-workspace-architecture.md:**
  - **iCloud File Storage for Multi-Device Sync** - Use iCloud Documents for your shared workspace to get free, automatic multi-device sync without building a sync layer. Includes implementation pattern, conflict handling, entitlements, and when NOT to use it.

### Philosophy

This update codifies a key insight for **agent-native apps**: when integrating with external APIs where the agent should have the same access as the user, use **Dynamic Capability Discovery** instead of static tool mapping. Instead of building `read_steps`, `read_heart_rate`, `read_sleep`... build `list_health_types` + `read_health_data(dataType: string)`. The agent discovers what's available, the API validates the type.

Note: This pattern is specifically for agent-native apps following the "whatever the user can do, the agent can do" philosophy. For constrained agents with intentionally limited capabilities, static tool mapping may be appropriate.

---

## [2.17.0] - 2025-12-25

### Enhanced

- **`agent-native-architecture` skill** - Major expansion based on real-world learnings from building the Every Reader iOS app. Added 5 new reference documents and expanded existing ones:

  **New References:**
  - **dynamic-context-injection.md** - How to inject runtime app state into agent system prompts. Covers context injection patterns, what context to inject (resources, activity, capabilities, vocabulary), implementation patterns for Swift/iOS and TypeScript, and context freshness.
  - **action-parity-discipline.md** - Workflow for ensuring agents can do everything users can do. Includes capability mapping templates, parity audit process, PR checklists, tool design for parity, and context parity guidelines.
  - **shared-workspace-architecture.md** - Patterns for agents and users working in the same data space. Covers directory structure, file tools, UI integration (file watching, shared stores), agent-user collaboration patterns, and security considerations.
  - **agent-native-testing.md** - Testing patterns for agent-native apps. Includes "Can Agent Do It?" tests, the Surprise Test, automated parity testing, integration testing, and CI/CD integration.
  - **mobile-patterns.md** - Mobile-specific patterns for iOS/Android. Covers background execution (checkpoint/resume), permission handling, cost-aware design (model tiers, token budgets, network awareness), offline handling, and battery awareness.

  **Updated References:**
  - **architecture-patterns.md** - Added 3 new patterns: Unified Agent Architecture (one orchestrator, many agent types), Agent-to-UI Communication (shared data store, file watching, event bus), and Model Tier Selection (fast/balanced/powerful).

  **Updated Skill Root:**
  - **SKILL.md** - Expanded intake menu (now 10 options including context injection, action parity, shared workspace, testing, mobile patterns). Added 5 new agent-native anti-patterns (Context Starvation, Orphan Features, Sandbox Isolation, Silent Actions, Capability Hiding). Expanded success criteria with agent-native and mobile-specific checklists.

- **`agent-native-reviewer` agent** - Significantly enhanced with comprehensive review process covering all new patterns. Now checks for action parity, context parity, shared workspace, tool design (primitives vs workflows), dynamic context injection, and mobile-specific concerns. Includes detailed anti-patterns, output format template, quick checks ("Write to Location" test, Surprise test), and mobile-specific verification.

### Philosophy

These updates operationalize a key insight from building agent-native mobile apps: **"The agent should be able to do anything the user can do, through tools that mirror UI capabilities, with full context about the app state."** The failure case that prompted these changes: an agent asked "what reading feed?" when a user said "write something in my reading feed"—because it had no `publish_to_feed` tool and no context about what "feed" meant.

## [2.16.0] - 2025-12-21

### Enhanced

- **`dhh-rails-style` skill** - Massively expanded reference documentation incorporating patterns from Marc Köhlbrugge's Unofficial 37signals Coding Style Guide:
  - **controllers.md** - Added authorization patterns, rate limiting, Sec-Fetch-Site CSRF protection, request context concerns
  - **models.md** - Added validation philosophy, let it crash philosophy (bang methods), default values with lambdas, Rails 7.1+ patterns (normalizes, delegated types, store accessor), concern guidelines with touch chains
  - **frontend.md** - Added Turbo morphing best practices, Turbo frames patterns, 6 new Stimulus controllers (auto-submit, dialog, local-time, etc.), Stimulus best practices, view helpers, caching with personalization, broadcasting patterns
  - **architecture.md** - Added path-based multi-tenancy, database patterns (UUIDs, state as records, hard deletes, counter caches), background job patterns (transaction safety, error handling, batch processing), email patterns, security patterns (XSS, SSRF, CSP), Active Storage patterns
  - **gems.md** - Added expanded what-they-avoid section (service objects, form objects, decorators, CSS preprocessors, React/Vue), testing philosophy with Minitest/fixtures patterns

### Credits

- Reference patterns derived from [Marc Köhlbrugge's Unofficial 37signals Coding Style Guide](https://github.com/marckohlbrugge/unofficial-37signals-coding-style-guide)

## [2.15.2] - 2025-12-21

### Fixed

- **All skills** - Fixed spec compliance issues across 12 skills:
  - Reference files now use proper markdown links (`[file.md](./references/file.md)`) instead of backtick text
  - Descriptions now use third person ("This skill should be used when...") per skill-creator spec
  - Affected skills: agent-native-architecture, andrew-kane-gem-writer, compound-docs, create-agent-skills, dhh-rails-style, dspy-ruby, every-style-editor, file-todos, frontend-design, gemini-imagegen

### Added

- **CLAUDE.md** - Added Skill Compliance Checklist with validation commands for ensuring new skills meet spec requirements

## [2.15.1] - 2025-12-18

### Changed

- **`/workflows:review` command** - Section 7 now detects project type (Web, iOS, or Hybrid) and offers appropriate testing. Web projects get `/playwright-test`, iOS projects get `/xcode-test`, hybrid projects can run both.

## [2.15.0] - 2025-12-18

### Added

- **`/xcode-test` command** - Build and test iOS apps on simulator using XcodeBuildMCP. Automatically detects Xcode project, builds app, launches simulator, and runs test suite. Includes retries for flaky tests.

- **`/playwright-test` command** - Run Playwright browser tests on pages affected by current PR or branch. Detects changed files, maps to affected routes, generates/runs targeted tests, and reports results with screenshots.
