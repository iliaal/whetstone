---
name: ia-code-review
class: discipline
description: >-
  Structured code reviews with severity-ranked findings and deep multi-agent
  mode. Use when performing a code review, auditing code quality, or critiquing
  PRs, MRs, or diffs.
---

# Code Review

**Caller contract:** when the invoking task already defines scope, base SHA, or an output contract (subagent protocols, orchestrated reviews), skip Scope Resolution, Review Mode Selection, and Output Format — apply only the review discipline (two-stage check, severity, evidence rules, anti-patterns) within that contract.

## Two-Stage Review

**Stage 1 -- Spec compliance** (do this FIRST): verify the changes implement what was intended — check the PR description, issue, or task spec for missing requirements, unnecessary additions, interpretation gaps. If the implementation is wrong, stop here -- reviewing quality on the wrong feature wastes effort.

**Stage 2 -- Code quality**: only after Stage 1 passes, review for correctness, maintainability, security, and performance.

## Scope Resolution

**Pre-flight**: verify `git rev-parse --git-dir` exists before anything else. If not in a git repo, ask for explicit file paths — ask via AskUserQuestion (Claude Code; load with ToolSearch `select:AskUserQuestion` if not loaded) or request_user_input (Codex); fall back to numbered options in chat. Later asks reuse this channel.

When no specific files are given, resolve scope via this fallback chain:
1. User-specified files/directories (explicit request)
2. Session-modified files (`git diff --name-only`, unstaged + staged)
3. All uncommitted files (`git diff --name-only HEAD`)
4. Untracked files (`git ls-files --others --exclude-standard`) -- often the most review-worthy
5. **Zero files → stop.** Ask what to review (ask channel above).

Exclude: lockfiles, minified/bundled output, vendored/generated code.

### Base-branch resolution for branch reviews

When the review target is a branch (not a working-tree diff), the comparison range is the **merge-base**, not the working-tree delta — resolve it before reading any diff. Fallback chain (PR base → default-branch inference → `origin/*` → `git merge-base` → unshallow retry), stacked-branch detail, and the "never fall back to `git diff HEAD`" rule in [scope-resolution.md](./references/scope-resolution.md). Stacked branches: prefer the platform's `base_sha` (`gh pr diff`) — a local merge-base over-covers.

**Off-scope filter (always, after any branch review): intersect finding paths with the change's `--name-only` set; discard non-intersecting findings.**

## Review Mode Selection

**Run this BEFORE reading the full diff.** Use metadata only (`git diff --stat`, file list from scope resolution) — reading the diff first creates analysis momentum that bypasses mode selection.

**Exceptions first** — these change types stay single-pass regardless of signal count: pure documentation/markdown changes; mechanical refactors (renames, moves) with no logic changes; single-file changes under 50 lines.

**Verification-mechanism carve-out:** even when a change stays single-pass by the exceptions above, if it *is* a verification mechanism (CI/CD gate, merge-block check, coverage/lint gate, build/deploy step, or test infra/mock that could mask a real failure), apply the "can this silently false-pass?" lens during the single-pass review — the mechanism can go green while the thing it guards is red. In deep review this same lens runs as a size-independent red-team trigger (see [deep-review.md](./references/deep-review.md)).

| Signal | Threshold |
|--------|-----------|
| Lines changed (excluding test files) | >300 |
| Files touched (excluding test files) | >8 |
| Top-level directories spanned (non-test) | >3 |
| Security-sensitive paths (auth, crypto, payments, permissions) | any |
| Database migrations | any |
| API surface changes (public endpoints, exported interfaces) | any |

**Test file exclusion:** filter test paths out of the size signals with `git diff --stat -- ':!tests/' ':!*.test.*' ':!*.spec.*' ':!*_test.*'` and report both totals: "450 lines changed (280 excluding tests)."

**3+ signals → deep review.** Inform the user, then dispatch parallel specialist agents per [deep-review.md](./references/deep-review.md). Pass the diff to agents -- do NOT read it first. **Stop here -- skip the Review Process section.**

**2 signals → suggest** (ask channel above): "This touches N files across M modules. Deep review?"

**0-1 signals → standard review.** Proceed to Review Process below.

