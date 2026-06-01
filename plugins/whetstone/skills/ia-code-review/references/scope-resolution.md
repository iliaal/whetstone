# Scope & comparison-range resolution

Git/`gh` plumbing for setting up a review: deriving the comparison range for a
branch review, and fetching prior discussion before raising findings. The core
file-selection fallback chain stays in the main skill; this covers the two
detailed cases.

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
