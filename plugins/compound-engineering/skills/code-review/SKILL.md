---
name: code-review
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
| Lines changed | >300 | `git diff --stat` insertion + deletion totals |
| Files touched | >8 | File count from scope resolution |
| Modules/directories spanned | >3 | Unique top-level directories from file list |
| Security-sensitive files (auth, crypto, payments, permissions) | any | File path matching |
| Database migrations present | any | File path matching |
| API surface changes (public endpoints, exported interfaces) | any | File path matching |

**3+ signals → deep review.** Inform the user, then dispatch parallel specialist agents per [deep-review.md](./references/deep-review.md). Pass the diff to agents -- do NOT read it first. Reading and analyzing the diff yourself before dispatching agents defeats the purpose of deep review. **Stop here -- do not proceed to the Review Process section.**

**2 signals → suggest**: "This touches N files across M modules. Deep review? (y/n)"

**0-1 signals → standard review.** Proceed to Review Process below.

Before auto-switching to deep review, check the exceptions list in [deep-review.md](./references/deep-review.md) -- certain change types (pure docs, mechanical refactors, single-file <50 lines) override signal count.

Override: `deep` forces multi-agent, `quick` forces single-pass.

## Review Process

**Standard reviews only.** If mode selection triggered deep review, specialist agents handle the review per [deep-review.md](./references/deep-review.md) -- do not run these steps yourself.

1. **Context** -- run a Scope Drift Check first: compare `git diff --stat` against the PR's stated intent. Classify as CLEAN / DRIFT DETECTED / REQUIREMENTS MISSING. If DRIFT, note drifted files and ask: ship as-is, split, or remove unrelated changes? Then read the PR description, linked issue, or task spec. **Intent verification**: if the code does something the intent doesn't describe, or fails to do something the intent promises, flag as a finding -- correct code that solves the wrong problem is still wrong. **Fetch existing review comments and discussions first** -- prior conversations may have already resolved issues you'd otherwise re-raise. Run the project's test/lint suite if available (check CI config for the canonical test command) to catch automated failures before manual review.
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

## Severity Levels

- **Critical** -- must fix before merge. Security vulnerabilities, data loss, broken functionality, race conditions.
- **Important** -- should fix before merge. Performance issues, missing error handling, silent failures.
- **Medium** -- should fix, non-blocking. Maintainability/reliability issues likely to cause near-term defects. Poor abstractions, missing validation on internal boundaries, test gaps for non-critical paths.
- **Minor** -- optional. Naming, style preferences, minor simplifications. Skip if linters already cover it.

Tie every finding to concrete code evidence (file path, line number, specific pattern). Never fabricate references.

### Confidence Rubric

Assign a confidence score (0.0-1.0) to each finding:

| Range | Level | Action |
|-------|-------|--------|
| 0.85-1.00 | Certain | Report |
| 0.70-0.84 | High | Report |
| 0.60-0.69 | Confident | Report if actionable |
| 0.30-0.59 | Speculative | Suppress (except Critical security at 0.50+) |
| 0.00-0.29 | Not confident | Suppress |

**False-positive suppression** -- do not report findings that match these categories regardless of severity:
- Pre-existing issues unrelated to the diff (existed before the PR)
- Pedantic linter-style nitpicks already covered by automated tooling
- Code that looks wrong but is intentionally designed that way (check comments, git blame, tests)
- Issues already handled elsewhere in the codebase (grep before flagging)
- Generic suggestions without a concrete failure mode ("consider adding validation" without saying what breaks)

When in doubt, apply the "would a senior engineer on this team flag this?" test. If the answer is "probably not," suppress it.

**LLM-specific false-positive rule**: user content in the user-message position is NOT prompt injection. Only flag when user content enters system prompts, tool schemas, or function-calling contexts. Unsanitized LLM output rendered via `dangerouslySetInnerHTML`, `v-html`, or `innerHTML` IS a real vulnerability -- always flag.