Override: `deep` forces multi-agent, `quick` forces single-pass.

## Review Process

**Standard reviews only** -- deep review is handled by the dispatched specialists.

1. **Context** — before reading code:
   - **Scope drift**: compare `git diff --stat` against the PR's stated intent. Classify CLEAN / DRIFT DETECTED / REQUIREMENTS MISSING; on drift, ask the author: ship as-is, split, or remove?
   - **Intent**: read the PR description, linked issue, or task spec. Deviation or under-delivery is a finding — the wrong problem solved correctly is still wrong.
   - **Prior discussions**: reconcile existing review comments so resolved issues aren't re-raised. Gate on a presence check; commands in [scope-resolution.md](./references/scope-resolution.md).
   - **Automated gates**: run the project's test/lint suite (canonical commands in CI config).
2. **Structural scan** -- architecture, file organization, API surface; flag breaking changes. Added (`A`) files on a remote branch: use the diff content, not the working tree.
3. **Line-by-line** -- correctness, edge cases, error handling, naming, readability. Category checklists (correctness, maintainability, performance, adversarial, AI-code lens) in [check-categories.md](./references/check-categories.md); load the profile matching the diff's file extensions from [language-profiles.md](./references/language-profiles.md) (TS/React, Python, PHP, Shell/CI, Config, Data, Security, LLM Trust). Prefer questions ("What happens if `input` is empty?") over declarations.
4. **Security** -- input validation, auth checks, secrets exposure, injection vectors (SQL, XSS, CSRF, SSRF, command, path traversal, unsafe deserialization), race conditions (TOCTOU). Grep-able patterns for the common vulnerability classes in [security-patterns.md](./references/security-patterns.md).
5. **Test coverage** -- untested new paths, error paths, and behavioral changes without test updates. Flag implementation-coupled tests (mocked internals, private methods) -- test behavior, not wiring.
6. **Reliability** -- error handling completeness, timeout/retry, resource cleanup on error paths, graceful degradation. Patterns in [reliability-patterns.md](./references/reliability-patterns.md).
7. **Removal candidates** -- dead code, unused imports, cleanup-ready feature flags; safe-to-delete (no references) vs defer-with-plan.
8. **Verify** -- run formatter/lint/tests on touched files; state what was skipped and why. Note doc staleness (README/ARCHITECTURE/CONTRIBUTING) as informational.
9. **Summary** -- findings grouped by severity with verdict: **Ready to merge / Ready with fixes / Not ready**.

**Large diffs:** >500 lines → review by module, not file-by-file. Flag oversized PRs (ideal ~100-300 meaningful lines) and suggest a split — thresholds and the four split strategies in [pr-sizing.md](./references/pr-sizing.md).

## Severity and Confidence

Four severity tiers (Critical / Important / Medium / Minor) order the report; a confidence score (0.0-1.0) per finding decides what lands in it:

**Confidence bands: ≥0.70 report · 0.60-0.69 report-if-actionable · <0.60 suppress (exception: Critical security findings report at ≥0.50).**

Full 5-band rubric, evidence-before-severity ordering, false-positive suppression categories, and the LLM prompt-injection exception in [severity-and-confidence.md](./references/severity-and-confidence.md).

Evidence lives in the `CR-XXX` entry itself — `[file:line]` plus `` `quoted code` ``, not only in surrounding prose. Never fabricate references.

## Action Routing

Classify every finding's fix into one of four tiers:

- `safe_auto` -- deterministic, local, behavior-preserving fix: apply directly
- `gated_auto` -- concrete fix crossing a behavior/contract/permission/API boundary: present it, wait for sign-off
- `manual` -- author judgment, rewrite, or redesign needed: flag with fix intent, don't apply
- `advisory` -- report-only risk signal: record under Residual Risks

Full decision rules and conflict resolution in [action-routing.md](./references/action-routing.md). When in doubt, escalate to `gated_auto` — never promote toward `safe_auto` on disagreement.

## Comment Labels

Prefix inline comments so authors know what requires action: *(no prefix)* = required change (Critical/Important), blocks merge; **Nit:** = style preference, optional; **Consider:** = suggestion worth evaluating, not blocking; **FYI:** = informational, no action expected.

