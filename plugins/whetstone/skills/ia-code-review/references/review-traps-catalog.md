# Review Traps Catalog

Concrete review-reasoning failure modes harvested from real Codex cycle disagreements and review post-mortems. Each entry states the Trap (what reviewers do wrong), the Reality (what's actually true), and the Fix (what to do instead). Load this file when running a code review, especially when about to file findings with words like "should", "might", "could break", "what if", or "pattern suggests."

## Reachability before severity

**Trap:** finding a genuine mechanical defect in an internal function (infinite loop, unbounded pointer advance, missing bound check) and filing it as a security issue without verifying that the function is reached from any public API path. Code trace and second-opinion review can both agree on the mechanics while missing that the enclosing dispatch short-circuits before the buggy function runs.

**Reality:** for a finding to be a security issue, an attacker must be able to *reach* the buggy code. Dispatch guards like `if (i <= 0)` upstream, NOTMIME-mode short-circuits, or unreachable conditional branches turn real mechanical defects into dead code from the user-facing API's perspective. Reachability review survives code-trace agreement — two reviewers reading the same function in isolation will both confirm the mechanic and both miss the same dispatch guard.

**Fix:** for every security finding that names a specific internal function, list every caller on every compiled path and trace the conditions under which each call actually fires. Build a real reproducer before filing. For UB-style findings without a sanitizer trap, verify the standard sanitizer toolbox actually covers the UB class — `-fsanitize=pointer-overflow` catches arithmetic wrap past UINTPTR_MAX and NULL-base offsets, not "pointer leaves its referent object." If no sanitizer fires and no crash is reproducible, the finding is spec-level UB, not a security issue.

## Docs-idiom smoke test for API-hardening changes

**Trap:** tightening a public-API method so a previously-swallowed failure now throws. Correctness verified against the call graph and existing tests; canonical documentation example not exercised. Tests pass, the change ships, a user runs the docs example a week later and files a bug.

**Reality:** official documentation shows the idiom users copy. Public APIs carry an implicit contract with the docs, not just with the test suite. "Every test passed" does not prove "every documented usage still works."

**Fix:** for any change to a widely-used public method, find the canonical example in the official docs and run it against the patched build before declaring done. If the harness has the Context7 MCP, prefer `query-docs` (after `resolve-library-id`) for the library at the project's pinned version over a raw web grep — it returns versioned official sections, not SEO blog pollution. Otherwise grep the official docs directly (`php.net/manual/en/<class>.<method>.php`, library README, Sphinx docs). Add the docs idiom to the test suite as a standing smoke test.

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

**PHP `preg_match` returns `false`, not `0`, on a PCRE engine error.** Exhausting `pcre.backtrack_limit` (default 1,000,000) is an error, so a plain truthiness test reads a correct subject as unmatched; a lazy `.*?` before an end anchor reaches that limit at around a megabyte of subject. Distinguish `false` from `0` and check `preg_last_error()`; the fix is usually a greedy `.*`.

**PHP `empty()` as the absence test collapses an empty array into "not submitted".** `empty([]) === true`, so a partial-update endpoint written as `empty($data['key']) ? null : map(...)`, with the updater guarding `if ($dto->key !== null)`, cannot distinguish a client sending `{"key": []}` to mean "none" from a client omitting the key. Every partial update works and only the clear-all affordance breaks: 200 returned, nothing written, and the refetch restores what the user just deleted. `isset()` and `?? null` distinguish a submitted empty array from absence, but conflate a submitted null with absence; `array_key_exists` distinguishes presence even for null. `empty()` and plain truthiness collapse empty arrays and other falsy values (`0`, `"0"`, and `""`); objects remain truthy. Bound the finding to the remove-all case, since removing *some* items works, and attack the remedy before proposing it: letting `[]` through starts deleting on a payload that previously did nothing, so count the mapping function's callers, confirm the sync path survives an empty array, check whether an existing test pins `[]` as "unchanged", and sweep the request pipeline (`prepareForValidation`, serializer defaults, `array_filter`, `?? []`) for anything upstream that can synthesise `[]` from something that was not the client saying "none".

**Laravel 11+ `HasUuids::newUniqueId()` returns `Str::uuid7()` (time-ordered).** `latest('id')` on a UUIDv7 PK sorts chronologically — the "UUIDs sort lexicographically, not chronologically" trap only applies to Laravel ≤10 or models overriding `newUniqueId()`.

**Laravel 11+ `HasOneOrMany::limit()` in an eager-load is per-parent, not global.** `->with(['relation' => fn ($q) => $q->limit(N)])` uses `groupLimit` when `$this->parent->exists` is false (eager-load path), which the older "this limits rows total, not per parent" finding no longer applies to.

When flagging a language/framework idiom as broken, first check the vendor source for the current version's behavior. Patterns that were traps in v10 often aren't in v11. If the harness has the Context7 MCP, run `query-docs` (after `resolve-library-id`) against the library at the project's pinned version (`composer.json` / `package.json` / `requirements.txt` / `go.mod`) before filing — see `language-profiles.md` "Verifying framework idioms before flagging" for the exact protocol.

## Same-name symbols across Enum / Model / DTO / Request

**Trap:** a codebase can have two classes with the same short name in different namespaces (e.g., `App\Enums\Foo\Bar` + `App\Models\Foo\Bar`). Citing a validation/serialization rule tied to "ClassName" without verifying which namespace binds. Result: mechanism wrong even if conclusion right.

**Fix:** when asserting "X is validated via `Rule::enum(Y::class)`" or similar, open the actual validator/request/casts and read the imports. Confirm which FQN is in scope. If the symbol is ambiguous, say so in the finding and defer the mechanism claim.

## Column-level rename misses JSON-embedded values

**Trap:** reviewing a migration that renames `foo = 'a'` to `foo = 'b'`, checking every table with a `foo` column and declaring the rename complete. In codebases that also store the same semantic value inside JSON columns (requirement payloads, config snapshots), the column-level audit misses the JSON sites.

**Fix:** before declaring a column-level rename complete, grep the full migration history for past renames of the same semantic. Past rename migrations are the best index of where the value lives — both columns *and* JSON payloads.

## Findings resting on an unverified absence

**Trap:** filing a finding whose load-bearing claim is a negative — "this symbol/handler/path doesn't exist" — based on a subagent's confident report, or on a hit from a broad/alternation grep pattern that actually matched other lines.

**Reality:** proving absence needs whole-search-space coverage, which under-searching fakes. A subagent's confident negative is its least reliable output; a broad pattern that returned lines proves only that the pattern matched something, not that the exact symbol is missing. Positive findings ("here it is at file:line") are trustworthy; negatives are not symmetric and must be re-derived.

**Fix:** before any finding depends on an absence, check it directly: read the region, or grep the *exact* symbol expecting zero lines. Re-derive every negative that arrived second-hand.

## Regression claims without a baseline read

**Trap:** calling a behavioral change a regression from the diff hunk alone — the removed lines look like a dropped feature, so the finding says "this removes X".

**Reality:** a re-spec may have intentionally redefined the contract (its description, not the OLD code, is the oracle); a dropped branch may have been a latent bug; a sibling may have always omitted the field. Conversely, pre-existing code outside the diff *is* this change's responsibility when the new feature makes a previously-invisible defect user-visible — frame that as introduced here, not a follow-up.

**Fix:** read the pre-change file at the base (`git show <base>:<file>`), not just the diff hunk, before filing a regression. When a regression is *confirmed* against the baseline, cite the introducing commit (SHA, author — via `git blame` or `git bisect`) as part of the finding's evidence, not just the symptom.

## Mirror bug on widened/narrowed keys and guards

**Trap:** accepting a fix that widens, narrows, or loosens a match key, dedup key, or guard because it demonstrably closes the reported failure.

**Reality:** the change re-opens failure along the axis it now ignores: closing duplicate-on-no-match by widening a key opens false-merge-on-shared-key; loosening a guard to admit a good value admits bad ones too; tightening a matcher to drop a bad value drops legitimate ones.

**Fix:** name one concrete opposite-defect case (real inputs, real key values) along the ignored axis before accepting the change. If no such case can be constructed, state that explicitly in the review.

## Hide/filter/redact checked on one projection only

**Trap:** verifying that a hide/filter/redact change removes the entity from the primary list and stopping there.

**Reality:** responses surface the same entity through sibling fields — the structured list AND the raw documents/files, the array AND its `*_count`/`*_ids`/`total`, the summary projection AND the detail projection. A filter applied to one projection leaks the entity via a sibling field on the same response.

**Fix:** enumerate every field in the response that surfaces the same entity, and require a test asserting the hidden entity is absent from *each* surfacing field, not just the primary list.

## Self-dismissal wording that gets findings dropped

**Trap:** wording a real finding with softeners — "INFO only", "no action required", "optional cleanup", "operational tradeoff".

**Reality:** a downstream validator or second reviewer reads those phrases as a self-dismissal and drops the finding regardless of real severity. Severity tags (`[Minor]`, `[FYI]`) are fine; dismissive prose is not. Hypothetical impact ("potentially hours") is easy to wave off.

**Fix:** anchor severity in concrete constants and numbers from the code ("20-minute floor", "every inactive bar") — a named constant is harder to wave off than a hypothetical. State the severity tag and stop; no minimizing commentary.

## A defect demoted to "considered, not raised" was never counted

**Trap:** noticing one instance of a mechanical defect -- a stranded docblock, a stale comment, a magic literal, a missing `@param`, a duplicated predicate -- judging it too small for a thread, and putting it in the round's summary as a "considered, not raised" line.

**Reality:** the demotion is a claim about the *count*, made without counting, and deciding the item is too small is exactly what removes the reason to measure it. The sweep is usually one command and was runnable before the demotion. N=1 is hygiene; N=8 is a thread, and the extra instances need not be the same defect in kind -- among eight stranded docblocks, two documented behavior the change had removed, which invites the next reader to restore it.

**Fix:** before writing a mechanical defect into a summary line, run the sweep for its siblings at head *and* at base. The count decides the severity; the base run separates "this change introduced eight" from "the file was always like this"; and the sweep's output is the note, because an author fixes a table faster than a description.

## Plan-mandated defects vs. documented overrides

**Trap:** treating everything the plan, task brief, or convention doc blesses as beyond review — or the opposite, re-raising a concern the project has explicitly overridden.

**Reality:** two distinct cases hinge on the rationale. A rationale-backed override in `CLAUDE.md`, `AGENTS.md`, or an inline comment ("we allow X because Y") is owner-blessed: honor it, don't re-raise the concern or work around it "just to be safe"; if the override lacks a rationale, suggest documenting one — don't argue the rule. But a plan or task brief that *mandates something the rubric calls a defect* (a test that asserts nothing, verbatim duplication of a logic block) is not self-justifying — the plan does not grade its own work.

**Fix:** honor rationale-backed overrides. Report plan-mandated defects as findings labeled "plan-mandated" for the human to adjudicate — don't silently approve them as spec-required and don't silently "fix" them.

## Error-string match against uncaptured subprocess output

**Trap:** a finding (or a test) that asserts on a captured error string from a spawned subprocess -- `expect(err.message).toContain("ENOENT")`, `assert "syntax error" in str(exc)`, matching `$result->getMessage()` against a tool's diagnostic. The reviewer accepts it as a real check on the program's output.

**Reality:** when a child process is spawned with `stdio: 'inherit'` (Node), `subprocess.run(...)` without `capture_output=True` (Python), `passthru`/`proc_open` with inherited descriptors (PHP), or any pipe the parent never reads, the child's diagnostics stream straight to the terminal -- they never land in the exception. `error.message` then holds only the **command line** ("Command failed: tsc --noEmit"), not the program's actual output. The matcher matches (or misses) the command string, so the assertion passes or fails for a reason unrelated to what the subprocess printed. A test that "checks the compiler reported an error" actually checks that the word appears in the invocation.

**Fix:** when a finding or test matches on an error string from a subprocess result, trace how the child's stdout/stderr is captured before trusting the match. Confirm the spawn captures output (`stdio: 'pipe'` / collecting `child.stderr`; `capture_output=True` or `stderr=PIPE`; `2>&1` into a read buffer; `proc_open` with pipe descriptors the parent reads) and that the matched string is asserted against *that* captured stream, not against `error.message`/the command line. If the output is inherited or uncaptured, flag the assertion as matching the command string rather than the program output -- it passes for the wrong reason. Suggest asserting on the captured stream, or on exit code when only success/failure matters.


## Size-capped buffer that then parses what it kept

**Trap:** a stream handler that caps growth in place -- `if (data.length < maxSize) data += chunk;`, `if len(buf) < LIMIT: buf += chunk` -- read as a correct bound on memory, then followed by a parse of `data`.

**Reality:** the cap bounds memory and silently truncates. Once the limit is hit, later chunks are dropped and the handler parses the prefix it happened to keep. A truncated JSON prefix usually throws, so the bug arrives disguised as a parse failure; a truncated NDJSON, CSV, or log buffer parses cleanly as a *shorter valid document*, and no caller can tell a 3-record payload from a 3000-record one. Dropping chunks without draining the stream also hands the writer an `EPIPE`.

**Fix:** on overflow, set a rejected flag, discard the buffer, return the empty or error value, and surface the overflow on stderr -- never parse a prefix. Keep consuming and discarding the stream so a finite writer can finish. When reviewing, trace what happens to the buffer *after* the cap fires; that the cap exists is not the question.

## Exhaustive primitive-hit accounting

**Trap:** grepping for a dangerous primitive (unsafe memory op, raw SQL build, unchecked cast) across a large diff or codebase, reading the first handful of hits, forming an opinion, and stopping there.

**Reality:** a sampled pass misses the one exploitable hit among forty safe ones, and there is no record of which hits were never opened. Every hit needs an explicit disposition, not a vibe.

**Fix:** for every primitive grep, assign each hit one of four dispositions before writing the review: safe by construction, mitigated upstream, a finding, or needs-trace. If a wrapper expands to several call sites, account for the wrapper call and its underlying primitive sites separately. An unaccounted-for hit is a gap to close, not a rounding error.

## Vendored or submodule code is not automatically out of scope

**Trap:** skipping review of a directory named `vendor/`, `third_party/`, or a Git submodule on the assumption that the directory name settles ownership.

**Reality:** modified vendored code is first-party and carries the same review obligation as any other first-party file. Only unmodified third-party code stays dependency code — and even then the host's bridge into it (the call site, the wrapper, the size conversion) is first-party and reviewable. A defect whose only location is inside a Git submodule, reachable solely behind a gitlink, belongs to that submodule's own repository, not the host's.

**Fix:** before excluding a path from review, check whether this repository has modified it, not just where it lives. Never file a finding whose location exists only behind a gitlink; trace host-bridge reachability into unmodified third-party code instead, and treat a known upstream issue there as prior art, not a new finding.

## Destructive replace on an empty result

**Trap:** a sync, import, or report job that deletes existing rows then reinserts from a source response, reviewed only for whether the reinsert logic is correct. The delete step is treated as safe because "if the source has zero rows, the reinsert is correctly empty too."

**Reality:** the job cannot distinguish *confirmed empty* (the source explicitly answered "zero rows") from *could not check* (an auth failure, a timeout, or a malformed response deserialized to an empty list). The failure shape recurs: an upstream 401 becomes an empty array, the empty array is read as "zero rows," and the job wipes every good row in place of the rows it failed to fetch.

**Fix:** fail the job on any non-success status before the destructive step. Require the source to assert emptiness explicitly — a count or checksum, not merely an empty array. Make the replace transactional so a failed reinsert rolls back the delete instead of leaving the table empty.

## A zero-result search needs a positive control

**Trap:** reading an empty result from a grep, a structured extraction, or a delegated sweep as evidence that the subject is absent.

**Reality:** every silent failure of the search produces the same empty output as a true negative. `cmd || echo "none found"` cannot distinguish exit 1 from exit 129 -- a pattern starting with `-` parses as an option and needs `-e`. `git grep <rev>` scopes to the shell's working directory, so an earlier `cd` re-scopes every later search, while `git show <rev>:<path> | grep` is immune. A structured extraction (`jq`, a JSON comprehension) addressing the wrong nesting level returns a measured-looking 0. Other producers of the same zero: a pipeline truncated by a pager or `head`, a line-oriented pattern against a construct formatted across lines, a member inherited from an ancestor class, a file the tool classified as binary and silently suppressed, a directory the scanner excludes, and an invocation that lives in another repository.

**Fix:** before concluding absence, run a positive control on a token known to be present, in the same command shape, flags, and working directory. Read the paths, not the count, on any sweep whose pattern also appears in prose -- documentation prescribing the sweep self-matches. Print the row count beside the rows. A symbol visibly present in a file already read and globally absent from the search is a broken oracle, never a discovery.

## A guard imported at one site leaves its siblings unguarded

**Trap:** accepting a fix, cap, or validation because it is correct at the site it touches.

**Reality:** guards arrive one site at a time. A cap added to one allocator leaves the neighbour unbounded; a fix naming two members of a family skips the third; the skipped sibling can carry an extra defect of its own.

**Fix:** read the fix commit's changed-file list, grep every sibling for the same call or shape, and give each an explicit disposition. Before proposing the same guard to a sibling, check that its call site supports it -- a cleanup-on-failure guard needs an exclusive-creation signal.

## A derived constant is cleared by its arithmetic, not by the dimension it guards

**Trap:** a diff introduces a magic number and, unusually, shows its work -- a docblock or config comment derives it ("the tightest per-provider throttle is 10/min and a job gets 15 attempts, so 10 x 15 = 150"). Every term is checkable at head, so each one gets checked, all of them hold, and the constant is recorded as cleared.

**Reality:** the derivation produces one quantity and the guard compares a different one. Same units, different dimension: the derived quantity was *how deep a queue one job survives*, while the guard reads `if ($requested > $cap)` where `$requested` is this invocation's candidate count. A per-call cap on a cumulative hazard is defeated by repetition, so the number can be perfectly derived and still not bound the thing it was derived against. Input verification is what suppresses the question -- the checks ran and came back clean, and a well-reasoned derivation reads as a sign the author thought about the hazard rather than a prompt to reopen it. A verified input can also be a *shared* budget: confirming that a job gets 15 attempts does not entitle this derivation to all 15 when cooldown waits and single-flight waits claim the same ceiling.

**Fix:** for any guard shaped `if ($measured OP $CONST)` where `$CONST` arrives with a derivation, write two sentences before accepting it -- what the derivation produces, in words, with its scope; and what `$measured` holds at that line, in words, with its scope. If the scopes differ (per-call vs cumulative, per-entity vs global, per-window vs total), the guard does not bound the derived hazard however sound the arithmetic; then name what reopens the gap: repetition, concurrency, or a second producer writing the same resource. Check each input for other claimants before granting the derivation the whole budget. When the answer is repetition, read the text that tells the user what to do after a refusal -- copy instructing them to retry with a narrower filter builds exactly the depth the cap exists to prevent, and it is invisible from the file the guard lives in.

## Adding a member to a shared contract breaks outside the changed file set

**Trap:** adding a method to an interface, abstract class, trait, or protocol and scoping the type gate to the touched files.

**Reality:** the breakage is in untouched implementers, often a load-time fatal, and test doubles are the highest-yield location. The cross-branch variant -- one branch adds the member, another adds an implementer -- merges clean and fails to load.

**Fix:** enumerate implementers at head across source *and* test directories, and run the gate over the untouched ones. For the cross-branch case, list the other live heads, compose the merge in a scratch worktree, and load the class, with a positive control.

## A fix extends a kind-keyed allow-list by exactly the kind the reproducer named

**Trap:** accepting a one-member addition to an allow-list keyed on a node kind or other discriminator, because the reproducer it closes is real.

**Reality:** the allow-list encodes an invariant, and every member sharing that invariant shares the defect. A helper refactor has the same shape: it migrates the call sites its author listed, and the one it missed still runs the old inline form.

**Fix:** state the invariant, enumerate the dispatch family against it, and require every member covered in the same commit and the same test.

## A comment that justifies an omission has no code to re-derive it from

**Trap:** accepting "X is deliberately not redone here, because the checks above only read immutable values" -- or "safe to cache, inputs are immutable", "no lock needed, write-once" -- as settled.

**Reality:** the clause enumerates what the current code reads, and a later commit adds a member that breaks it silently. A comment describing what code *does* gets re-derived by the next reader; a comment explaining why something is *not* done is a terminal answer nobody re-checks. A revert has the same effect, leaving behind the rationale prose the reverted fix was born with.

**Fix:** when a diff adds a validation, guard, or filter, grep the file for sentences characterizing what "the checks above" read. When a diff edits a docblock stating a precondition, diff the sentence itself. When a guard changes, expect the docstring stating its contract to be out-of-hunk.

## Policy comments are owner-blessed; factual comments are not

**Trap:** treating every comment inside the diff as baseline truth, including one that asserts something about the world outside the repository.

**Reality:** the two kinds behave differently. A comment recording a *policy decision* ("we allow X because Y") is owner-blessed and stays honored -- see "Plan-mandated defects vs. documented overrides". A comment asserting a *fact about something outside the repository* ("the SDK emits a loose union", "the backend hasn't shipped this yet") is the most stale-prone artifact in the tree, and it self-injects into every reviewer who reads the diff, so unanimity around it proves nothing.

**Fix:** make the external-fact comment the claim under test and settle it against the installed dependency or the remote's current state. When a diff *removes* a workaround together with its rationale comment, weight the removal: the author deleting it has usually re-checked the premise more recently than whoever wrote it.

## Full-replace payload lifted from an older sibling migration

**Trap:** approving a data migration whose stated purpose is "swap one validator" because the replacement payload is internally consistent.

**Reality:** the payload was cloned from an earlier migration and edited by one line. Every migration touching the same key since is reverted the moment the full replace runs, and deleted values come back. No concurrency is involved, and no test covers it because the store is absent from tests.

**Fix:** compare the payload against the row's *current* state, walk every migration on the same key since the snapshot date, and require read-modify-write for a single-field change. A one-line motivation implemented as a whole-object rewrite is the tell.

## Stakes keywords fired by prose that documents the hazard

**Trap:** running a risk-triage grep (migration, `DROP`, `DELETE`, `rm -rf`) over a diff that is mostly markdown, and escalating on hit count.

**Reality:** a knowledge base about destructive operations contains every destructive keyword because it documents them.

**Fix:** evaluate risk triggers against executable files only. A reference-integrity sweep over the same diff must exclude provenance lines (`Absorbed:`, `Supersedes:`) or drown in them -- the surviving dangler hides in an example citation inside prose.

## A static reviewer's verdicts are routing, not conclusions

**Trap:** reading a static or LLM reviewer's "Clean" as an all-clear and its "Critical" as a confirmed defect.

**Reality:** on a churn hotspot a confident "Clean" is low-confidence evidence of absence -- it names the path it did not trace -- and a confident "Critical" is scrutiny routing until a reproducer runs. Sequence-dependent defects (use-after-free across an ownership boundary, reentrancy, state-machine preconditions) sit above the ceiling of read-and-reason review even with perfect file coverage.

**Fix:** treat each verdict as a queue position. Require a reproducer before a "Critical" becomes a finding, and route the sequence-dependent classes to a fuzzer under sanitizers instead of widening the static pass.

## A wait-for-steady-state call is not a deploy gate

**Trap:** accepting -- or demanding -- a "wait until the service is stable" call as the gate that proves a deployment succeeded.

**Reality:** a waiter asserts the service settled, never that the new revision is running. Where the platform auto-rolls-back a failed deployment, the scenario the gate was added to catch is the one that makes it pass: the bad revision is reverted, the service stabilises on the old image, and the waiter returns success.

**Fix:** read the rollback configuration before accepting the gate *or before flagging its absence*. When rollback is on, gate on the identity of the running revision rather than on stability.

## "The gate is already red on the base branch" is one query away

**Trap:** accepting an author's claim that a failing job also fails on the base branch, and dropping the finding on it.

**Reality:** the claim is usually sincere and still wrong, because the author's machine builds against a different artifact than CI does (a regenerated contract, a different config source). One error in the trace against several in the author's account is the tell, and an error citing a line the change itself added settles it.

**Fix:** list the base branch's recent pipelines, confirm the specific job *ran* rather than being skipped by a path filter, and compare its failures against the ones on the head.

## Posting a remedy without replaying the trigger through it

**Trap:** posting a finding that ships a suggested fix as soon as the defect claim is evidenced.

**Reality:** such a finding carries two claims, and only the defect claim gets graded. A `valid` verdict on the defect lends the fix its credibility, and the author implements it verbatim. Remedies reproduce the bug routinely -- one positional comparison swapped for another, a guard that breaks a co-tenant caller, a DOM toggle inert against the element's actual classes. A partially-correct remedy launders the half it does not fix. Executed evidence for the defect claim feels finished, which is exactly why the check on the fix gets skipped.

**Fix:** run the finding's own trigger input through the suggested fix before posting, at every severity. Each part of a multi-part remedy needs its own run; a guard-shaped remedy copied from a sibling needs one structural check -- does the guard read state that survives the failure it guards against? When one remedy covers N findings, replay it against each failure case. If the harness is gone, post the claim alone. Cold-read the new mechanism the fix ships and give its defects their own severity.

## Writing a remedy looser than the finding

**Trap:** wording the fix suggestion more loosely than the mechanism sentence that motivated it.

**Reality:** the author implements the prose literally, so every quantifier, hedge, verb, and qualifier ships. "The stub" where "every stub" was meant leaves siblings stale; a defensive "and more than one" carves out exactly the cell where the defect survives; a hedge the author tightens is the version that lands; the half of a clause left unrewritten acquires the reviewer's endorsement.

**Fix:** grade the verb. Re-read, re-check, refresh, and "verify again just before" only *narrow* a check-then-act window, while a conditional write with the precondition in its predicate, a uniqueness constraint, a lock taken by every writer, or compare-and-swap *closes* it -- a remedy that does not discharge its own mechanism sentence is cosmetic, and its own note refutes it. Prescribe the derivation, never a literal measured off the local tree. Reassurance clauses ("still works", "cannot happen") carry the finding's evidentiary bar, because authors quote them into the code as comments where they become premises for every later reader. A remedy that destroys information (mask, truncate, hash, round) is always sold with a clause about what survives, and that clause is a testable claim about the corpus.

## Reviewing a prescribed fix for compliance instead of consequence

**Trap:** on a follow-up round whose delta is the fix the review asked for, checking whether the change says what the finding said.

**Reality:** it does, so review collapses and nothing outside the checklist gets read; reviewing against acceptance criteria the same reviewer wrote makes for a worse reader of them. A defect *created by* a fix is neither a prior finding nor obviously new work, so the fixed/not-fixed frame never asks about it.

**Fix:** budget the round to verify the fixes, then re-read the delta as if the prior round had never happened, quoting each criterion verbatim beside the change. Name the complement of the fix's new predicate (threshold, type check, early return) and ask whether the mechanism raised earlier lives there too; diff the remedy's outcome against every other rule the same commit states. An added assertion, a rewritten comment, or a corrected paragraph is unreviewed prose held to the finding's bar; after a correction lands, grep the corrected claim and any retracted identifier across every artifact that carries it.

## Treating prior clearances as settled

**Trap:** applying "don't re-litigate" to clearances the way it applies to findings.

**Reality:** a clearance retires an area for every later round and gets quoted back by the author under the reviewer's name. A clearance carrying an implicit quantifier ("both guards are load-bearing", "all the callers were updated") has a denominator that came from reading, and reading is what missed the third one. A clearance written as a list is worse -- one sentence of evidence spread over N subjects.

**Fix:** derive the denominator from the code and state it ("three guards, two pinned, one not"); give each subject its own evidence line, or say plainly it was read and not tested; where the subject can be instantiated many ways, state the bounding invariant instead of enumerating. Re-derive a clearance whenever the current change exists because of it, and every round when its premise is a non-existence claim ("nothing implements this yet"). When a round establishes a general mechanism, grep prior clearances for the contradicted premise -- settled means the fact still holds, premise-dead means the later finding that falsified it can be named. Write clearances that name the fact, not the API, and scope them to one axis.

## Accepting an author's correction because it arrives with evidence attached

**Trap:** conceding a finding because the author's rebuttal arrives with a command, a log excerpt, or a measurement attached.

**Reality:** the finding got three rounds of scrutiny and the rebuttal gets none. A correction right about the instance can be wrong about the class, and a "Verified" tag on a prior reviewer's note certifies their confidence, not the claim.

**Fix:** re-derive the corrected premise independently, counted rather than eyeballed, with a control that must come back different. When the correction turns on a magnitude, vary the magnitude before conceding the class. A correction claiming the defect reached further than the finding said widens the fix into territory nobody scoped or tested -- scope and test that widening rather than absorbing it.
