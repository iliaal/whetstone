# Orchestrated simplification

## Orchestrator Mode (When Chained With Other Skills)

When this skill is invoked by an orchestrator that also runs `ia-code-review`, `ia-writing-tests`, or `ia-verification-before-completion` on the same scope, each sub-skill re-resolving scope independently wastes tokens and risks drift. Avoid this by resolving scope exactly once and passing a canonical block to every sub-skill.

**Resolved scope format**: the orchestrator builds this once, before dispatching any sub-skill:

```

## Resolved scope
Files:
- path/to/file-a.ts
- path/to/file-b.ts

Commit range: HEAD~3..HEAD (or "uncommitted")

Intent: [one-sentence description pulled from the user request or PR description]

Constraints:
- Preserve public API
- No behavior change
- [other constraints specific to this run]
```

Pass this block verbatim to each chained sub-skill as the source of truth for scope. Reuse the block instead of independently resolving the request again. If later edits require a scope change, reconcile the block before continuing.

Assign one final verification owner after all edits are integrated. Honor each sub-skill's documented checks; do not invent suppression flags. The final owner can be the orchestrator or a delegated verifier with access to the integrated files.

Require a verification receipt with the checked revision and worktree identity, relevant file or diff fingerprints for uncommitted changes, executed commands, exit statuses, material output, and coverage gaps. Confirm that the receipt covers the final integrated state and the required checks. Fresh delegated evidence is valid when that correspondence holds; delegation alone does not require a duplicate parent suite. If files change after verification or the receipt is incomplete, rerun the affected checks against the new state. Produce one final report based on the receipt.

This prevents two failure modes: scope drift (sub-skill A simplifies one set of files, sub-skill B reviews a different set) and double work (every sub-skill rediscovers the same facts).