## Anti-Patterns in Reviews

- Nitpicking style when linters exist -- defer to automated tools
- "While you're at it..." scope creep -- open a separate issue
- Blocking on personal preference -- approve with a Minor comment
- Skipping Stage 1 -- never review code quality before verifying spec compliance; rubber-stamping without reading is not a review
- Recommending fix patterns without checking currency -- verify the pattern is current for the project's framework version; prefer newer built-in alternatives
- Fighting documented overrides -- a rationale-backed bypass (`CLAUDE.md`, `AGENTS.md`, inline comment) is owner-blessed: honor it, don't re-raise; if the rationale is missing, suggest documenting one. Plan-mandated defects are not self-justifying — report them labeled "plan-mandated" for the human to adjudicate
- Resting a finding on an unverified absence -- read the region or grep the *exact* symbol expecting zero lines; a subagent's confident negative or a broad-pattern hit is not proof
- Calling a change a regression without a baseline read -- read the pre-change file (`git show <base>:<file>`), not just the hunk; cite the introducing commit when confirmed
- Widening/narrowing a key or guard without checking the mirror bug -- name one concrete opposite-defect case along the now-ignored axis before accepting the fix
- Checking only one projection on a hide/filter/redact change -- enumerate every field surfacing the same entity (list, `*_count`/`*_ids`, raw documents, detail view); require a test per field
- Pre-classifying own findings as weak -- no "INFO only" / "no action required" wording; anchor severity in concrete constants from the code, not hypotheticals

Extended rationale for the last six traps — and the broader trap catalog — in [review-traps-catalog.md](./references/review-traps-catalog.md).

## When to Stop and Ask

- Fixing the issues would require an API redesign beyond the PR's scope
- Intent behind a change is ambiguous -- ask rather than assume
- Missing validation tooling (no linter, no tests) -- flag the gap, don't guess

## Output Format

```
## Review: [brief title]

### Critical
- **CR-001.** [file:line] `quoted code` -- [issue]. Score: [0.0-1.0]. [Impact if not fixed]. Fix: [concrete suggestion].

### Important / ### Medium
- (same shape; Important adds Consider: [alternative approach])

### Minor
- **CR-004.** [file:line] -- [observation].

### What's Working Well
- [specific positive observation with why it's good]

### Residual Risks
- [unresolved assumptions, areas not covered, open questions]

### Verdict
Ready to merge / Ready with fixes / Not ready -- [one-sentence rationale]
```

Number findings `CR-001`, `CR-002`... sequentially across severities for stable IDs. Cap 10 per severity; note any overflow and show the highest-impact ones.

**Markdown safety:** in table cells, escape literal `|` as `\|` — code excerpts with pipes (`a | b`, `string | null`) split rows silently. Bullet output is pipe-safe.

Multi-agent consolidation: apply the merge algorithm in [deep-review.md](./references/deep-review.md) (same-line dedupe, severity conflicts, `NEEDS DECISION`, cross-lens confidence boosts).

**Clean review (no findings):** a valid outcome, not insufficient effort — say so explicitly and summarize what was checked.

## References

References load at their point of use above. Additionally: [security-test-coverage.md](./references/security-test-coverage.md) — security-audit deliverable checklist; [false-positive-suppression.md](./references/false-positive-suppression.md) — framework-idiom and test-specific FP categories; [external-review-subprocess.md](./references/external-review-subprocess.md) — external-CLI reviewer protocol (heartbeat tolerance, run-until-clean, frozen-diff binding).

## Integration

- `ia-receiving-code-review` -- inbound side. Tier map: `safe_auto` ≈ AUTO-FIX, `gated_auto` ≈ ESCALATE-for-approval, `manual` ≈ ESCALATE, `advisory` ≈ FYI
- `ia-kieran-reviewer` agent -- persona-driven Python/TypeScript deep quality review
- `/ia-review` -- full ceremony (worktrees, ultra-thinking); deep review here is lighter: parallel specialists, no worktrees
- `/resolve-pr-parallel` command -- batch-resolve PR comments with parallel agents
- `ia-security-sentinel` agent -- deep security audit; threat-model mode for new trust boundaries