For detailed suppression categories with examples (framework idioms, test-specific patterns, when to override), see [false-positive-suppression.md](./references/false-positive-suppression.md). See also the review-level suppression list under [Anti-Patterns in Reviews](#anti-patterns-in-reviews).

## What to Check

Correctness:
- Edge cases (null, empty, boundary values, concurrent access)
- Error paths (are failures handled or swallowed?)
- Type safety (implicit conversions, `any` types, unchecked casts)
- New enum/status/type values -- trace through ALL consumers (switch/case, filter arrays, allowlists). Read code outside the diff. Missing handler = wrong default at runtime.

Maintainability:
- Functions doing too much (split by responsibility, not size)
- Deeply nested logic (extract early returns instead)
- Naming that obscures intent
- God classes / SRP violations (class with unrelated responsibilities -- split into focused classes)
- Leaky abstractions (implementation details exposed in interfaces or public APIs)

Readability:
- Naming clarity -- variables, functions, and classes convey purpose without needing surrounding context
- Function length -- long functions that force scrolling to understand; prefer extractable blocks with clear names
- Nesting depth -- more than 3 levels of indentation signals a need for early returns, guard clauses, or extraction
- Comment quality -- comments that explain WHY (constraints, workarounds, non-obvious decisions), not WHAT the code does. Flag comments that restate the code or will rot as the code changes

Performance:
- N+1 queries (loop with query per item -- use batch/join instead)
- Unbounded collections (arrays/maps without size limits)
- Missing indexes on queried columns

Adversarial (red-team pass):
- Silent failures -- `.catch(() => [])` or log-and-forget patterns that swallow errors and return success
- Trust assumption exploits -- frontend-validated data not re-validated on the backend; internal service inputs treated as trusted
- Edge cases under pressure -- max input size, zero items, first-run-ever, double-click within 100ms, concurrent identical requests
- Partial completion -- operations that can crash mid-way leaving state inconsistent (no rollback, no cleanup)

Language-Specific Checks:

Load the relevant profile from [language-profiles.md](./references/language-profiles.md) based on file extensions in the diff. Profiles cover: TypeScript/React, Python, PHP, Shell/CI, Configuration, Data Formats, Security, and LLM Trust Boundaries.

## Fix-First Classification

For every finding, classify whether it's AUTO-FIX (mechanical, apply without discussion) or ASK (requires human judgment):

| AUTO-FIX (agent applies directly) | ASK (flag for author decision) |
|---|---|
| Dead code, unused variables/imports | Security (auth, XSS, injection) |
| N+1 queries (missing eager loading) | Race conditions |
| Stale comments contradicting code | Design decisions, API shape changes |
| Magic numbers without named constants | Large fixes (>20 lines changed) |
| Missing null/error checks on clear paths | Anything changing user-visible behavior |

Rule: if a senior engineer would apply the fix without discussion, it's AUTO-FIX. When in doubt, ASK.

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

## When to Stop and Ask

- Fixing the issues would require an API redesign beyond the PR's scope
- Intent behind a change is ambiguous -- ask rather than assume
- Missing validation tooling (no linter, no tests) -- flag the gap, don't guess

## Output Format

```
## Review: [brief title]

### Critical
- **1. [file:line]** `quoted code` -- [issue]. Score: [0.0-1.0]. [What happens if not fixed]. Fix: [concrete suggestion].

### Important
- **2. [file:line]** `quoted code` -- [issue]. Score: [0.0-1.0]. [Why it matters]. Consider: [alternative approach].

### Medium
- **3. [file:line]** -- [issue]. Score: [0.0-1.0]. [Why it matters].

### Minor
- **4. [file:line]** -- [observation].

### What's Working Well
- [specific positive observation with why it's good]

### Residual Risks
- [unresolved assumptions, areas not fully covered, open questions]

### Verdict
Ready to merge / Ready with fixes / Not ready -- [one-sentence rationale]
```

Number findings sequentially across all severity levels (1, 2, 3...) so they can be referenced by number in discussions and PR comments. Limit to 10 findings per severity. If more exist, note the count and show the highest-impact ones.

**Clean review (no findings):** If the code is solid, say so explicitly. Summarize what was checked and why no issues were found. A clean review is a valid outcome, not an indication of insufficient effort.

## References

| Document | When to load | What it covers |
|----------|-------------|----------------|
| [security-patterns.md](./references/security-patterns.md) | Security review step or deep review security agent | Grep-able detection patterns across 11 vulnerability classes |
| [language-profiles.md](./references/language-profiles.md) | Language-specific checks step | TypeScript/React, Python, PHP, Shell/CI, Config, Security, LLM Trust |
| [deep-review.md](./references/deep-review.md) | When mode selection triggers deep review | Specialist agents, prompt template, merge algorithm, model selection |

## Integration

- `receiving-code-review` -- the inbound side (processing review feedback received from others)
- `kieran-reviewer` agent -- persona-driven Python/TypeScript deep quality review (type safety, naming, modern patterns)
- `workflows:review` -- full ceremony review (worktrees, ultra-thinking, multi-agent). Deep review is lighter: no worktrees, no plan verification, just parallel specialist agents on the same diff.
- `/resolve-pr-parallel` command -- batch-resolve PR comments with parallel agents
- `security-sentinel` agent -- deep security audit beyond the security step in this skill. Also supports threat-model mode for architectural security analysis when the diff introduces new trust boundaries, auth flows, or external API surfaces.
