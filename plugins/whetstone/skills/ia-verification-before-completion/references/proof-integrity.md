# proof integrity

## The Rule

No completion claims without fresh verification evidence. If the verification command has not been run **immediately before the claim**, the claim cannot be made.

"Should pass", "probably works", and "looks correct" are not verification. Only command output confirming the claim counts (typically exit code 0). For independently established base failures, see [When verification fails](./claims-and-failures.md#when-verification-fails).

Evidence is invalid when the change makes the oracle easier to satisfy instead of making the behavior correct. Never weaken a specification, assertion, test, validator, or acceptance criterion to obtain a pass. Regenerate expected output only after reviewing and justifying the semantic change. Do not hard-code the exercised subject or success path.

Classify proof honestly. Fixtures, mocks, seeded rows, retained captures, and recorded responses can support deterministic tests, but they are not live evidence. Claim live behavior only after a fresh process exercises the intended entry point against runtime-selected or independently varied subjects where that distinction matters.

**Tightening validation on input you cannot read is not covered by green tests.** When a change moves a parser from lenient to strict (`validate=True`, `strict=True`, `errors="strict"`, a tight regex replacing a permissive built-in) and the value comes from a secret store, an environment variable, or a human, the tests construct their input with the canonical encoder and are green by construction: they cannot emit the stray byte the old leniency was absorbing. "It has worked in production for a year" is likewise zero evidence: the leniency is precisely what hid the byte. Pair the strictness with an explicit normalization step and state the coverage gap rather than reporting the change as verified.

When the positive capability is safe, authorized, and in scope, a refusal-only path is incomplete. Verify and report the refusal behavior, but do not close the feature until the positive path works through its intended entry point.

## Pre-Verification Check

Before running verification, check the working tree state: `git status --porcelain`. If there are uncommitted changes unrelated to the current task, handle them first (commit, stash, or acknowledge); verification commits on top of a dirty tree create tangled history.

**Dirty tree + shared-module change → local green is not evidence.** Reproduce on a clean base ([isolated-verification.md](./isolated-verification.md)).

**Check what verification connects to before running it, including the baseline run below.** Before a test suite, migration, seeder, or legacy binary runs for verification, resolve its effective targets: the database URL or `DB_*` values after the test overlay is applied (`phpunit.xml` `<env>`, `.env.testing`, pytest or Jest config, CI env), the queue, cache, and mail drivers, and external API base URLs. Every target must be disposable: a dedicated test database, container, or throwaway schema. The developer's own dev database is local but not disposable, and a shared dev, staging, or production database or service is neither. If any target is not disposable, stop and ask which environment to use; a `RefreshDatabase` or truncating suite with no test-database override, or `migrate:fresh`, destroys the data of the database it reaches. Stop every server or background process the verification started, and say so in the handoff.

**Broad-blast-radius changes need the baseline captured before the first write.** For a dependency bump, framework upgrade, codegen change, or migration, run the repo's validation suite against the existing state first, record the exact command set, and save its output as an artifact: JUnit XML, or the raw runner log including its summary line. Rerun that same set verbatim afterward, with the same config and environment; a post-change run of a *different* command set proves nothing. If the baseline is already red, stop and report before writing anything: starting a migration on a red base makes every later failure unattributable, and a recorded red baseline is one step from "it was already broken, not my problem". This is the one case where the retroactive base-branch proof under When Verification Fails is impractical: a regenerated lockfile does not `git stash` cleanly. Ordinary source edits stay on that retroactive path.

**A framework or dependency upgrade is proven only by a measured before/after on the same tests.**

- **Measured baseline.** The saved artifact above is the baseline. A typed-up table or a remembered pass count is not.
- **Same tests.** Diff the test tree between the base and the upgraded tree (`git diff --stat <base> -- <test paths>`). Deleting, skipping, or marking tests expected-to-fail to get green invalidates the proof. Name every test the upgrade edited in the handoff: a green rerun of edited tests says nothing about the original behavior, and a weakened assertion cannot be detected mechanically; only the fact that the file changed can.
- **Silent deltas.** For each upgrade-guide or changelog entry that changes behavior without a compile, type, or test failure (a changed default, a deprecation that now no-ops or degrades silently, a serialization, encoding, or casting change), point to a test that exercises the affected call site, exists at the base, and passes on both sides. Where none exists, add a characterization test on the base first, then re-capture the baseline and treat that commit as `<base>` for the test-tree diff; otherwise list the entry as an unverified gap.
- Split a move across several major versions, or a runtime plus a framework upgrade, into hops that each go green.

For delegated work: never trust the implementer subagent's own report. Spec compliance and quality are separate concerns; verify both. Confirm via the VCS diff that changes were actually made, then run the verification command directly; never relay the subagent's claim.
