# PR sizing and large-diff strategy

## Large diffs (>500 lines)

Review by module/directory rather than file-by-file. Summarize each module's
changes first, then drill into high-risk areas. Flag a split only when a gate from the Change sizing section below applies.

Each module-scoped pass receives the full current file bodies for its assigned
files, not diff-hunk slices; in deep review, carry them in the `FILES:` field of
the specialist prompt template in [deep-review.md](./deep-review.md) (Agent
Prompt Template). Unchanged code around a hunk (callers, guards,
error paths) is authoritative context; a pass fed only hunks reports guards that
moved as missing and never sees the call sites the diff did not touch.

## Change sizing

Ideal PRs are ~100-300 lines of meaningful changes (excluding generated code,
lockfiles, snapshots). PRs beyond this range have slower review cycles and higher
defect rates. Treat the range as a review-cost signal, and count it only when a
person must review the change; agent review reads the same total diff however
the work is split. Size alone is not a reason to split.

Suggest a split only when a concrete gate exists: a part needs an independent
deploy or rollback, a part needs a separate reviewer or owner, or isolating a
risky part keeps it from blocking or endangering the rest. Name the gate in the
suggestion. When a gate applies, split using one of these strategies:

- **Stack**: sequential PRs where each builds on the previous, merged in order.
- **By file group**: group related files (e.g., model + migration + tests) into separate PRs.
- **Horizontal**: split by layer (frontend, API, database).
- **Vertical**: split by feature slice (each PR delivers one user-visible behavior end-to-end).
