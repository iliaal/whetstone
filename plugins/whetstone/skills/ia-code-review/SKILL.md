---
name: ia-code-review
class: discipline
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

### Base-branch resolution for branch reviews

When the review target is a branch (not a working-tree diff), the comparison range is the **merge-base**, not the working-tree delta — resolve it before reading any diff. Full fallback chain (PR base → default-branch inference → `origin/*` fallback list → `git merge-base` → shallow-clone retry) and the "never fall back to `git diff HEAD`" rule in [scope-resolution.md](./references/scope-resolution.md).

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

**Test file exclusion:** exclude test paths (`tests/`, `test/`, `__tests__/`, `*.test.*`, `*.spec.*`, `*_test.*`) from the lines/files/directories signals — they inflate complexity without adding review risk. Filter with `git diff --stat -- ':!tests/' ':!*.test.*' ':!*.spec.*' ':!*_test.*'` and report both totals: "450 lines changed (280 excluding tests)."

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
   - **Fetch existing discussions (when present)**: before raising findings, reconcile prior review comments so you don't re-raise issues other reviewers already resolved. Gate the fetch on a presence check to avoid empty work — the exact `gh pr view`/`gh api` commands are in [scope-resolution.md](./references/scope-resolution.md).
   - **Run automated gates**: execute the project's test/lint suite if available (check CI config for the canonical commands) to catch failures before manual review.
2. **Structural scan** -- architecture, file organization, API surface changes. Flag breaking changes. For files marked as added (`A`) in the diff, use the diff content directly -- don't attempt to read them from the working tree when reviewing a remote branch.
3. **Line-by-line** -- correctness, edge cases, error handling, naming, readability. Use question-based feedback ("What happens if `input` is empty here?") instead of declarative statements to encourage author thinking.
4. **Security** -- input validation, auth checks, secrets exposure, injection vectors (SQL, XSS, CSRF, SSRF, command, path traversal, unsafe deserialization). Flag race conditions (TOCTOU, check-then-act). Use [security-patterns.md](./references/security-patterns.md) for grep-able detection patterns across 11 vulnerability classes.
5. **Test coverage** -- verify new code paths have tests. Flag untested error paths, edge cases, and behavioral changes without corresponding test updates. Flag tests coupled to implementation details (mocking internals, testing private methods) -- test behavior, not wiring.
6. **Reliability** -- error handling completeness, timeout/retry logic, resource cleanup on error paths, graceful degradation. Use [reliability-patterns.md](./references/reliability-patterns.md) for detection patterns and grep-able signals.
7. **Removal candidates** -- identify dead code, unused imports, feature-flagged code that can be cleaned up. Distinguish safe-to-delete (no references) from defer-with-plan (needs migration).
8. **Verify** -- run formatter/lint/tests on touched files. State what was skipped and why. If code changes affect features described in README/ARCHITECTURE/CONTRIBUTING, note doc staleness as informational.
9. **Summary** -- present findings grouped by severity with verdict: **Ready to merge / Ready with fixes / Not ready**.

**Large diffs & PR sizing:** For diffs >500 lines, review by module rather than file-by-file. Flag oversized PRs (ideal ~100-300 meaningful lines, excluding generated code) and suggest a split. Module-review approach, sizing thresholds, and the four split strategies (stack / by-file-group / horizontal / vertical) in [pr-sizing.md](./references/pr-sizing.md).

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
- Fighting documented overrides -- if `CLAUDE.md`, `AGENTS.md`, or an inline comment documents a deliberate bypass (e.g., "we allow X because Y"), honor it: don't re-raise the concern or work around it "just to be safe". If the override lacks a rationale, suggest documenting one — don't argue the rule.

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

Number findings `CR-001`, `CR-002`... sequentially across all severities so they're referenceable by ID. Limit to 10 per severity; if more exist, note the count and show the highest-impact ones.

**Markdown safety:** in table cells, escape literal `|` as `\|` — code excerpts with pipe operators (`a | b`, `string | null`) split rows silently otherwise. Bullet output is pipe-safe.

For multi-agent consolidation (deep/parallel review), apply the merge algorithm in [deep-review.md](./references/deep-review.md) — same-line dedupe, conflicting severity, `NEEDS DECISION` flagging, cross-lens confidence boosting.

**Clean review (no findings):** if the code is solid, say so explicitly — summarize what was checked and why no issues were found. A clean review is a valid outcome, not a sign of insufficient effort.

## References

| Document | Load when — what it covers |
|----------|----------------------------|
| [security-patterns.md](./references/security-patterns.md) | Security step — grep-able detection patterns, 11 vulnerability classes |
| [security-test-coverage.md](./references/security-test-coverage.md) | Security-audit deliverable (`ia-security-sentinel`) — auth/authz, input-boundary, concurrency, session, output checklist |
| [language-profiles.md](./references/language-profiles.md) | Language-specific checks — TS/React, Python, PHP, Shell/CI, Config, LLM Trust |
| [deep-review.md](./references/deep-review.md) | Mode triggers deep review — specialist agents, prompt template, merge algorithm, model selection |
| [review-traps-catalog.md](./references/review-traps-catalog.md) | Any non-trivial review; "should"/"could"/"what if" findings — reachability-first, convention-from-3, speculative-design, enum drift, contract staleness, version gotchas |
| [check-categories.md](./references/check-categories.md) | Line-by-line step — correctness, maintainability, performance, adversarial, AI-code lens |
| [action-routing.md](./references/action-routing.md) | Per-finding fix tier — safe_auto / gated_auto / manual / advisory, conflict resolution |
| [severity-and-confidence.md](./references/severity-and-confidence.md) | Severity + confidence — 4 tiers, 5-band rubric, FP suppression |
| [false-positive-suppression.md](./references/false-positive-suppression.md) | FP categories — framework-idiom and test-specific overridable patterns |
| [scope-resolution.md](./references/scope-resolution.md) | Branch review or prior PR comments — merge-base resolution, discussion-fetch commands |
| [pr-sizing.md](./references/pr-sizing.md) | Large/oversized diff — module review, sizing thresholds, split strategies |
| [external-review-subprocess.md](./references/external-review-subprocess.md) | External-CLI reviewer (codex/`claude -p`, `/code-review ultra`) — heartbeat tolerance, run-until-clean, frozen-diff binding |

## Integration

- `ia-receiving-code-review` -- the inbound side (processing review feedback received from others). Action-routing terminology maps across: `safe_auto` ≈ AUTO-FIX, `gated_auto` ≈ ESCALATE-for-approval, `manual` ≈ ESCALATE, `advisory` ≈ FYI (no-op).
- `ia-kieran-reviewer` agent -- persona-driven Python/TypeScript deep quality review (type safety, naming, modern patterns)
- `/ia-review` -- full ceremony review (worktrees, ultra-thinking, multi-agent). Deep review is lighter: no worktrees, no plan verification, just parallel specialist agents on the same diff.
- `/resolve-pr-parallel` command -- batch-resolve PR comments with parallel agents
- `ia-security-sentinel` agent -- deep security audit beyond the security step in this skill. Also supports threat-model mode for architectural security analysis when the diff introduces new trust boundaries, auth flows, or external API surfaces.
