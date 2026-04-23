---
name: ia-code-review
description: >-
  Structured code reviews with severity-ranked findings and deep multi-agent
  mode. Use when performing a code review, auditing code quality, or critiquing
  PRs, MRs, or diffs.
---

# Code Review

## Two-Stage Review

**Stage 1 -- Spec compliance** (do this FIRST): verify the changes implement what was intended. Check against the PR description, issue, or task spec. Identify missing requirements, unnecessary additions, and interpretation gaps. If the implementation is wrong, stop here -- reviewing code quality on the wrong feature wastes effort.

**Stage 2 -- Code quality**: only after Stage 1 passes, review for correctness, maintainability, security, and performance.

## Scope Resolution

**Pre-flight**: verify `git rev-parse --git-dir` exists before anything else. If not in a git repo, ask for explicit file paths.

When no specific files are given, resolve scope via this fallback chain:
1. User-specified files/directories (explicit request)
2. Session-modified files (`git diff --name-only` for unstaged + staged)
3. All uncommitted files (`git diff --name-only HEAD`)
4. Untracked files (`git ls-files --others --exclude-standard`) -- new files are often most review-worthy
5. **Zero files → stop.** Ask what to review.

Exclude: lockfiles, minified/bundled output, vendored/generated code.

## Review Mode Selection

**Run this BEFORE reading the full diff.** Use metadata only (`git diff --stat`, file list from scope resolution) to count signals. Reading the diff first creates analysis momentum that bypasses mode selection.

| Signal | Threshold | Detect from |
|--------|-----------|-------------|
| Lines changed | >300 | `git diff --stat` insertion + deletion totals, **excluding test files** |
| Files touched | >8 | File count from scope resolution, **excluding test files** |
| Modules/directories spanned | >3 | Unique top-level directories from non-test file list |
| Security-sensitive files (auth, crypto, payments, permissions) | any | File path matching |
| Database migrations present | any | File path matching |
| API surface changes (public endpoints, exported interfaces) | any | File path matching |

**Test file exclusion:** test files inflate complexity signals without adding review risk -- they're boilerplate-heavy and follow repetitive patterns. Exclude paths matching `tests/`, `test/`, `__tests__/`, `*.test.*`, `*.spec.*`, `*_test.*` from the lines, files, and directories signals. Use `git diff --stat -- ':!tests/' ':!test/' ':!__tests__/' ':!*.test.*' ':!*.spec.*' ':!*_test.*'` for the filtered count. Report both totals for transparency: "450 lines changed (280 excluding tests)."

**3+ signals → deep review.** Inform the user, then dispatch parallel specialist agents per [deep-review.md](./references/deep-review.md). Pass the diff to agents -- do NOT read it first. Reading and analyzing the diff yourself before dispatching agents defeats the purpose of deep review. **Stop here -- do not proceed to the Review Process section.**

**2 signals → suggest**: "This touches N files across M modules. Deep review? (y/n)"

**0-1 signals → standard review.** Proceed to Review Process below.

Before auto-switching to deep review, check the exceptions list in [deep-review.md](./references/deep-review.md) -- certain change types (pure docs, mechanical refactors, single-file <50 lines) override signal count.

Override: `deep` forces multi-agent, `quick` forces single-pass.

## Review Process

**Standard reviews only.** If mode selection triggered deep review, specialist agents handle the review per [deep-review.md](./references/deep-review.md) -- do not run these steps yourself.

1. **Context** — do these before reading code:
   - **Scope Drift Check**: compare `git diff --stat` against the PR's stated intent. Classify as CLEAN / DRIFT DETECTED / REQUIREMENTS MISSING. If DRIFT, note the drifted files and ask the author: ship as-is, split, or remove unrelated changes?
   - **Read the intent**: PR description, linked issue, or task spec. If the code does something the intent doesn't describe, or fails to do something the intent promises, flag as a finding — correct code that solves the wrong problem is still wrong.
   - **Fetch existing discussions**: prior review comments may have already resolved issues you'd otherwise re-raise. Check `gh api repos/{owner}/{repo}/pulls/{pr}/comments` before starting.
   - **Run automated gates**: execute the project's test/lint suite if available (check CI config for the canonical commands) to catch failures before manual review.
