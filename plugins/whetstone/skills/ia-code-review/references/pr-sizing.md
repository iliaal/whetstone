# PR sizing and large-diff strategy

## Large diffs (>500 lines)

Review by module/directory rather than file-by-file. Summarize each module's
changes first, then drill into high-risk areas. Flag if the PR should be split.

## Change sizing

Ideal PRs are ~100-300 lines of meaningful changes (excluding generated code,
lockfiles, snapshots). PRs beyond this range have slower review cycles and higher
defect rates. When a PR exceeds this, suggest splitting using one of these
strategies:

- **Stack** -- sequential PRs where each builds on the previous, merged in order.
- **By file group** -- group related files (e.g., model + migration + tests) into separate PRs.
- **Horizontal** -- split by layer (frontend, API, database).
- **Vertical** -- split by feature slice (each PR delivers one user-visible behavior end-to-end).
