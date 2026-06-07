# Scope & comparison-range resolution

Git/`gh` plumbing for setting up a review: deriving the comparison range for a
branch review, and fetching prior discussion before raising findings. The core
file-selection fallback chain stays in the main skill; this covers the two
detailed cases.

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