2. **Structural scan** -- architecture, file organization, API surface changes. Flag breaking changes. For files marked as added (`A`) in the diff, use the diff content directly -- don't attempt to read them from the working tree when reviewing a remote branch.
3. **Line-by-line** -- correctness, edge cases, error handling, naming, readability. Use question-based feedback ("What happens if `input` is empty here?") instead of declarative statements to encourage author thinking.
4. **Security** -- input validation, auth checks, secrets exposure, injection vectors (SQL, XSS, CSRF, SSRF, command, path traversal, unsafe deserialization). Flag race conditions (TOCTOU, check-then-act). Use [security-patterns.md](./references/security-patterns.md) for grep-able detection patterns across 11 vulnerability classes.
5. **Test coverage** -- verify new code paths have tests. Flag untested error paths, edge cases, and behavioral changes without corresponding test updates. Flag tests coupled to implementation details (mocking internals, testing private methods) -- test behavior, not wiring.
6. **Reliability** -- error handling completeness, timeout/retry logic, resource cleanup on error paths, graceful degradation. Use [reliability-patterns.md](./references/reliability-patterns.md) for detection patterns and grep-able signals.
7. **Removal candidates** -- identify dead code, unused imports, feature-flagged code that can be cleaned up. Distinguish safe-to-delete (no references) from defer-with-plan (needs migration).
8. **Verify** -- run formatter/lint/tests on touched files. State what was skipped and why. If code changes affect features described in README/ARCHITECTURE/CONTRIBUTING, note doc staleness as informational.
9. **Summary** -- present findings grouped by severity with verdict: **Ready to merge / Ready with fixes / Not ready**.

**Large diffs (>500 lines):** Review by module/directory rather than file-by-file. Summarize each module's changes first, then drill into high-risk areas. Flag if the PR should be split.

**Change sizing:** Ideal PRs are ~100-300 lines of meaningful changes (excluding generated code, lockfiles, snapshots). PRs beyond this range have slower review cycles and higher defect rates. When a PR exceeds this, suggest splitting using one of these strategies: (a) **Stack** -- sequential PRs where each builds on the previous, merged in order; (b) **By file group** -- group related files (e.g., model + migration + tests) into separate PRs; (c) **Horizontal** -- split by layer (frontend, API, database); (d) **Vertical** -- split by feature slice (each PR delivers one user-visible behavior end-to-end).

## Severity and Confidence

Four severity tiers (Critical / Important / Medium / Minor) and a 5-band confidence rubric (0.0-1.0 → Report / Report-if-actionable / Suppress) govern what lands in the report. Full rules, false-positive suppression categories, and the LLM-specific prompt-injection exception in [severity-and-confidence.md](./references/severity-and-confidence.md).

Tie every finding to concrete code evidence (file path, line number, specific pattern). Never fabricate references.

## What to Check

For category checklists (Correctness, Maintainability & Readability, Performance, Adversarial red-team pass, AI-generated code lens), load [check-categories.md](./references/check-categories.md). It's the structured checklist for the line-by-line review step.

Language-specific checks live in [language-profiles.md](./references/language-profiles.md) — load the profile matching the file extensions in the diff (TypeScript/React, Python, PHP, Shell/CI, Configuration, Data Formats, Security, LLM Trust Boundaries).

## Action Routing

For every finding, classify the fix into one of four tiers: `safe_auto` / `gated_auto` / `manual` / `advisory`. Full decision rules and conflict-resolution policy in [action-routing.md](./references/action-routing.md). When in doubt, escalate to `gated_auto` — never promote toward `safe_auto` on disagreement.

## Comment Labels

Prefix inline review comments so authors know what requires action:

- *(no prefix)* -- required change (maps to Critical or Important severity), blocks merge
- **Nit:** -- style preference, optional
- **Consider:** -- suggestion worth evaluating, not blocking
- **FYI:** -- informational, no action expected

## Anti-Patterns in Reviews

- Nitpicking style when linters exist -- defer to automated tools instead
- "While you're at it..." scope creep -- open a separate issue instead
- Blocking on personal preference -- approve with a Minor comment instead
- Rubber-stamping without reading -- always verify at least Stage 1
- Reviewing code quality before verifying spec compliance -- do Stage 1 first
- Recommending fix patterns without checking currency -- verify the pattern is current for the project's framework version before suggesting it. Prefer built-in alternatives from newer versions
- Fighting documented overrides -- if the project's `CLAUDE.md`, `AGENTS.md`, or an inline comment documents a deliberate bypass of a general rule (e.g., "we intentionally allow X because Y"), honor it. Do not re-raise the underlying concern; do not "just to be safe" around it. If the override lacks rationale, suggest documenting the reason — don't argue the rule.

