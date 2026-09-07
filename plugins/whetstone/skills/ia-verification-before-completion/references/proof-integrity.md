# proof integrity

## The Rule

No completion claims without fresh verification evidence. If the verification command has not been run **immediately before the claim**, the claim cannot be made.

"Should pass", "probably works", and "looks correct" are not verification. Only command output confirming the claim counts (typically exit code 0). For independently established base failures, see [When verification fails](./claims-and-failures.md#when-verification-fails).

Evidence is invalid when the change makes the oracle easier to satisfy instead of making the behavior correct. Never weaken a specification, assertion, test, validator, or acceptance criterion to obtain a pass. Regenerate expected output only after reviewing and justifying the semantic change. Do not hard-code the exercised subject or success path.

Classify proof honestly. Fixtures, mocks, seeded rows, retained captures, and recorded responses can support deterministic tests, but they are not live evidence. Claim live behavior only after a fresh process exercises the intended entry point against runtime-selected or independently varied subjects where that distinction matters.

**Tightening validation on input you cannot read is not covered by green tests.** When a change moves a parser from lenient to strict (`validate=True`, `strict=True`, `errors="strict"`, a tight regex replacing a permissive built-in) and the value comes from a secret store, an environment variable, or a human, the tests construct their input with the canonical encoder and are green by construction -- they cannot emit the stray byte the old leniency was absorbing. "It has worked in production for a year" is likewise zero evidence: the leniency is precisely what hid the byte. Pair the strictness with an explicit normalization step and state the coverage gap rather than reporting the change as verified.

When the positive capability is safe, authorized, and in scope, a refusal-only path is incomplete. Verify and report the refusal behavior, but do not close the feature until the positive path works through its intended entry point.

## Pre-Verification Check

Before running verification, check the working tree state: `git status --porcelain`. If there are uncommitted changes unrelated to the current task, handle them first (commit, stash, or acknowledge) -- verification commits on top of a dirty tree create tangled history.

**Dirty tree + shared-module change → local green is not evidence.** Reproduce on a clean base ([isolated-verification.md](./isolated-verification.md)).

**Broad-blast-radius changes need the baseline captured before the first write.** For a dependency bump, framework upgrade, codegen change, or migration, run the repo's validation suite against the existing state first and record the exact command set. Rerun that same set verbatim afterward -- a post-change run of a *different* command set proves nothing. If the baseline is already red, stop and report before writing anything: starting a migration on a red base makes every later failure unattributable, and a recorded red baseline is one step from "it was already broken, not my problem". This is the one case where the retroactive base-branch proof under When Verification Fails is impractical -- a regenerated lockfile does not `git stash` cleanly. Ordinary source edits stay on that retroactive path.

For delegated work: never trust the implementer subagent's own report -- spec compliance and quality are separate concerns, verify both. Confirm via the VCS diff that changes were actually made, then run the verification command directly; never relay the subagent's claim.
