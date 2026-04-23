# Changelog

All notable changes to the compound-engineering plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2026-04-23

**Breaking**: every skill, agent, and command now carries an `ia-` prefix. The `workflows:` command namespace is gone — `/workflows:plan` is now `/ia-plan`. Any project referencing `compound-engineering:code-review` or similar must update to `compound-engineering:ia-code-review`. See migration note below.

The release bundles the prefix rename with a heavy sync + audit pass: 19 new reference files across 10 skills and 3 agents, walker fixes in the validator, a new Bun CLI `cleanup` subcommand for stale Codex/OpenCode installs, and substantial content additions sourced from EveryInc's compound-engineering-plugin and openai/claude-code-security-review.

### Migration

- Replace every `/workflows:<name>` with `/ia-<name>`.
- Replace every `compound-engineering:<name>` plugin-namespaced reference with `compound-engineering:ia-<name>`.
- ClawHub slugs (`compound-eng-<name>`) and the `ai-skills` mirror (`npx skills add iliaal/ai-skills -s <name>`) are unchanged — existing installs keep working. The `ia-` prefix lives only inside the plugin directory.
- External-project refs already updated for known sites: `~/.claude/commands/dual-review.md`, `~/ai/codesage/.claude/commands/release.md`, `~/ai/php/.claude/commands/{php-improve,php-respond}.md`, `~/ai/php/.claude/skills/php-bug-fixer/SKILL.md`, `~/ai/last30days-skill/REFACTOR_TODO.md`.
- Historical artifacts (`docs/brainstorms/*`, `.claude-cycles/*`) left as-is — frozen records.

### Added

- **Bun CLI `cleanup` subcommand** (`src/commands/cleanup.ts`): moves stale installs to a timestamped backup under `~/.cache/compound-engineering/legacy-backup/`. Supports `--target codex|opencode|kilocode|agents` and `--dry-run`.
- **README install sections**: per-target Codex and OpenCode headings with copy-paste commands and cleanup instructions. Acknowledgements section crediting EveryInc/compound-engineering-plugin and ComposioHQ/awesome-claude-skills.
- **code-review/references/review-traps-catalog.md**: 15 portable review-trap patterns with Trap / Reality / Fix — reachability-before-severity, docs-idiom smoke test, convention-from-3-files, speculative future-design, paired-enum drift, cross-repo contract staleness, PHP 8 null-property-access semantics, Laravel 11+ UUID-v7 chronological sort.
- **code-review/references/{check-categories,action-routing,severity-and-confidence}.md**: What-to-Check lists, 4-tier fix-application taxonomy, 5-band confidence rubric extracted for load-on-demand.
- **security-sentinel references**: `security-fp-suppression.md` (hard exclusions, confidence floor, severity gates, project-level overrides), `security-threat-modeling.md` (STRIDE process + output format), `security-adversarial-pass.md` (happy-path hunt, silent failures, trust-boundary tracing), `security-requirements-checklist.md` (13-item pre-report pass).
- **rust-systems references**: `build-profiles.md` (release/release-dbg/release-min + mold linker), `ci-pipeline.md` (rustsec audit, cargo-llvm-cov, rust-cache, matrix strategy), `production-resilience.md` (fail-fast config, health endpoints, graceful shutdown, retries, timeouts), `observability.md` (tracing init recipe, correlation IDs, metrics, distributed tracing).
- **orchestrating-swarms references**: `resilience-patterns.md` (cascade prevention, recovery strategy, mid-pipeline compensation, post-failure synthesis), `anti-sycophancy.md` (cold-start isolation, fresh instances per round, label randomization, convergence detection), `quick-reference.md` (spawn/message/task/shutdown snippets), `primitives.md` (glossary + file layout), `dispatch-anti-patterns.md` (router persona, persona-calls-persona, sequential paraphraser, deep persona trees).
- **frontend-design references**: `premium-details.md` (`<kbd>` keystroke rendering, faux-OS window chrome, hero image fade, banned meta-labels, baseline alignment, browser-automation safety boundary), `mobile-and-performance.md` (single-column below `md:`, 44x44 touch targets, rotation-on-mobile, GPU-composited animation, z-index discipline).
- **planning/references/plan-deepening.md**: `/deepen-plan` workflow, per-section enhancement format, Enhancement Summary block.
- **writing-tests/references/rationalization-table.md**: 13 rationalization-vs-reality rows for test-skipping pressure.
- **php-laravel/references/production-performance.md**: OPcache, JIT, preloading, Laravel deploy caches. Plus new **Common Pitfalls** section in the main SKILL.md documenting four Laravel-specific recurring bugs (mass-update event bypass, observer parent-scope cleanup, jsonb migration clobber, date-cast wire-format).
- **agents/review/references/database-review-triggers.md**: grep-first review triggers for JSON-column migration clobber, query-builder update skipping observers/audit, column rename missing JSON copies, DynamoDB FilterExpression+Limit pagination, full-attribute replace, paired-enum drift.
- **agents/workflow/references/docker-containerization.md**: Dockerfile best practices, image optimization, container security, graceful shutdown, Docker Compose dev-setup extracted from infrastructure-engineer.

### Changed

