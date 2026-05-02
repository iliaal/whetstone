# Review Traps Catalog

Concrete review-reasoning failure modes harvested from real Codex cycle disagreements and review post-mortems. Each entry states the Trap (what reviewers do wrong), the Reality (what's actually true), and the Fix (what to do instead). Load this file when running a code review, especially when about to file findings with words like "should", "might", "could break", "what if", or "pattern suggests."

## Reachability before severity

**Trap:** finding a genuine mechanical defect in an internal function (infinite loop, unbounded pointer advance, missing bound check) and filing it as a security issue without verifying that the function is reached from any public API path. Code trace and second-opinion review can both agree on the mechanics while missing that the enclosing dispatch short-circuits before the buggy function runs.

**Reality:** for a finding to be a security issue, an attacker must be able to *reach* the buggy code. Dispatch guards like `if (i <= 0)` upstream, NOTMIME-mode short-circuits, or unreachable conditional branches turn real mechanical defects into dead code from the user-facing API's perspective. Reachability review survives code-trace agreement — two reviewers reading the same function in isolation will both confirm the mechanic and both miss the same dispatch guard.

**Fix:** for every security finding that names a specific internal function, list every caller on every compiled path and trace the conditions under which each call actually fires. Build a real reproducer before filing. For UB-style findings without a sanitizer trap, verify the standard sanitizer toolbox actually covers the UB class — `-fsanitize=pointer-overflow` catches arithmetic wrap past UINTPTR_MAX and NULL-base offsets, not "pointer leaves its referent object." If no sanitizer fires and no crash is reproducible, the finding is spec-level UB, not a security issue.

## Docs-idiom smoke test for API-hardening changes

**Trap:** tightening a public-API method so a previously-swallowed failure now throws. Correctness verified against the call graph and existing tests; canonical documentation example not exercised. Tests pass, the change ships, a user runs the docs example a week later and files a bug.

**Reality:** official documentation shows the idiom users copy. Public APIs carry an implicit contract with the docs, not just with the test suite. "Every test passed" does not prove "every documented usage still works."

**Fix:** for any change to a widely-used public method, find the canonical example in the official docs and run it against the patched build before declaring done. If the harness has the docfork MCP, prefer `search_docs` for the library at the project's pinned version over a raw web grep — it returns versioned official sections, not SEO blog pollution. Otherwise grep the official docs directly (`php.net/manual/en/<class>.<method>.php`, library README, Sphinx docs). Add the docs idiom to the test suite as a standing smoke test.

## Key-vs-label: open three files before flagging

**Trap:** when a string field is passed into a form feeding a `<Select>` whose options use keys, flagging "if the source is a label, the form will submit a label." The assumption isn't verified.

**Reality:** a five-second check of (a) the API resource/DTO, (b) the fixture/mock, (c) the schema (Zod/Pydantic/etc.) usually settles it. If all three say key, the bug didn't exist.

**Fix:** before writing a "key vs label" finding, open the three sources above. Only file if at least one of them passes a label through.

## "Convention is X" from a 3-file sample

**Trap:** reviewing a new file in a populated directory, grepping 2-3 siblings, spotting a pattern, and citing it as the convention. If the sample is small and non-random, the "convention" often isn't one.

**Reality:** directories with 40+ similarly-shaped files frequently have splits. Different authors established different local patterns over time. The 3 files opened happened to use one pattern; the 11+ not opened use another. Both are equally established.

**Fix:** before writing a "inconsistent with convention" finding, grep across the whole directory, not just neighbours. If both patterns have >3 examples, there is no convention — drop the finding. Only cite "convention" when the evidence is overwhelming (say, >80% of the population on one side).

## Consult convention docs BEFORE reading the diff

**Trap:** projects with `agents/*.md`, `CLAUDE.md`, or similar convention docs contain cheap-to-catch rules. Starting review with "look at the diff, see what looks off" misses rules that are in plain sight.

**Reality:** memory-based recall of project conventions is unreliable, including from reviewers who have read the docs before. Rules that were obvious in the convention doc slip through review.

**Fix:** for every diff, identify which area it touches (DB migration, audit trail, routing, auth), open the matching convention doc first, and scan for applicable rules. Treat it like a checklist: rule → check diff → either dismiss or flag. Only after that pre-flight, open the diff.

## Speculative future-design findings on greenfield code

**Trap:** reviewing a brand-new feature with no prior consumers, reaching for "what if later..." findings to look thorough — pagination metadata on fixed-N endpoints, polymorphic ID collision worries on UUID models, hardcoded strings in projects with no i18n. Each dressed up as Medium/Minor but with no concrete failure mode in the diff or its near-term consumers.

**Reality:** greenfield code has no real bugs adjacent to the diff, so the urge to produce a "complete" review surfaces design-future-facing commentary. Our skill explicitly suppresses "generic suggestions without a concrete failure mode" but the rule loses to thoroughness pressure.

**Fix:** before writing a Medium/Minor finding on new code, ask "what specifically breaks today, or which committed near-term consumer breaks?" If the answer is "later, if X is added" or "if a different shape is needed", drop it. Treat a `speculative` classification from a second reviewer as confirmation, not an invitation to debate.

## "Misnamed class" without reading what the type represents

**Trap:** when a class name has a noun like `File` or `Record` and the body manipulates a model with a different surface name (e.g., `DeleteProviderDocumentFileAction` operating on a `Document` model), flagging it as "misnamed". The reasoning is shape-based.

**Reality:** in many codebases the model name *is* the domain entity. `Document` may *be* the file entity (with `storage_path`, `final_path`, `thumbnail_path`). Reading the model for two lines settles it.

**Fix:** before flagging "misnamed" or similar naming critique, open the referenced model and skim the columns/methods. If the model represents the noun in the class name, drop the finding. Naming critiques ungrounded in what the type actually represents are noise.

## Pattern-matching validation from sibling fields

**Trap:** a diff adds a new field that "looks like" an existing one (e.g., `fax` alongside `phone`). Flagging "why doesn't `fax` have the same format rule as `phone`?" The reasoning is analogical.

**Reality:** the project often already has a convention for the new field across other endpoints that differs from the sibling. A 10-second grep settles it.

**Fix:** before flagging "field X should use validation rule Y", grep the codebase for `'X'` across request classes, resources, and forms. If multiple files treat the field the same way the diff does, the diff is following convention — drop the finding. Analogy to a different field is not evidence.

## Consumer doesn't handle new enum case — but does the default break?

**Trap:** a diff adds a new enum case; greenping every consumer that matches on the enum and flagging each one that doesn't include the new case.

**Reality:** the mere absence of a case in a `match` is not a bug. What matters is whether the `default` / fallback path produces a *wrong runtime outcome*. Two patterns to distinguish:

1. `default` short-circuits correctly (returns empty array for a list endpoint, returns `null` for an optional lookup, throws, logs and skips). Absence of the new case is fine.
2. `default` returns an empty result that gets silently forwarded into an update/create/delete, producing 200 OK with no work done. Silent-success bug.

Only pattern 2 is a finding.

**Fix:** for each consumer missing the new case, follow the code path from `default` to the caller's response. If the caller's behavior under `default` is already semantically correct for the new case, drop the finding.

## Paired-enum invariant drift

**Trap:** adding a case to enum A without mirroring it in a semantically-sibling enum B used one ORM layer away. Type system doesn't enforce the pair; CI is green and tests pass; production ships a write-then-read crash.

**Reality:** frameworks let request validation and model casts pick enums independently. Two enums with overlapping but non-identical cases silently drift. A validator using enum A as a superset accepts the new case, persists it, then the model's cast to enum B throws on every subsequent read. The failing layer is nowhere near the change site.

**Fix:** when adding an enum case, grep every `Rule::enum(ThisEnum::class)` and every `ThisEnum::class` cast reference. Check for sibling enums with overlapping cases — paired invariants nothing in the type system protects. If the sibling isn't updated in the same change, write-then-read will break.

## New endpoint that duplicates existing behavior

**Trap:** reviewing a new controller/action/endpoint that does roughly what an existing one already does (destroy a resource, update a resource). Focus pattern-matches to the diff in front of you; the existing implementation is out of mind. You miss that the new endpoint skips guards, policies, soft-delete logic, or cascade handling the existing one already figured out.

**Reality:** existing implementations on the same resource encode hard-won rules about completed-state protection, cross-tenant scope, soft-delete vs force-delete, audit trails, side-effect ordering. A new alternative endpoint is a high-probability regression vector unless it explicitly reuses the existing flow.

**Fix:** before writing findings on a new destroy/update/create endpoint, grep for existing destroy/update/create methods on the same resource. Read them in full. Diff every guard and side effect against the new implementation. What's missing is the finding.

## Confirmation-style findings dressed up as nits

**Trap:** writing "nit: I noticed X is pre-existing behavior and the diff doesn't touch it, just confirming the intent is Y." Two signals that the finding has slipped from actionable into noise: (1) the body explicitly notes the behavior is unchanged by the diff, (2) the ask is for the author to confirm intent rather than propose a change.

**Reality:** review is an author-facing channel. If the finding has no change for the author to make, it's not a comment — it's a note-to-self. Posting inflates review size, dilutes signal of the real findings, and trains the author to skim.

**Fix:** before posting a nit, ask "what action does this request?" If the answer is "confirm this is intentional", delete the comment. Keep the observation in internal review notes if it matters.

## Hypothetical queue/cache concerns without grounding

**Trap:** enum renames and schema migrations often raise "queue jobs will break on deserialization" or "cached values will mismatch" concerns. Valid classes of risk, but the review comment needs to point to an actual job/cache site that serializes the affected value — otherwise it's a template concern, not a finding.

**Fix:** before flagging a queue/cache concern, grep for jobs/cache writes that include the affected type as a serialized field. If no such site exists in the diff or in grep results, drop the concern or explicitly label as hypothetical ("if any jobs serialize X directly, this will break — we didn't find any").

## Defensive nit not evidenced by data already flowing the same pattern

**Trap:** drafting a defensive finding ("what if `documents` is `''`? `json_decode` returns null and `foreach (null)` errors") on a code path where the same construct has been used by N prior migrations against the same tables in production without incident.

**Reality:** the hypothetical edge case isn't in the data, and prior migrations are positive evidence that it isn't. If the convention itself is wrong, fix it as a separate cross-cutting cleanup.

**Fix:** before flagging a defensive nit, grep for the same pattern in adjacent code. If three prior migrations use the identical pattern over the same tables without incident, drop the finding.

## Findings on lines outside the MR diff

**Trap:** reading a new file in a diff, flagging something in *surrounding* code that was already on the base branch. The reviewer sees the guard/handler/early-return in context and assumes it's part of the change.

**Reality:** many code-hosting platforms reject comments anchored to lines outside the diff (GitLab DiffNote, GitHub inline comments on unchanged lines). Even when accepted, the finding is out-of-scope for the current change.

**Fix:** before drafting a comment, confirm the target line is actually inside the MR's diff. `git diff <base>...<head> -- <file>` is authoritative. If the line isn't in the hunks, either drop the finding or reframe as follow-up: "this behavior is pre-existing but worth addressing separately" — raise as a separate issue, not an inline comment.

## Cross-repo contract claims need current remote state

**Trap:** when a review cites cross-repo backend contracts (routes, schemas), the reviewer's view of the other repo is whatever's in their local working tree — which may be stale. A confident "this endpoint doesn't exist" can be wrong if the companion change has already merged on `origin/develop`.

**Fix:** when making a cross-repo contract claim, verify with `git show origin/develop:path/to/file` before acting. If local is behind, `git fetch` and re-read. When handing a diff to a subagent for review, note which SHA the review is supposed to be against; LLM tools that supplement from the filesystem will otherwise read pre-change state.

## Language-specific gotchas reviewers re-discover

**PHP 8 property-access on null does NOT fatal.** `null->foo` emits a Warning and evaluates to `null`, which the `??` operator catches. Only method calls (`null->foo()`) throw. Before flagging `?->` (null-safe operator) as a required fix for "potential 500", confirm the suggestion changes runtime behavior beyond warning-level log noise.

**PHP `json_encode` comparison is type-safe.** `json_encode(1)` vs `json_encode("1")` produces `1` vs `"1"` — distinguishable. `json_encode($a) !== json_encode($b)` is a valid deep-equality check for JSON-serializable values.

**Laravel 11+ `HasUuids::newUniqueId()` returns `Str::uuid7()` (time-ordered).** `latest('id')` on a UUIDv7 PK sorts chronologically — the "UUIDs sort lexicographically, not chronologically" trap only applies to Laravel ≤10 or models overriding `newUniqueId()`.

**Laravel 11+ `HasOneOrMany::limit()` in an eager-load is per-parent, not global.** `->with(['relation' => fn ($q) => $q->limit(N)])` uses `groupLimit` when `$this->parent->exists` is false (eager-load path), which the older "this limits rows total, not per parent" finding no longer applies to.

When flagging a language/framework idiom as broken, first check the vendor source for the current version's behavior. Patterns that were traps in v10 often aren't in v11. If the harness has the docfork MCP, run `search_docs` against the library at the project's pinned version (`composer.json` / `package.json` / `requirements.txt` / `go.mod`) before filing — see `language-profiles.md` "Verifying framework idioms before flagging" for the exact protocol.

## Same-name symbols across Enum / Model / DTO / Request

**Trap:** a codebase can have two classes with the same short name in different namespaces (e.g., `App\Enums\Foo\Bar` + `App\Models\Foo\Bar`). Citing a validation/serialization rule tied to "ClassName" without verifying which namespace binds. Result: mechanism wrong even if conclusion right.

**Fix:** when asserting "X is validated via `Rule::enum(Y::class)`" or similar, open the actual validator/request/casts and read the imports. Confirm which FQN is in scope. If the symbol is ambiguous, say so in the finding and defer the mechanism claim.

## Column-level rename misses JSON-embedded values

**Trap:** reviewing a migration that renames `foo = 'a'` to `foo = 'b'`, checking every table with a `foo` column and declaring the rename complete. In codebases that also store the same semantic value inside JSON columns (requirement payloads, config snapshots), the column-level audit misses the JSON sites.

**Fix:** before declaring a column-level rename complete, grep the full migration history for past renames of the same semantic. Past rename migrations are the best index of where the value lives — both columns *and* JSON payloads.