## When to Stop and Ask

- Fixing the issues would require an API redesign beyond the PR's scope
- Intent behind a change is ambiguous -- ask rather than assume
- Missing validation tooling (no linter, no tests) -- flag the gap, don't guess

## Output Format

```
## Review: [brief title]

### Critical
- **CR-001.** [file:line] `quoted code` -- [issue]. Score: [0.0-1.0]. [What happens if not fixed]. Fix: [concrete suggestion].

### Important
- **CR-002.** [file:line] `quoted code` -- [issue]. Score: [0.0-1.0]. [Why it matters]. Consider: [alternative approach].

### Medium
- **CR-003.** [file:line] -- [issue]. Score: [0.0-1.0]. [Why it matters].

### Minor
- **CR-004.** [file:line] -- [observation].

### What's Working Well
- [specific positive observation with why it's good]

### Residual Risks
- [unresolved assumptions, areas not fully covered, open questions]

### Verdict
Ready to merge / Ready with fixes / Not ready -- [one-sentence rationale]
```

Number findings as `CR-001`, `CR-002`... sequentially across all severity levels so they can be referenced by ID in discussions, PR comments, and follow-up todos. Limit to 10 findings per severity. If more exist, note the count and show the highest-impact ones.

For multi-agent consolidation (deep review, parallel specialists), apply the merge algorithm in [deep-review.md](./references/deep-review.md) — it handles same-line dedupe, conflicting severity, `NEEDS DECISION` flagging, and cross-lens confidence boosting.

**Clean review (no findings):** If the code is solid, say so explicitly. Summarize what was checked and why no issues were found. A clean review is a valid outcome, not an indication of insufficient effort.

## References

| Document | When to load | What it covers |
|----------|-------------|----------------|
| [security-patterns.md](./references/security-patterns.md) | Security review step or deep review security agent | Grep-able detection patterns across 11 vulnerability classes |
| [security-test-coverage.md](./references/security-test-coverage.md) | Full security audit deliverable (used by `ia-security-sentinel` agent) | Auth edge cases, authorization, input boundary, concurrency, session hygiene, output boundary checklist |
| [language-profiles.md](./references/language-profiles.md) | Language-specific checks step | TypeScript/React, Python, PHP, Shell/CI, Config, Security, LLM Trust |
| [deep-review.md](./references/deep-review.md) | When mode selection triggers deep review | Specialist agents, prompt template, merge algorithm, model selection |
| [review-traps-catalog.md](./references/review-traps-catalog.md) | Starting any non-trivial review; writing findings with "should"/"could"/"what if" | Reachability-before-severity, docs-idiom smoke test, convention-from-3-files, speculative future-design, paired-enum drift, cross-repo contract staleness, language-version gotchas |
| [check-categories.md](./references/check-categories.md) | Line-by-line step, structuring the read | Correctness, Maintainability, Performance, Adversarial, AI-generated-code lens |
| [action-routing.md](./references/action-routing.md) | Classifying fix-application for each finding | 4-tier split (safe_auto / gated_auto / manual / advisory), conflict resolution |
| [severity-and-confidence.md](./references/severity-and-confidence.md) | Classifying severity + confidence for each finding | Critical/Important/Medium/Minor tiers, 5-band confidence rubric, FP suppression categories |
| [false-positive-suppression.md](./references/false-positive-suppression.md) | Detailed FP categories with framework-idiom and test-specific examples | Linked from severity-and-confidence; covers overridable patterns |

## Integration

- `ia-receiving-code-review` -- the inbound side (processing review feedback received from others). Action-routing terminology maps across: `safe_auto` ≈ AUTO-FIX, `gated_auto` ≈ ESCALATE-for-approval, `manual` ≈ ESCALATE, `advisory` ≈ FYI (no-op).
- `ia-kieran-reviewer` agent -- persona-driven Python/TypeScript deep quality review (type safety, naming, modern patterns)
- `workflows:review` -- full ceremony review (worktrees, ultra-thinking, multi-agent). Deep review is lighter: no worktrees, no plan verification, just parallel specialist agents on the same diff.
- `/resolve-pr-parallel` command -- batch-resolve PR comments with parallel agents
- `ia-security-sentinel` agent -- deep security audit beyond the security step in this skill. Also supports threat-model mode for architectural security analysis when the diff introduces new trust boundaries, auth flows, or external API surfaces.
