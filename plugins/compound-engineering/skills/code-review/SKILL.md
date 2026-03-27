---
name: code-review
description: >-
  Structured code reviews with severity-ranked findings. Use when performing a
  code review, auditing code quality, or critiquing PRs, MRs, or diffs.
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

## Review Process

1. **Context** -- run a Scope Drift Check first: compare `git diff --stat` against the PR's stated intent. Classify as CLEAN / DRIFT DETECTED / REQUIREMENTS MISSING. If DRIFT, note drifted files and ask: ship as-is, split, or remove unrelated changes? Then read the PR description, linked issue, or task spec. **Fetch existing review comments and discussions first** -- prior conversations may have already resolved issues you'd otherwise re-raise. Run the project's test/lint suite if available (check CI config for the canonical test command) to catch automated failures before manual review.
2. **Structural scan** -- architecture, file organization, API surface changes. Flag breaking changes. For files marked as added (`A`) in the diff, use the diff content directly -- don't attempt to read them from the working tree when reviewing a remote branch.
3. **Line-by-line** -- correctness, edge cases, error handling, naming, readability. Use question-based feedback ("What happens if `input` is empty here?") instead of declarative statements to encourage author thinking.
4. **Security** -- input validation, auth checks, secrets exposure, injection vectors (SQL, XSS, CSRF, SSRF, command, path traversal, unsafe deserialization). Flag race conditions (TOCTOU, check-then-act). Use [security-patterns.md](./references/security-patterns.md) for grep-able detection patterns across 11 vulnerability classes.
5. **Test coverage** -- verify new code paths have tests. Flag untested error paths, edge cases, and behavioral changes without corresponding test updates. Flag tests coupled to implementation details (mocking internals, testing private methods) -- test behavior, not wiring.
6. **Resource cleanup** -- file handles, DB connections, event listeners, timers, subscriptions. Verify cleanup on both success and error paths.
7. **Removal candidates** -- identify dead code, unused imports, feature-flagged code that can be cleaned up. Distinguish safe-to-delete (no references) from defer-with-plan (needs migration).
8. **Verify** -- run formatter/lint/tests on touched files. State what was skipped and why. If code changes affect features described in README/ARCHITECTURE/CONTRIBUTING, note doc staleness as informational.
9. **Summary** -- present findings grouped by severity with verdict: **Ready to merge / Ready with fixes / Not ready**. Classify each finding using the Fix-First Heuristic, then auto-apply AUTO-FIX items (with one-line summaries) and batch-present ASK items for user decision.

**Large diffs (>500 lines):** Review by module/directory rather than file-by-file. Summarize each module's changes first, then drill into high-risk areas. Flag if the PR should be split.

## Severity Levels

- **Critical** -- must fix before merge. Security vulnerabilities, data loss, broken functionality, race conditions.
- **Important** -- should fix before merge. Performance issues, missing error handling, silent failures.
- **Medium** -- should fix, non-blocking. Maintainability/reliability issues likely to cause near-term defects. Poor abstractions, missing validation on internal boundaries, test gaps for non-critical paths.
- **Minor** -- optional. Naming, style preferences, minor simplifications. Skip if linters already cover it.

Tie every finding to concrete code evidence (file path, line number, specific pattern). State confidence: **high** (verified in code), **medium** (inferred from pattern), **low** (suspected, needs verification). Never fabricate references.

## Fix-First Heuristic

After classifying severity, determine disposition for each finding:

| AUTO-FIX (apply without asking) | ASK (needs human judgment) |
|---------------------------------|---------------------------|
| Dead code, unused variables/imports | Security (auth, XSS, injection) |
| N+1 queries (missing eager load) | Race conditions |
| Stale comments contradicting code | Design decisions |
| Magic numbers -> named constants | Large fixes (>20 lines changed) |
| Variables assigned but never read | Removing functionality |
| Version/path mismatches in docs | Anything changing user-visible behavior |

**Rule of thumb:** if a senior engineer would apply it without discussion, AUTO-FIX. If reasonable engineers could disagree, ASK. Critical findings default toward ASK. Minor/mechanical findings default toward AUTO-FIX.

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

Performance:
- N+1 queries (loop with query per item -- use batch/join instead)
- Unbounded collections (arrays/maps without size limits)
- Missing indexes on queried columns

Language-Specific Checks:

Load the relevant profile from [language-profiles.md](./references/language-profiles.md) based on file extensions in the diff. Profiles cover: TypeScript/React, Python, PHP, Shell/CI, Configuration, Data Formats, Security, and LLM Trust Boundaries.

## Anti-Patterns in Reviews

- Nitpicking style when linters exist -- defer to automated tools instead
- "While you're at it..." scope creep -- open a separate issue instead
- Blocking on personal preference -- approve with a Minor comment instead
- Rubber-stamping without reading -- always verify at least Stage 1
- Reviewing code quality before verifying spec compliance -- do Stage 1 first
- Recommending fix patterns without checking currency -- verify the pattern is current for the project's framework version before suggesting it. Prefer built-in alternatives from newer versions

**Also suppress** (do not flag these):
- "X is redundant with Y" when redundancy aids readability
- "Add a comment explaining this threshold" -- thresholds change during tuning, comments rot
- "This assertion could be tighter" when it already covers the behavior
- Consistency-only changes (reformatting to match adjacent code style)
- "Regex doesn't handle edge case X" when input is constrained and X never occurs
- Anything already addressed in the diff being reviewed -- read the FULL diff before commenting

## When to Stop and Ask

- Fixing the issues would require an API redesign beyond the PR's scope
- Intent behind a change is ambiguous -- ask rather than assume
- Missing validation tooling (no linter, no tests) -- flag the gap, don't guess

## Output Format

```
## Review: [brief title]

### Critical
- **[file:line]** `quoted code` -- [issue]. Confidence: high|medium|low. [What happens if not fixed]. Fix: [concrete suggestion].

### Important
- **[file:line]** `quoted code` -- [issue]. Confidence: high|medium|low. [Why it matters]. Consider: [alternative approach].

### Medium
- **[file:line]** -- [issue]. Confidence: high|medium|low. [Why it matters].

### Minor
- **[file:line]** -- [observation].

### What's Working Well
- [specific positive observation with why it's good]

### Residual Risks
- [unresolved assumptions, areas not fully covered, open questions]

### Verdict
Ready to merge / Ready with fixes / Not ready -- [one-sentence rationale]
```

Limit to 10 findings per severity. If more exist, note the count and show the highest-impact ones.

**Clean review (no findings):** If the code is solid, say so explicitly. Summarize what was checked and why no issues were found. A clean review is a valid outcome, not an indication of insufficient effort.

## Integration

- `receiving-code-review` -- the inbound side (processing review feedback received from others)
- `workflows:review` -- the full review command with multi-agent analysis
- `resolve-pr-parallel` -- batch-resolve PR comments with parallel agents
- `security-sentinel` agent -- deep security audit beyond the security step in this skill
