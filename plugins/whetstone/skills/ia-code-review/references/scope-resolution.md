# Scope & comparison-range resolution

Git/`gh` plumbing for setting up a review: deriving the comparison range for a
branch review, and fetching prior discussion before raising findings. The core
file-selection fallback chain stays in the main skill; this covers the two
detailed cases.

Contents: [working-tree safety](#working-tree-safety-never-reorganize-the-users-checkout-to-review) · [branch base](#base-branch-resolution-for-branch-reviews) · [coverage ledger](#review-coverage-ledger) · [prior discussions](#fetching-existing-pr-discussions)

## Working-tree safety: never reorganize the user's checkout to review

A review is read-only on the working tree. Setting up a review must not mutate
what the user has in progress. Before any other setup step, run:

```
git status --short --branch -uall
```

Treat every modified, staged, and untracked file in that output as the user's
work-in-progress, not as clutter to clear. Do **not**, as review setup, run any
of: `git switch` / `git checkout <branch>`, `git reset --hard`, `git clean`,
`git stash` / `git stash -u`, or `gh pr checkout`. Each silently relocates or
destroys uncommitted work.

Moving untracked work "out of the way" is the same interference, not a
safeguard: do **not** copy or move the user's WIP to `/tmp`, a backup dir, or any
location outside the checkout to "protect" it. Relocating someone's uncommitted
work is the same class of harm as stashing it -- it leaves the tree in a state
the user did not create and cannot predict.

If the target diff genuinely requires a different branch or a clean tree, stop
and ask before switching, stashing, resetting, or cleaning. Reviewing a branch
does not require checking it out -- resolve the comparison range and read the
diff range directly (see "Base-branch resolution for branch reviews" below); a
remote branch reads via `git diff <base>...<branch>` without touching the
working tree.

**HEAD-drift guard (when the review ends in a stage/commit/push):** record the
commit before staging and re-check before the write:

```
before=$(git rev-parse HEAD)
# ... review, then stage ...
[ "$(git rev-parse HEAD)" = "$before" ] || echo "HEAD moved since review start -- stop and report"
```

If `HEAD` moved, or commits appeared that the review did not create, stop and
report rather than committing or pushing on top of an unknown state.

## Base-branch resolution for branch reviews

This governs the *comparison range* for a branch review — distinct from the
file-selection chain in the main skill. When the review target is a branch (not a
working-tree diff), run base-branch resolution first; the file-selection
fallbacks are for in-progress local work, where `git diff HEAD` is the correct
command. Do not stitch the two: a branch review needs the merge-base, not the
working-tree delta.

When reviewing a branch (no specific files, no PR), derive the comparison base
via this fallback chain:

1. **If a PR exists for the branch** -- use its base: `gh pr view --json baseRefName --jq .baseRefName`. Authoritative; no further detection needed.
2. **Else infer the default branch**: try `git symbolic-ref --quiet --short refs/remotes/origin/HEAD` (parses to `origin/<name>`). If unset, try `gh repo view --json defaultBranchRef --jq .defaultBranchRef.name`.
3. **Else fallback list**: try `origin/main`, `origin/master`, `origin/develop`, `origin/trunk` in order; pick the first that resolves via `git rev-parse --verify`. Bare-local names are a last resort if no `origin/*` remote ref exists.
4. **Compute the diff base**: `git merge-base HEAD <resolved-base>`. Review the range `<merge-base>..HEAD`, not `HEAD` against the working tree.
5. **Shallow-clone retry**: if `git merge-base` returns nothing and `git rev-parse --is-shallow-repository` is `true`, run `git fetch --unshallow origin` and retry. Document this in the review output so the reviewer knows the comparison range only became available after unshallowing.

**Never fall back to `git diff HEAD`** when base resolution fails -- that hides
all committed work on the branch and reviews only the uncommitted delta. Stop and
ask which base to use instead.

### Stacked branches

When a branch is stacked on another unmerged branch, `git merge-base HEAD
<default-branch>` over-covers -- it sweeps in the sibling branch's commits,
fabricating findings on files this change doesn't touch. Prefer the hosting
platform's authoritative base SHA (PR/MR `base_sha`, or `gh pr diff`) over a
locally computed merge-base. After the run, intersect every finding's path with
the change's `--name-only` set and discard off-scope ones.

## Review coverage ledger

Track mechanical coverage separately from finding quality. Prove only that each selected file received a completed correctness review, not that it is defect-free.

### Build the denominator before filtering

After resolving the comparison range, freeze the original changed-file universe from its name-and-status output. Include added, modified, renamed, copied, and deleted paths. Include untracked files in workspace mode. Only then classify each path as `selected` or `excluded(reason)`.

Tests excluded from deep-review size signals are still part of the universe and
remain selectable. Keep deletion-only changes selectable so removal regressions
can be reviewed against the old side. Exclude only paths outside explicit user
scope or the main skill's declared lockfile, minified/bundled, vendored, and
generated categories. Record the concrete reason; never silently drop an
oversized or unreadable selected file -- mark it failed.

Use one disposition per path:

| Set | Meaning |
|-----|---------|
| `changed` | Original pre-filter universe with path, change status, and workspace diff fingerprint when mutable. |
| `selected` | Files that require a correctness review. |
| `covered` | Selected files actually inspected by their assigned correctness coverage unit. |
| `failed` | Selected files not reviewable, with concrete evidence such as timeout, unreadable input, or context exhaustion. |
| `pending` | Selected files with no terminal disposition yet. |
| `excluded` | Changed files deliberately outside review, with a reason. |

For standard reviews, hold the ledger in context. For persisted `/ia-review`
runs, store the same top-level arrays in transient review scratch state; entries
carry `path` plus `status`/`fingerprint`, `unit`, or `reason` as applicable.
Assign every selected file to exactly one correctness unit, even when multiple
specialist lenses inspect it.

### Reconcile before the verdict

For a frozen branch or commit review, reconcile against the original
name-and-status set. For mutable workspace review, re-enumerate and compare
per-file diff fingerprints immediately before the verdict; add new or changed
paths as pending.

Derive terminal coverage mechanically:

- **complete** -- `selected = covered`, with no failed or pending paths.
- **partial** -- at least one selected path is covered and at least one is failed or pending.
- **failed** -- selected paths exist but none received usable coverage, or scope identity became untrustworthy.
- **skipped** -- no files were selected; report that no review verdict was produced.

Only complete coverage may produce `Ready to merge` or `Ready with fixes`.
Partial or failed coverage forces `Not ready`, independently of finding count.
Always list excluded paths under Residual Risks; explicit exclusion makes scope
truthful, not necessarily safe.

## Fetching existing PR discussions

Before raising findings, reconcile prior review comments so you don't re-raise
issues other reviewers already resolved. Gate the fetch on a presence check to
avoid spawning empty work:

```
gh pr view <pr> --json reviews,comments --jq '(((.reviews // []) | map(select(.state != "APPROVED" or .body != "")) | length) > 0) or (((.comments // []) | length) > 0)'
```

Returns `true` only when at least one substantive review or issue comment exists
(approval-only clicks excluded; null-defensive on PRs with no review array). On
`false`, skip the prior-comments pass entirely. On `true`, fetch the bodies via
`gh api repos/{owner}/{repo}/pulls/{pr}/comments` and reconcile before raising
findings -- prior reviewers may have already resolved issues you'd otherwise
re-raise.