- **All skill / agent / command names renamed with `ia-` prefix**. 30 skills + 19 agents + 22 commands. The `workflows:` command namespace is dropped; those 6 commands now live directly under `commands/`. See migration.
- **`hooks/skill-patterns.sh`**: all array keys prefixed with `ia-`; regex strings unchanged (they match user speech, not skill names).
- **30 trigger regression fixture files** renamed to match (`distillery/tests/fixtures/triggers/ia-<name>.jsonl`).
- **security-sentinel**: three-phase methodology (Phase 0 project baseline, Phase 1 comparative analysis, Phase 2 category scans) replaces generic OWASP-style scanning. FP suppression is now a structured framework with hard exclusions, confidence floor (≥0.8), language-gated exclusions, and project-level override honoring — explicitly stricter than `code-review`'s general rubric for a deliberate precision trade-off. Exploit Scenario is now a required field for Critical/High findings.
- **verification-before-completion**: Verification Strategies by Change Type table (Frontend / Backend / CLI / Infra / DB migration / Refactoring). Mandatory adversarial probe for production-logic changes (boundary value, concurrency, idempotency, or orphan op).
- **orchestrating-swarms**: four named dispatch anti-patterns (router persona, persona calls persona, sequential paraphraser, deep persona trees) with why-it-fails for each.
- **code-review**: AI-generated code lens (over-engineering, defensive noise, cost bloat, scope drift) in the Adversarial pass with pointer to `code-simplicity-reviewer` for the 6-trap taxonomy. Project-level override discipline in Anti-Patterns in Reviews.
- **brainstorming**: info-dump + numbered clarifiers pattern for when user opens with rich context.
- **planning**: Execution Handoff section offering explicit Subagent-driven vs Inline choice after plan approval.
- **writing-tests**: Silent Failure Coverage subsection (empty catch, swallowed rejections, converted errors, missing async, no rollback) with assertion-pattern guidance. AI-Generated Test Smells anti-pattern section.
- **rust-systems**: `bytes::Bytes` zero-copy idiom, workspace-level `[workspace.lints.*]`, hot-path allocation reduction (`SmallVec`, `ArrayVec`, `dashmap`+`Box::leak` interning), Tower resilience layer stack naming, `cargo fuzz` for parsers.
- **writing**: `[CURLY-QUOTES]`, `[EMOJI]`, `[FALSE-RANGE]` tags added to long-form audit vocabulary.
- **frontend-design**: Premium Detail Patterns and Browser-Assisted Verification boundary folded in (both extracted to references for body-size discipline).
- **code-simplicity-reviewer**: six named over-production traps (while-I'm-here, for-future-flexibility, defensive-coding, modernization, consistency, cleanup) with scope self-check template.
- **reflect**: `remember:` high-confidence capture marker convention; optional UserPromptSubmit hook pattern documented.
- **document-review**: Step 7 Reader Test strengthened with concrete methodology — predict 5-10 questions, dispatch fresh subagent, interpret confident-correct / confident-wrong / hedged / ambiguity-flagged outcomes.
- **Review and research agents**: `tools: Read, Grep, Glob, Bash` restriction added to accessibility-tester, architecture-strategist, cloud-architect, database-guardian, kieran-reviewer, performance-oracle, security-sentinel, git-history-analyzer. `tools: Read, Grep, Glob` (no Bash) on learnings-researcher.
- **CLAUDE.md working agreement**: added "no personal-machine paths in plugin files" rule (grep -rn '~/ai/' plugins/ pre-flight). Skill compliance checklist now documents the description-as-shortcut failure mode with concrete evidence.
- **Scripts**: `update-metadata.sh` walker excludes `*/references/*` (count fix). `publish-clawhub.sh` strips `ia-` before composing slug (existing URLs preserved). `mirror-to-ai-skills.sh` strips `ia-` on mirror write and rewrites SKILL.md frontmatter (existing `npx skills add` commands preserved). `generate-skill-hooks.sh` TIER_MAP and PROJECT_TYPE_MAP keys prefixed.
- **`distillery/scripts/distiller.py`**: walker skips `*/references/*` when enumerating commands and agents. Placeholder detection strips code blocks and skips forbidding-context sentences (`never use "TBD"`, `Forbid: TBD...`) before matching.

### Fixed

- **`commands/verify.md`**: YAML parse error from unquoted colon in description; frontmatter is now double-quoted.
- **security-sentinel Reporting Protocol** no longer conflicts with Audit Deliverable Format — bridge sentence clarifies the outer-envelope vs SS-NNN finding relationship.
- **`hooks/skill-patterns.sh`**: stale `Total skills: 29` annotation corrected to 30.
- **Body-size discipline**: 10 components brought at-or-near budget through reference extraction — `security-sentinel` 4793 → 3017 tokens; `orchestrating-swarms` 5818 → under 4K; `code-review` 5572 → 4021; `rust-systems` 5282 → 4179; `frontend-design` 5110 → 4183; `planning` 4481 → 4051; `writing-tests` 4254 → under 4K; `php-laravel` 4007 → under 4K; `database-guardian` 3671 → under 3K; `infrastructure-engineer` 3249 → under 3K.
- **Mechanical false positives** eliminated from validate-plugin output (4 reference-file EMPTY_DESCRIPTION walker bugs, 2 TBD-in-forbidding-rule placeholder bugs).
- Edge CDP framework migration (Edge launcher + `post-thread.py` now use the shared `edge-cdp` package).
- Announce tooling: marketing-hook pattern, top-N condensing, `.announce/` thread persistence instead of `/tmp`.
- Audit-plugin VAGUE_DESCRIPTION check, AGENTS.md workflow-description warning.
- README badges added; LICENSE mirrored to ai-skills.

### Removed

- **`workflows:` command namespace**: the 6 commands (`brainstorm`, `plan`, `work`, `review`, `compound`, `document-release`) moved from `commands/workflows/` to flat `commands/` with `ia-` prefix.
- **security-sentinel Operational Guidelines vague bullets**: "Always assume worst-case" and "Don't just find problems" removed; redundant with Adversarial Pass and Remediation Roadmap.
- **Sync log at `~/ai/wiki/tools/compound-engineering-sync-log.md`**: relocated to `docs/audit/audit-log.md` (in-repo, gitignored operational log).

## [2.56.1] - 2026-04-18

Broad hardening pass. Sync + audit cycle applied ~56 refinements across 10 skills, 3 agents, 1 command, and the root context files, plus two new reference files. No new components; existing content got sharper rules, tighter cross-references, and structural fixes exposed by the audit.

### Added

- **orchestrating-swarms/references/context-carry-forward.md**: decision table for long orchestrated sessions — Continue / Rewind / `/compact` / Subagent / `/clear`+brief. Rewind beats "correcting in place" because it drops the failed path from context instead of leaving it as a negative anchor.
- **writing/references/pr-descriptions.md**: PR/MR description style guide. Sizing matrix (1 sentence for trivial, full narrative for architecturally significant), Before / After / Scope-rationale frame, Mermaid-for-topology / table-for-grid rule, GitHub `#NN` auto-link trap, self-check list.
- **agent-native-architecture/references/dynamic-context-injection.md**: new Trust Levels principle. Three-tier model (trusted / semi-trusted / untrusted) with a concrete prompt-injection defense test — inject "ignore all prior rules" into a retrieved document and confirm the agent refuses.

### Changed

- **react-frontend**: 5-class race taxonomy — lifecycle cleanup gaps, remount-timing mistakes, boolean-as-state when UI has more than two modes, stale promises / timers without cancel, per-element handlers where delegation is safer. Each class framed around its production signal, not the rule. Data-fetching cancellation unified: `AbortController` for fetch, `ignore`-flag for non-cancellable promises, React Query covers both.
- **code-review**: Fix-First Classification renamed to Action Routing with a 4-tier split (`safe_auto` / `gated_auto` / `manual` / `advisory`) plus a conservative-route merge rule so a loose classification never promotes a boundary-crossing change to auto-fix. Integration section maps these to `receiving-code-review`'s AUTO-FIX / ESCALATE vocabulary. Configuration profile in `language-profiles.md` promoted from 4 prose bullets to numbered CFG-001 through CFG-006 checks (magnitude-change, timeout hierarchy inversion, pool mismatch, env drift, rollback gap, observability gap).
- **code-review/references/deep-review.md**: reviewer prompt gains DO / DON'T preamble — read the actual code, don't take the PR description at face value, don't rubber-stamp sections you didn't open. Merge algorithm gains a fingerprint-first preamble; two-agent overlap now tags `MULTI-SPECIALIST CONFIRMED (s1 + s2)` with +0.05 confidence, three-agent with +0.10 (applied once per group). Output header reports K-at-3+ / M-at-2 counts so reviewers can scan for convergent signal without reading every finding.
- **code-review/references/reliability-patterns.md**: double-retry stacked anti-pattern. Application `@retry` on an auto-retrying SDK multiplies attempts (3×3 = 9) and the backoff compounds; audit the client's default retry policy before wrapping it, and retry at exactly one layer.
- **orchestrating-swarms**: BLOCKED triage decision tree — missing context re-dispatches same agent, reasoning ceiling escalates model, task-too-large splits, spec-wrong escalates to human. Pre-dispatch file-intersection check as a runnable safety gate with a "no git / no test suite in parallel" constraint embedded in dispatch prompts. Fresh-agent rule on every reviewer re-dispatch across rounds — reviewers carrying memory from a prior round anchor on their earlier verdicts and miss regressions from fixes. NEEDS_CONTEXT aligned to "start or continue" across orchestrating-swarms / verification-before-completion / debugging.
- **deployment-verification-agent**: Rollout Decision Thresholds table with quantified advance / hold / rollback bands for error-rate delta, p95 latency delta, client JS errors, and business metric delta. Stages protocol with SEV-level calibration note. Feature-Flag Lifecycle requirements: owner, expiration date, 2-week cleanup after 100% rollout, no nested flags, both states exercised by CI.
- **performance-oracle**: Core Web Vitals thresholds section. LCP (≤2.5s / ≤4.0s / >4.0s), INP (≤200ms / ≤500ms / >), CLS (≤0.1 / ≤0.25 / >) with Poor-band classification as Critical and Needs-improvement as Important.
- **verification-before-completion**: Scope Confirmation pre-Edit gate for ambiguous-scope imperatives ("migrate my project", "refactor everywhere", "update across the app"). Surface concrete blast radius with `rg` breakdown before any Write or Edit — imperative phrasing is not the same as defined scope.
- **agent-native-architecture**: Context Injection checklist gains a trust-levels bullet pointing at the new Trust Levels principle. Tool Design checklist adds Eval Gate — 10 Q/A pairs, 9/10 CI threshold, closed-data multi-hop tests — surfaced into the body from the MCP tool-design reference.
- **receiving-code-review**: 4-tag false-positive taxonomy for dismissed suggestions — FP-ASSUMPTION / FP-CONVENTION / FP-ALREADY-HANDLED / FP-OUT-OF-SCOPE — with a push-back mapping column so dismissals cite structured reasoning. Integration section cross-maps to code-review action-routing tiers.
- **workflows:review**: per-agent `.review/NN-<agent>.md` artifact persistence for large reviews (8+ agents OR diff with more than 500 changed lines per `git diff --shortstat`). Missing-file recovery rule so a crashed specialist doesn't silently lose coverage at synthesis. `.review/` is transient scratch (gitignored), NOT a Protected Artifact.
- **repo-research-analyst**: iterative retrieval pattern. Cycle 1 uses broad terms to discover the repo's own vocabulary ("throttle" not "rate-limit"); cycle 2 refines with learned terminology; stop at 3+ relevant hits or 3 cycles.
- **frontend-design**: H1 2-3 line iron rule (ultra-wide containers like `max-w-5xl`, `clamp(3rem, 5vw, 5.5rem)` for fonts that scale down instead of wrapping). Mobile Collapse Mandate — asymmetric layouts above `md:` must collapse to `w-full px-4` below 768px, 44×44px minimum touch targets, no rotations or negative-margin overlaps on mobile. Bento-grid `grid-flow-dense` rule and hero scroll-filler ban added to `banned-ai-patterns.md`. Cross-card baseline alignment check added to `redesign-audit.md`.
- **md-docs**: Monorepo Context Loading section. Ancestors load at startup walking up, descendants lazy-load on subtree access, siblings never load — put shared conventions at the root, package-specific at each package root.
- **simplifying-code**: Step 6 pre-submit scope audit. Walk every changed line and ask "does the task explicitly require this?" If no, revert and list as a follow-up.
- **writing**: PR / MR Descriptions section cross-references the new reference file.
- **CLAUDE.md / AGENTS.md**: description must describe *when* to invoke the skill (trigger conditions), never *how* the skill proceeds step-by-step. Restating the body's procedure in the description causes Claude to follow the description and skip the skill content.
- Description refinements on `brainstorming`, `meta-prompting`, `planning`, `verify`, `agent-native-audit`, `deepen-plan`, and `workflows:compound` for sharper trigger fit.
- **distillery**: new `analyze-outcomes` command surfaces (skill, project) pairs whose negative rate exceeds the global average by more than 10pp. `model_baseline_prefixes` tracking in the skill manifest filters stale sessions from retired runtime models. `VAGUE_DESCRIPTION` added to the validator's anti-pattern taxonomy.
- Keep a Changelog reference updated from 1.0.0 to 1.1.0.

### Fixed

- `deployment-verification-agent`: Rollout Decision Thresholds and Feature-Flag Lifecycle promoted from H3 inside the Go/No-Go checklist template to H2 peers after it. Restored "Sample console verification" as the tail of section 6 Post-Deploy Monitoring — the earlier insertion had orphaned it.
- `workflows:review`: heading renamed "Per-phase artifact persistence" to "Per-agent artifact persistence" (files are per-agent; "phase" already means the command's numbered sections). "500 lines" threshold made measurable as "500 changed lines per `git diff --shortstat`".
- `code-review/references/deep-review.md`: merge-algorithm preamble clarifies that fingerprinting runs before the numbered rules, so the single-agent rule has a defined basis to operate on. Confidence boost applied once per group, not stacked across rules 6 and 7.
- `code-review/references/language-profiles.md`: dropped the false "same way as TS-003 or PY-002" precedent claim — sibling profiles have no numbered IDs, so the comparison didn't hold.
- `frontend-design/references/redesign-audit.md`: check #16 reformatted from 3-sentence declarative to single-question interrogative matching siblings 1 through 15.
- `announce` (internal): Edge profile moved to the Windows path. `post-thread.py` now defaults to draft-only.
- `README`: `rust-systems` row added to the skills table; `release.sh` now stages the README so documentation ships with each release.

## [2.56.0] - 2026-04-14

New `rust-systems` skill brings the language-skill roster to four (Python, Node, PHP, Rust). Covers edition-2024 Rust across CLI tools, axum services, and cargo workspaces, with discipline that targets the gaps LLMs consistently miss in Rust code: `unwrap` creep, unsafe without SAFETY comments, silent feature-flag degradation, and `tokio::sync::Mutex` where `RwLock` or `ArcSwap` would fit. Two focused references for clap-derive CLIs and axum service layout.

### Added

- **rust-systems skill**: new language skill for application-layer Rust (no embedded / no_std). Core SKILL.md covers cargo/clippy/rustfmt/nextest tooling, workspace layout with inward-only deps, `thiserror` in libraries / `anyhow` in binaries, ownership signatures, tokio patterns (JoinSet, CancellationToken, bounded mpsc, Semaphore, RwLock for read-heavy state), unsafe discipline with SAFETY comments and miri, production resilience (fail-fast config, `/health` vs `/ready`, graceful shutdown, backon retries, connection pools), tracing+metrics observability. Feature gates must error on runtime mismatch, never silently degrade.
- **rust-systems/references/cli-tools.md**: clap derive patterns, layered `LowArgs → HiArgs` parsing for non-trivial CLIs (ripgrep-style), config layering (defaults → XDG → project → env → flags), stderr logging with TTY-aware progress, `assert_cmd` CLI testing.
- **rust-systems/references/axum-service.md**: project layout (routes → services → repos), AppState with `Arc` inside, `IntoResponse` error envelope from `thiserror`, `ValidatedJson` extractor, tower middleware order, `tokio::signal` graceful shutdown, `sqlx::query_as!` compile-time macros with offline `.sqlx/` cache, `tower::ServiceExt::oneshot` for router tests.
- **rust-systems trigger pattern**: added to `hooks/skill-patterns.sh` (Tier 2) with 18 regression fixtures at precision 1.0 / recall 1.0. Handles `cargo`, `clippy`, `tokio`, `axum`, `clap`, `async rust`, `JoinSet`, and `Cargo.toml` triggers without misfiring on Python/Node/PHP/bash/Terraform prompts.

### Changed

- **code-review**: merged Maintainability and Readability subsections under "What to Check" — three of five Maintainability items (naming, function length, nesting depth) duplicated the Readability list. Consolidated section preserves Readability's measurable thresholds ("3 levels of indentation", "forces scrolling") and keeps Maintainability-unique items (God classes / SRP, leaky abstractions).
- **code-review**: test-file exclusion added to Review Mode Selection signals. Lines/files/directory counts now exclude `tests/`, `__tests__/`, `*.test.*`, `*.spec.*`, `*_test.*` paths so boilerplate-heavy test expansions don't falsely trigger deep review. Both totals reported for transparency.
- **code-review/references/false-positive-suppression.md**: clarified the vague "already addressed in the diff" example under Readability-aiding redundancy. Now explicit: author fixed it in a later commit within the same diff, flagged it in their own PR comments, or a prior reviewer resolved it.

## [2.55.1] - 2026-04-12

Model tier review and full plugin audit. Haiku was assigned to review tasks that require reasoning about absence (untested paths, missing error handling, breaking API changes), producing shallow or missed findings. Upgraded all deep-review specialists and key agents to appropriate tiers. Cleaned up dead references, dangling cross-refs, and redundant content.

### Changed

- **deep-review specialists**: all 6 former-haiku slots (testing, maintainability, performance, reliability, cloud-infra, api-contract) upgraded to opus. These reason about what's absent in code, not pattern-match what's present.
- **pr-comment-resolver**: haiku → opus. Implementing PR review comments is authoring-level work.
- **accessibility-tester**: haiku → sonnet, description updated to WCAG 2.1/2.2 (2.2 current since Oct 2023).
- **infrastructure-engineer**: added `model: sonnet` (CI/CD, Docker, tracing, incident triage).
- **deployment-verification-agent**: added `model: sonnet` (runbooks with SQL queries and rollback procedures).
- **php-laravel**: replaced ambiguous "Fat models, thin controllers" with clear boundary -- models own domain behavior, services own orchestration.
- **react-frontend**: React Compiler install instruction updated to framework-first config path (Next.js `reactCompiler: true`).
- **python-services**: added `uv run ty check .` to Verify section -- ty was listed as a tool but never enforced.
- **repo-research-analyst**: replaced off-stack Ruby ast-grep example with PHP.
- **code-simplicity-reviewer**: removed "Great!" filler from invocation example.
- **orchestrating-swarms**: trimmed redundant "Best Practices" section (3 items already covered by Dispatch Discipline and QA retry loop) down to 2 unique "Integration Rules" (post-integration verification, spawned-session behavior).
- **verification-before-completion**: collapsed 6-row Rationalization Prevention table into a 2-sentence paragraph -- the Gate Function already covers these rules.
- **workflows:review**: removed ~90 lines of generic "Ultra-Thinking" checklists (stakeholder perspectives, scenario exploration, multi-angle reviews) that duplicated specialist agent coverage. Sections renumbered 1-4.
- **update-plugin.sh**: modernized to use `claude` CLI commands.

### Fixed

- 5 dead references to `agent-native-reviewer` (removed in v2.55.0) cleaned up across `workflows/review.md`, `setup.md`, `README.md`, and `orchestrating-swarms/agent-types.md`. The dispatch at review.md:92 would error at runtime.
- Brainstorming skill: dangling "see Question Clustering below" forward reference -- no such section existed. Rule folded inline.

## [2.55.0] - 2026-04-10

Cross-repo sync (14 external references) + full plugin audit + command delegation cleanup. Agent count: 20 → 19 (deployment-engineer + devops-engineer merged into infrastructure-engineer).

### Added

- **tools** restriction added to 5 analysis-only agents (`bug-reproduction-validator`, `spec-flow-analyzer`, `repo-research-analyst`, `best-practices-researcher`, `code-simplicity-reviewer`) — all are explicitly read-only but previously inherited full write access.
- **model: sonnet** declared on `design-iterator`, `figma-design-sync`, `repo-research-analyst`, `spec-flow-analyzer` — mechanical or low-judgment work where sonnet is sufficient and cheaper than opus.
- **Agent model tier policy**: `model: opus` declared on `architecture-strategist`, `kieran-reviewer`, `database-guardian`, `cloud-architect`, `performance-oracle`, and `security-sentinel` to guarantee high-judgment agents use Opus regardless of the calling session's default model.
- **Postgresql trigger regression fixtures** (5 new cases) covering the actual misfire samples from session harvesting (letter-review, plugin-audit, PHP-extension-upgrade contexts).

### Changed — skills

- **writing**: Named-tag lookup table with severity suffixes (`+H`, `+S`) — `[STACCATO]`, `[FALSE-AGENCY]`, `[BINARY-CONTRAST]`, `[ELEGANT-VAR]`, `[EM-DASH]`, `[META-COMMENTARY]`, `[INFLATED]`, `[VAGUE-DECLARATIVE]`. Per-tag fix action table and structured AUDIT/CORRECTED TEXT/CHANGELOG output format. Cross-referenced the "Kill on Sight" and "Long-form audit workflow" vocabulary sections (short-form vs long-form use). Sourced from `ai-writing-audit` and `stop-slop`.
- **orchestrating-swarms**: Preset Team Compositions table extracted to `references/team-compositions.md` (Review, Debug, Feature, Fullstack, Migration, Security, Research). Cardinal `subagent_type` rule added calling out read-only agents silently failing on writes. Sourced from agents repo.
- **frontend-design**: Mandatory Interactive States section (loading/empty/error/tactile press), Performance Guardrails (grain filter on scrolling containers, `transform`/`opacity` only, z-index restraint, perpetual animation isolation), and RSC/Client Component boundaries extracted to `references/rsc-client-boundaries.md` (`useMotionValue` vs `useState`, `'use client'` leaf isolation, `staggerChildren` parent-child colocation). Typography and Backgrounds bullets split from ~200-word run-on paragraphs into sub-bulleted rules. Sourced from `taste-skill`.
- **brainstorming**: Phase 3b inline spec self-review checklist (placeholder scan, internal consistency, scope containment, ambiguity sweep, assumption validation, non-goals) before handing off to planning. Sourced from `superpowers`.
- **code-review**: Merge algorithm for multi-agent output moved to `references/deep-review.md` (same-line-same-issue = merge higher severity, same-line-different-issue = co-located, conflicting severity = take higher, conflicting recommendations = `NEEDS DECISION`, convergence = boost confidence). Findings use `CR-001` IDs (previously the output template used `**1.**` which contradicted the CR-numbering instruction — fixed). Review Process step 1 (Context) split from a dense 5-sentence paragraph into sub-bulleted actions (Scope Drift Check, intent read, existing-discussion fetch, automated gates). Sourced from gstack, agents repo.
- **verification-before-completion**: Structured Completion Report Format with `DONE/DONE_WITH_CONCERNS/BLOCKED/NEEDS_CONTEXT` status, mandatory `Things I didn't touch (intentionally)` section for visible scope discipline, and verification evidence block. Rationalization table collapsed from 14 rows to 6 by consolidating near-identical entries. Sourced from gstack, google-agent-skills.
- **simplifying-code**: Orchestrator Mode section with canonical `Resolved scope` fenced block passed verbatim to every chained sub-skill, preventing scope drift and double work. Sourced from `agent-skills/code-polish`.
- **receiving-code-review**: Batched clarification pattern for ambiguous critical-path findings (up to 4 items in one `AskUserQuestion` call with `Valid / False positive / Defer` options); documents fallback behavior when `AskUserQuestion` tool isn't available. Sourced from `agent-skills/coderabbit`.
- **debugging**: STATUS line gained `NEEDS_CONTEXT` option to match the canonical 4-status taxonomy used by `orchestrating-swarms` and `verification-before-completion`. Verify section corrected from "all five fields" to "all seven fields" (Debug Report has 7 fields: SYMPTOM, ROOT CAUSE, FIX, EVIDENCE, REGRESSION, RELATED, STATUS). Anti-patterns table collapsed from 12 rows to 6 by merging duplicate "guessing / shotgun / fixing symptoms" rationalizations.
- **planning**: Execution Posture Signals clarified — **tests-after is the default**, test-first/characterization-first/external-delegate are opt-in annotations. Added the per-section enhancement format and Enhancement Summary block to Plan Deepening (content moved from the `/deepen-plan` command). Removed redundant Anti-Patterns table — content was already enforced by Plan Quality Rules and Phase Sizing Rules.
- **postgresql**: Removed duplicated slow-query and table-bloat SQL from Query Optimization section (the full versions already exist in Detection Queries below). Trigger pattern tightened to require SQL/database context anchors — previously matched bare keywords like `trigger`, `function`, `extension`, causing **90% misfire rate** (9/10 injections) on letter-review and plugin-audit sessions.
- **debugging**: Trigger pattern tightened to require the word "debug" within 30 chars of a failure indicator (error/bug/fail/crash/issue/broken/problem/trace/stack/regression), avoiding matches on "debug mode" or "debug output" in non-bug contexts.
- **reflect**: Memory path placeholder `~/.claude/projects/.../memory/` replaced with concrete `<project-slug>` placeholder explanation.
- **refine-prompt**: Removed duplicate "Never invent" rule (was stated in both Rules and Constraints sections).
- **md-docs**: Writing Style section rewritten — replaced vague meta-instructions ("terse", "accurate") with measurable criteria (lead-with-answer, verify-every-command, no-passive-voice in directives, headings every ~20 lines).
- **php-laravel**: Converted cross-skill markdown link `[writing-tests](../writing-tests/SKILL.md)` to prose reference matching the plugin's cross-skill convention.

### Changed — agents

- **Merged `deployment-engineer` + `devops-engineer` → `infrastructure-engineer`**. The split between CI/CD and containerization/observability created routing ambiguity — both agents were called in similar contexts and contained cross-reference preambles pointing at the other. Merged agent covers CI/CD pipelines, deployment strategies (blue-green, canary, rolling, feature flags), Docker and containerization, observability (metrics/logs/traces), and incident management. Scope boundary defers database-migration verification to `deployment-verification-agent`, cloud architecture to `cloud-architect`, and IaC to the `terraform` skill.
- **security-sentinel**: Security Test Coverage Checklist extracted to `references/security-test-coverage.md` as an explicit audit deliverable — auth edge cases (`alg=none`, wrong issuer), IDOR, mass assignment, TOCTOU, file upload magic-byte validation, session cookie flags, business-logic bypass. Each finding requires CVSS 3.1, exploit proof, and copy-paste-ready remediation. Promoted to `model: opus`. Sourced from `agency-agents`.
- **bug-reproduction-validator**: Description clarified as "reproduce-first stage" with explicit handoff to `debugging` skill for fixing.
- **deployment-verification-agent**: Description sharpened to distinguish from `database-guardian` — this agent builds the deploy *runbook*; database-guardian reviews the migration *code*. Run database-guardian first.
- **best-practices-researcher** and **repo-research-analyst**: Descriptions trimmed to remove bloated cross-reference preambles.

### Changed — commands

- **workflows:review**: Always-on red-team adversarial pass after parallel specialists return, targeting cross-category compound vulnerabilities, happy-path assumptions, silent failures in auth/payment code, and trust boundary violations. Severity taxonomy aligned with `code-review` skill's 4-level scale (Critical / Important / Medium / Minor) — previously used a P1/P2/P3 scale with "Nice-to-Have" that didn't match the skill's merge algorithm. Sourced from gstack.
- **workflows:work**: Subagent Execution Discipline section replaced with a one-line delegation to `orchestrating-swarms` skill (which owns the fresh-agent-per-task rule, two-stage review gate, model-selection-by-complexity table, and four-status reporting protocol). Phase 2 Test Continuously explicitly sets tests-after as the default for new features; test-first is opt-in via the `planning` skill's posture signal. Command drops from ~4300 to 3774 tokens.
- **workflows:plan**: Idea Refinement (Phase 0) trimmed by ~65 lines — delegation to `brainstorming` skill for the interview protocol. Step 2 (Plan Structure & Naming) consolidated from three checklists to the orchestration essentials. Command drops from ~4100 to 3234 tokens.
- **workflows:brainstorm**: Further thinned to defer Phase 2-3 details to `brainstorming` skill; removed duplicated "NEVER CODE" line (the skill's Hard Gate owns this).
- **workflows:compound**: Phase 2 changed from prose instruction ("Invoke the compound-docs skill") to an explicit `Skill({ skill: "compound-docs", args: ... })` tool call, making the delegation actionable rather than advisory.
- **deepen-plan**: Step 4 learnings-discovery replaced with a single `learnings-researcher` agent dispatch (removed ~90 lines of inline filesystem traversal, frontmatter filtering, and example prompts). Step 8 enhancement format replaced with a pointer to `planning` skill's Plan Deepening section. Command drops from ~3900 to 3006 tokens.
- **agent-native-audit**: Collapsed 8 per-principle sub-agent prompts (~230 lines) into a single parameterized template that references the `agent-native-architecture` skill for principle definitions. Command drops from ~2500 to 1637 tokens.
- **adr**: Added explicit Argument handling section covering empty, `list`, short title, longer topic, and `deprecate <NNNN>` cases.

### Removed

- **deployment-engineer** agent and **devops-engineer** agent — consolidated into `infrastructure-engineer`.

## [2.53.2] - 2026-04-08

### Changed

- **orchestrating-swarms**: Task description template with file ownership and interface contracts. Controller-curates-context principle. Spawned-session behavior for subagent skills. Circuit-breaker, bulkhead isolation, and saga compensation for mid-pipeline failures.
- **code-review**: Fix-First heuristic (AUTO-FIX vs ASK classification table). Red-team adversarial pass (silent failures, trust exploits, edge cases). Comment labels for inline review feedback. LLM-specific false-positive rule. Numbered findings for easier referencing.
- **security-sentinel agent**: Threat Modeling Mode with STRIDE analysis, risk matrix, and focus paths. Referenced from planning, code-review, and brainstorming.
- **agent-native-architecture**: MCP tool annotations, structured output with actionable errors, transport selection matrix, pagination contract, multi-server tool naming.
- **planning**: Session continuity protocol. Threat modeling reference for security-sensitive designs.
- **git-worktree**: Branch completion ceremony (4-option flow with discard confirmation). Change Summary with "DIDN'T TOUCH" section.
- **brainstorming**: Seven ideation lenses, "Not Doing" list, assumptions-with-validation format. Threat modeling reference.
- **writing**: Wh- sentence openers, Narrator-from-a-distance, lazy extremes, meta-commentary tells.
- **writing-tests**: Three-source QA inventory (requirements, features, claims).
- **simplifying-code**: Chesterton's Fence in read-first step. Over-simplification failure modes. Function length threshold tightened to >20 lines.
- **frontend-design**: Utility copy discipline for product UI vs marketing copy.
- **debugging**: RELATED and STATUS fields in debug report. CI failure investigation pattern in specialized-patterns.md.
- **verification-before-completion**: Pre-verification dirty-tree check. Don't-trust-implementer rule for delegated work.
- **reflect**: Operational learnings step with 5-minute filter.
- **postgresql**: Migration Safety section with expand-contract pattern, batch UPDATE with FOR UPDATE SKIP LOCKED, dangerous operations guide.
- **nodejs-backend**: Fail-fast env validation, health endpoints (shallow vs deep), migration patterns, third-party response validation, pre-ship endpoint checklist.
- **php-laravel**: Fail-fast config validation, health endpoints, migration discipline, third-party response validation.
- **python-services**: Fail-fast config validation via Pydantic BaseSettings, health endpoints, migration patterns, uv upgrade workflow, third-party response validation.

## [2.53.1] - 2026-04-08

### Added

- **inject-skills hook**: Project-context filtering for skill injection. Detects project type from marker files (composer.json, package.json, pyproject.toml, Cargo.toml, go.mod, *.tf) and suppresses domain skills that don't match the project stack. Monorepo-safe (multiple types detected simultaneously). No filtering when no markers found.
- **distillery**: `analyze-outcomes` command correlates skill injection with session signal per project. Surfaces (skill, project) pairs where negative rate exceeds the skill's global average by >10 percentage points.
- **generate-skill-hooks.sh**: `PROJECT_TYPE_MAP` for auto-generating `SKILL_PROJECT_TYPES` entries during pattern regeneration.

## [2.53.0] - 2026-04-05

### Added

- **code-review**: Three new deep-review specialists -- api-contract (breaking changes, versioning, error consistency), data-migration (reversibility, lock duration, backfill strategy), red-team (adversarial second pass finding integration gaps). Change sizing guidance with 4 splitting strategies. Readability as explicit review dimension.
- **writing**: Two-phase audit workflow (detect all tells first, then rewrite) with citation auditing tags ([OAICITE], [LINK-ROT], [ISBN-DOI-FAIL], [REF-BUG]). New `references/audit-workflow.md`.
- **frontend-design**: Expanded AI slop detection to 6 prioritized patterns plus 15 additional tells. Motion patterns extracted to `references/motion-patterns.md` with spring physics values, stagger recipes, and GPU-safe animation rules.
- **orchestrating-swarms**: Cold-start agent isolation, label randomization for judge panels, convergence detection. Two-stage review gate for subagent outputs. Resilience patterns (cascade prevention, recovery strategy, post-failure synthesis).
- **verification-before-completion**: Three new rationalization table entries and red flags list for detecting skipped verification.
- **planning**: Vertical slicing taxonomy, checkpoint system (verify every 2-3 tasks), strengthened no-placeholders rule.
- **writing-tests**: Prove-It Pattern for bug fixes (reproduce bug with failing test before fixing). Test pyramid level definitions.
- **md-docs**: Context hierarchy for CLAUDE.md files (Rules > Tech stack > Commands > Conventions > Boundaries).
- **python-services**: Sync vs async decision guide. API design patterns with FastAPI idioms.
- **php-laravel**: API design patterns with Laravel idioms (API Resources as contracts, Form Requests for boundary validation).
- **nodejs-backend**: API design patterns with TypeScript/Express idioms (Zod schemas, consistent error envelopes). Expanded Express trigger to cover endpoints/routes/APIs.
- **react-frontend**: Tailwind integration section with cross-reference to tailwind-css skill. JSX class sorting with `useSortedClasses` config.
- **agent-native-architecture**: Hooks patterns reference (`references/hooks-patterns.md`) covering agent-context hook limitations, decision control, MCP matchers, async hooks, two-tier config.
- **database-guardian** agent: Migration risk patterns (reversibility, data loss, lock duration, backfill, multi-phase safety).
- **security-sentinel** agent: Adversarial pass section (happy-path assumptions, silent failures, trust boundary violations, cross-category compound issues).
- **spec-flow-analyzer** agent: 12-dimension scenario coverage sweep (happy path through state transitions).
- **performance-oracle** agent: 8 grep-able detection patterns with thresholds (N+1 queries, missing indexes, O(n^2), bundle size, rendering waterfalls, lazy loading, pagination, blocking sync).
- **deployment-verification-agent**: SEV1-SEV4 severity matrix with response times and 4-step rollback runbook template.
- **architecture-strategist** agent: 6 structured review dimensions with dimension assessment in output format.
- **workflows:work** command: Subagent execution discipline (fresh agent per task, two-stage review, model selection by complexity, status protocol).
- **workflows:compound** command: Post-mortem structure (5 Whys, impact quantification, timeline, action items with owners, blameless framing).
- **workflows:review** command: Scope resolution fallback chain, two-stage review gate, scope drift check.
- **verify** command: 4 new verification phases (performance, accessibility, infrastructure, documentation) with applicability detection.
- **ideate** command: 7 ideation lenses for divergent thinking (Inversion, Constraint removal, Audience shift, Time shift, Scale shift, Simplification, Combination).
- 20 new trigger regression test cases covering expanded content areas.
- 6 regex pattern expansions (md-docs, nodejs-backend, planning, writing, agent-native-architecture, frontend-design).

### Changed

- **code-review**: Removed Fix-First Heuristic and auto-fix instructions -- skill is diagnostic only, identifies and reports issues without fixing.
- **frontend-design**: Condensed motion bullet in SKILL.md, moved detailed rules to references/motion-patterns.md. Replaced inline "Additional tells" with reference link.
- **orchestrating-swarms**: Removed duplicate "fresh agent" and "provide full context" directives that appeared in both Dispatch Discipline and later sections.
- **verification-before-completion**: Removed duplicate "zero issues found" row from rationalization table (already covered in Rules section).
- **agent-native-architecture**: Rephrased "Primitives not Workflows" to positive form.
- **nodejs-backend**: Added positive alternative to sync method ban (use fs.promises/streams).
- **php-laravel**: Clarified "don't explain" rule to specifically target generated code comments.
- **python-services**: Discipline section references Verify section instead of restating commands.
- **planning**: Removed redundant anti-pattern row (covered by Phase Sizing Rules).
- **tailwind-css**: Removed out-of-scope React 19 forwardRef note (belongs in react-frontend).
- **database-guardian** agent: Fixed duplicate section numbering in Phase 1.

## [2.52.1] - 2026-04-04

### Changed

- **planning**: Vertical slicing principle in anti-patterns table and verify checklist. Task duration heuristic (>2h = split) in phase sizing rules.
- **frontend-design**: Four new banned AI patterns -- colored icon circles, left-border accent cards, cookie-cutter section rhythm, bubbly rounded containers. Fixed stock imagery alternative.
- **writing-tests**: DAMP over DRY principle and test pyramid ratios (~80/15/5) as separate subsections. DAMP caveat added to "When Stuck" table.
- **debugging**: Reduce step (1c) with stopping criterion -- strip to minimal failing case before investigating.
- **nodejs-backend**: Contract-first principle with named artifact (route schemas). Reconciled with existing OpenAPI generation guidance.
- **verification-before-completion**: Removed duplicate empty Integration heading.

## [2.52.0] - 2026-04-02

### Added

- **debugging**: Three new reference docs -- `defense-in-depth.md` (4-layer validation pattern), `competing-hypotheses.md` (full ACH methodology with 6 failure categories and evidence scoring), `root-cause-tracing.md` (backward call-chain tracing with test pollution detection).
- **code-review**: `reliability-patterns.md` reference -- error handling, timeouts, retries, circuit breakers, resource cleanup, queue resilience. New reliability agent in deep-review specialist roster.
- **code-review**: `false-positive-suppression.md` reference -- 8 suppression categories with override rules.
- **frontend-design**: `redesign-audit.md` reference -- 60+ checks across typography, color, layout, interactivity, content, and component patterns for existing UI improvement.
- **writing**: Quality Gate section with 5-dimension scoring rubric (Directness, Rhythm, Trust, Authenticity, Density) and 8-item quick audit checklist.
- **writing/phrases.md**: Three structural anti-pattern categories (Dramatic Fragmentation, Formulaic Constructions, Narrator-from-a-Distance).
- **writing-tests**: Four new rationalization table entries (hard-to-test code, understanding-first delay, prototype excuse, deadline pressure).
- **postgresql**: Expanded anti-patterns table (7 patterns) with 3 detection queries (slow queries, table bloat, unused indexes).
- **simplifying-code**: Two AI slop patterns (redundant error wrapping, verbose stdlib reimplementations).
- **verification-before-completion**: `system-wide-test-check.md` reference -- blast-radius verification for task completion.
- **resolve-pr** command -- merged `resolve-pr-parallel` + `resolve-pr-feedback` into single smart command with cluster analysis (3+ comments) and parallel agent dispatch.
- **deep-review**: `cloud-infra` specialist agent dispatched conditionally when diff touches infrastructure files.
- **receiving-code-review**: Headless mode extracted to `references/headless-mode.md`.
- **commands/references**: Shared `adr-templates.md` (extracted from adr command) and `agent-browser-cli.md` (shared between test-browser and feature-video).

### Changed

- **agent-native-audit**: Absorbed `agent-native-reviewer` agent as `quick` mode. One component instead of two.
- **pr-comment-resolver**: Model set to haiku (mechanical work).
- **git-history-analyzer**: Model set to haiku (git read operations).
- **accessibility-tester**: Model set to haiku (WCAG pattern-matching). Added cross-reference from frontend-design.
- **devops-engineer**: Added `autoApprove: read` for consistency with other analysis agents.
- **meta-prompting**: Description trimmed to under 80 tokens while preserving all 15 slash command triggers.
- **code-review**: Description trimmed. FP suppression consolidated into reference file. "Also suppress" list moved from main body to reference.
- **verification-before-completion**: Description trimmed with "Use when" trigger.
- **planning**: Clarified `.plan/` overwrite scope (between features vs within multi-phase). Strengthened no-placeholder rule.
- **brainstorming**: Phases 4-5 trimmed to delegate orchestration to `workflows:brainstorm` command.
- **orchestrating-swarms**: Best Practices trimmed from 7 to 4 items (removed generic agent hygiene).
- **writing**: Self-Check trimmed from 11 to 5 items (merged overlap with Quality Gate).
- **workflows:work**: System-Wide Test Check extracted to verification-before-completion reference.
- **workflows:compound**: Description differentiated from compound-docs skill.
- **adr**: Templates extracted to `commands/references/adr-templates.md` (-109 lines).
- **test-browser**: CLI reference extracted to shared file (-31 lines).
- **figma-design-sync**: Phase 2 trimmed to reference Phase 1 results (-30 lines).
- **performance-oracle**: Removed redundant "Code Review Approach" section.
- **lfg**: Added empty-arguments guard.
- **changelog**: Added explicit output destination instruction.
- **compound-docs**: "BLOCK until valid" replaced with actionable "fix and re-run" fallback.

### Removed

- **agent-native-reviewer** agent -- absorbed into agent-native-audit command.
- **resolve-pr-parallel** command -- merged into resolve-pr.
- **resolve-pr-feedback** command -- merged into resolve-pr.

## [2.51.0] - 2026-03-31

### Added

- **distiller**: `validate-plugin` command -- deterministic validation of all plugin components (frontmatter gates, anti-pattern detection, reference integrity, README/hook count accuracy). Replaces manual AI checks in `/audit-plugin` Phase 1.
- **distiller**: `test-triggers` command -- regex trigger regression suite with JSONL fixture files per skill (29 skills, 179 test cases). Release gate in `release.sh`.
- **distiller**: `test-semantic` command -- Claude-cli injection tests (Sonnet) that verify skills trigger organically from natural language prompts via `TEST_INJECTION_LOG` env var.
- **distiller**: Skill change manifest (`distillery/.skill-versions.json`) -- tracks SHA256 hashes of SKILL.md content and trigger patterns per skill. Enables staleness filtering in analysis commands.
- **planning**: Execution posture signals (test-first, characterization-first, external-delegate) for phase-level implementation sequencing.
- **planning**: Plan deepening section for targeted strengthening of existing plans.
- **frontend-design**: Design variance parameters (DESIGN_VARIANCE, MOTION_INTENSITY, VISUAL_DENSITY) to prevent aesthetic convergence.
- **frontend-design**: `references/banned-ai-patterns.md` -- comprehensive banned AI design patterns (layout, color, typography, decoration, interaction, content).
- **hooks**: `TEST_INJECTION_LOG` env var in `inject-skills.sh` for test observability (zero overhead in normal operation).

### Changed

- **audit-plugin**: Phase 1 now runs `validate-plugin` + `test-triggers` deterministically before AI analysis. Phase 2 adds `analyze-misfires` and `diagnose-negatives` as trigger coverage checks. Phase 7 runs full test suite (pytest + triggers + semantic).
- **sync-from-repos**: Phase 1 launches `harvest-sessions` in background. Phase 6 runs `discover-signals` for negative pattern discovery. Body budget threshold raised to 4K tokens for skills.
- **release.sh**: Pre-commit gates added -- `test-triggers` (blocking), `test-semantic` (warning), `generate-manifest.py` (auto-updates manifest).
- **harvest-sessions/analyze-misfires/diagnose-negatives**: Stale data filtering by default (exclude examples from before skill/pattern was last changed). `--include-stale` flag to override.

### Removed

- **distiller**: `ab_eval()`, `test_skill()`, `DEFAULT_TEST_MODELS` -- stale OpenRouter-dependent A/B testing code, CLI commands, and tests.

## [2.50.0] - 2026-03-29

### Added

- **code-review**: Deep multi-agent review mode -- auto-detects complex diffs (3+ signals) and dispatches parallel specialist agents (correctness, security, testing, maintainability, performance). New `references/deep-review.md` with agent prompt templates, merge algorithm, and model selection.
- **code-review**: Confidence rubric (0.0-1.0 scoring) with false-positive suppression categories. Intent verification in review process.
- **receiving-code-review**: Headless mode for programmatic triage (AUTO-FIX / AUTO-DECLINE / ESCALATE classification). Prior-feedback check on re-reviews.
- **document-review**: 5 conditional review lenses (Product, Design, Security, Scope guardian, Adversarial) activated by document signals.
- **orchestrating-swarms**: Handoff protocol for structured agent-to-agent transfers. Coordination models comparison (stateless vs stateful). Reference map table.
- **frontend-design**: 6 banned AI design patterns (purple gradient, centered-cards layout, uniform corners, accent lines, emoji headers, generic placeholder copy).
- **git-worktree**: Environment detection (existing worktree, sandbox, bare repo).
- **planning**: Test discovery phase for existing projects. Verify section with 6 measurable criteria.
- **verification-before-completion**: 3 new rationalization entries (just this once, CI will catch it, zero issues on first pass).
- **Verify sections** added to 9 skills: receiving-code-review, simplifying-code, tailwind-css, md-docs, meta-prompting, refine-prompt, debugging, react-frontend, writing-tests (renamed from Test Quality Checklist). Also nodejs-backend and python-services.
- **brainstorming**: Success criteria section.
- **writing**: Short-form/long-form mode labels for self-check. Two new self-check items (contrast structures, vague declaratives).

### Changed

- **agent-native-architecture**: Converted non-standard XML tags (`<intake>`, `<routing>`, `<architecture_checklist>`) to standard markdown. Added H1 heading. Removed duplicate References section. Linked orphan `quick-start.md`.
- **orchestrating-swarms**: Removed duplicate Best Practices rules 1 and 8 (covered by Verify and Dispatch Discipline).
- **php-laravel**: Removed duplicate Anti-Patterns section (4/5 entries already covered; moved unique entry to Discipline).
- **postgresql**: Removed 10 duplicate Anti-Patterns entries (kept 1 genuinely new).
- **linux-bash-scripting**: Compressed Linux-Specific section to non-obvious items only (GNU coreutils differences, timeout).
- **compound-docs**: Replaced verbose Integration Points block with slim Integration section.
- **reflect**: Replaced vague "auto memory system" with concrete file path. Folded Proactive Trigger into Process step.
- **document-review**: Renumbered steps 1-8 sequentially (was 1, 2, 2b, 3, 4, 5, 5b, 6). Broadened description to cover specs, ADRs, and any doc.
- **workflows:plan**: Extracted issue formatting and creation logic to `references/issue-formatting.md` (was over 4K token budget). Removed hardcoded year. Fixed non-standard namespaced agent call.
- **resolve-todo-parallel**: Removed dead dependency diagram code.
- **lfg**: Normalized namespaced command references to short names. Added auto-detect note for deepen-plan.
- **agent-native-audit**: Added argument anchor at top of body.
- **deployment-verification-agent**: Replaced emoji section headers with text. Fixed stale "Data Migration Expert" reference to `database-guardian`. Made examples stack-neutral.
- **devops-engineer**: Removed incorrect `autoApprove: read` (agent writes Dockerfiles).
- **figma-design-sync**: Removed `autoApprove: read` (Phase 2 writes code).
- **kieran-reviewer**: Sharpened description with persona-driven focus. Added code-review cross-reference.
- **pr-comment-resolver**: Removed emoji from output template.
- **bug-reproduction-validator**: Replaced "add temporary logging" with "inspect existing logs" (permission-safe).
- **security-sentinel**, **learnings-researcher**: Added OWASP/schema fallback notes for cross-reference paths.
- **Cross-references**: Added bidirectional Integration entries across simplifying-code, verification-before-completion, debugging, code-review, and 4 description-level pointers.
- **Description triggers**: Added missing synonyms to verification-before-completion, nodejs-backend, code-review, meta-prompting, simplifying-code, debugging, compound-docs, devops-engineer.

### Removed

- All Rails/Ruby-specific examples replaced with TypeScript/PHP/generic equivalents across 18 files (agents, commands, skills). Plugin no longer assumes a Rails stack.

## [2.49.4] - 2026-03-27

### Fixed

- **agent-native-audit**: removed Step 1 skill invocation that deadlocked on interactive `<intake>` menu; command now references `agent-native-architecture` skill as canonical source
- **feature-video**: replaced hardcoded personal rclone remote (`r2:kieran-claude/`) with configurable `$R2_REMOTE`, `$R2_BUCKET`, `$PUBLIC_BASE_URL` env vars; upload step aborts gracefully if rclone not configured
- **resolve-todo-parallel**: rewrote garbled Step 2 run-on sentence into structured imperative bullets
- **deepen-plan**: consolidated duplicate skill/agent discovery (was in Steps 2 and 5) into single upfront step; added soft cap of 10 agents per category; removed unbounded "40+ parallel agents is fine" directives; net -118 lines

## [2.49.3] - 2026-03-27

### Changed

- **Deep audit: 35 findings fixed, 2 agent consolidations, net -381 lines**
- Merged `data-integrity-guardian` + `data-migration-expert` into `database-guardian` (two-phase: schema review, then migration validation)
- Absorbed `design-implementation-reviewer` into `figma-design-sync` as Phase 1 (review-only with stop condition)
- Renamed `resolve_todo_parallel` to `resolve-todo-parallel` (naming convention compliance)
- Fixed wrong agent namespace in workflows:plan (`workflow:` -> `review:spec-flow-analyzer`)
- Fixed wrong maintainer name in report-bug command
- Removed stale `resolve-pr-parallel` hook pattern (deleted in v2.49.1)
- Removed dead `schema.yaml` link in compound-docs, dead `/research` ref in compound, dead rclone skill ref in feature-video
- Removed inert `paths:` frontmatter from 8 skills, `allowed-tools`/`preconditions` from compound-docs
- Removed stale "Task tool" references from performance-oracle and spec-flow-analyzer agents
- Resolved brainstorming directive contradiction (one-at-a-time vs clustering)
- Replaced vague "elegant" directive in nodejs-backend, php-laravel, python-services with measurable criteria
- Trimmed deepen-plan (~64 lines), workflows:work (~123 lines), changelog directives (21 -> 10 rules)
- Removed XML wrapper tags from workflows:review and workflows:work
- Fixed phase numbering gap in workflows:review (Phase 3,4 -> Phase 1,2)
- Removed emoji directive from workflows:plan, hardcoded year from brainstorm/deepen-plan
- Added verify sections to orchestrating-swarms, terraform, pinescript, git-worktree
- Added constraints to refine-prompt, success criteria to document-review
- Moved oversized content to references/: frontend-design, debugging, brainstorming
- Clarified descriptions: repo-research-analyst, deployment-verification-agent
- Fixed bare backtick skill refs in php-laravel, react-frontend
- Removed duplicate `frontend-design` reference in design-iterator

## [2.49.2] - 2026-03-27

### Changed

- **Token budget optimization**: debugging skill 3089t -> 2832t (-257t, environment diagnostics + intermittent issues + postmortem moved to `references/specialized-patterns.md`); planning skill 2557t -> 2195t (-362t, context management + error protocol + iterative refinement + 5-question check moved to `references/operational-patterns.md`)
- **Command argument fixes**: `$ARGUMENTS` interpolation added to report-bug, workflows:compound, workflows:document-release (3 more commands that had argument-hint but never used the value)

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
