# Scope and mode selection

Read for a standalone review whose scope or review mode is not already fixed by the caller.

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

When the review target is a branch (not a working-tree diff), the comparison range is the **merge-base**, not the working-tree delta — resolve it before reading any diff. Fallback chain (PR base → default-branch inference → `origin/*` → `git merge-base` → unshallow retry), stacked-branch detail, and the "never fall back to `git diff HEAD`" rule in [scope-resolution.md](./scope-resolution.md). Stacked branches: prefer the platform's `base_sha` (`gh pr diff`) — a local merge-base over-covers.

**Off-scope filter (always, after any branch review): intersect finding paths with the change's `--name-only` set; discard non-intersecting findings.**

### Coverage gate

Enumerate changed files **before** exclusions and track each path through `selected -> pending -> covered | failed` or `excluded(reason)` per [scope-resolution.md](./scope-resolution.md). Keep tests and deletions reviewable. Give each selected file one correctness owner; any pending or failed path forces **Not ready**. List exclusions under Residual Risks.

## Review Mode Selection

**Run this BEFORE reading the full diff.** Use metadata only (`git diff --stat`, file list from scope resolution) — reading the diff first creates analysis momentum that bypasses mode selection.

**Exceptions first** — passive prose and mechanical refactors with no behavior change usually need only a single pass. Classify files by their role: agent instructions, configuration, executable examples, and policy/gate definitions remain subject to correctness/security review even in Markdown. A short diff or `.md` extension alone does not override material risk signals.

**Verification-mechanism carve-out:** even when a change stays single-pass by the exceptions above, if it *is* a verification mechanism (CI/CD gate, merge-block check, coverage/lint gate, build/deploy step, or test infra/mock that could mask a real failure), apply the "can this silently false-pass?" lens during the single-pass review — the mechanism can go green while the thing it guards is red. In deep review this same lens runs as a size-independent red-team trigger (see [deep-review.md](./deep-review.md)). A diff that modifies a documented-standards file (CLAUDE.md, AGENTS.md, CONTRIBUTING.md, STYLE.md, lint configs) gets the same treatment: it is not "pure documentation" -- apply deep-review's standards-disclosure rule (quote each rule added or loosened and what it suppresses in this same diff) during the single-pass review.

### Outcome-integrity lens

Apply these checks to tests, validators, CI gates, specifications, golden files, dependency policy, demos, and conformance tooling regardless of diff size:

- Compare the base and head oracle. Flag weakened assertions, removed discriminating cases, narrower subjects, relaxed validators, or changed acceptance criteria that make the same defect pass.
- Review golden and expected-output changes semantically. A regenerated file and a green suite do not prove that the new output is intended.
- Require each new check, matrix, report, or process artifact to name the observed defect class or release capability it gates. Flag speculative verification machinery as scope without a deliverable.
- Reject vendoring, wrappers, or shims that bypass an explicit dependency or runtime policy unless the policy itself changed through the repository's authorized decision path.
- Look for demo identities, fixed records, special SKUs, or hard-coded subjects that prove only the showcased path. Require varied or runtime-selected subjects when general behavior is claimed.
- Treat process-only changes as process changes. Do not describe them as feature delivery unless the requested deliverable is the process artifact itself.

| Signal | Threshold |
|--------|-----------|
| Lines changed (excluding test files) | >300 |
| Files touched (excluding test files) | >8 |
| Top-level directories spanned (non-test) | >3 |
| Security-sensitive paths (auth, crypto, payments, permissions) | any |
| Database migrations | any |
| API surface changes (public endpoints, exported interfaces) | any |

**Test file exclusion:** filter test paths out of the size signals with `git diff --stat -- ':!tests/' ':!*.test.*' ':!*.spec.*' ':!*_test.*'` and report both totals: "450 lines changed (280 excluding tests)."

**3+ signals → deep review.** Inform the user, then dispatch parallel specialist agents per [deep-review.md](./deep-review.md). Pass the diff to agents -- do NOT read it first. **Stop here -- skip the Review Process section.**

**2 signals → suggest** (ask channel above): "This touches N files across M modules. Deep review?"

**0-1 signals → standard review.** Proceed to Review Process below.

Override: `deep` forces multi-agent, `quick` forces single-pass.
