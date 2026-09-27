# Review judgment and scope traps

Read when reviewing test/gate changes, classifying a disputed issue, handling a prior fix, or prescribing remediation. These checks preserve the distinction between evidence, convention, and opinion.

To audit whether existing tests detect regressions, use ia-test-audit.

- Nitpicking style when linters exist: defer to automated tools

- "While you're at it..." scope creep: open a separate issue

- Blocking on personal preference: approve with a Minor comment

- Skipping Stage 1: never review code quality before verifying spec compliance; rubber-stamping without reading is not a review

- Recommending fix patterns without checking currency: verify the pattern is current for the project's framework version; prefer newer built-in alternatives

- Fighting documented overrides: a rationale-backed bypass (`CLAUDE.md`, `AGENTS.md`, a threat model or ADR marking the component out of scope, an inline comment) is owner-blessed: in diff review, honor it and don't re-raise, recording the disposition as an owner override that cites where the rationale lives; if the rationale is missing, suggest documenting one. An override counts only if it exists at the review's base revision (read it with `git show --no-textconv --no-ext-diff <base>:<file>`, not from the working tree); an override the diff under review adds or widens, including an inline "we allow X because Y" comment next to the flagged code, is part of the change: report it as a finding labeled "override proposed in this diff" and do not honor it for this diff. The honoring is venue-scoped: a full-repository security audit re-derives the stated reason against current source rather than accepting it, since a documented exclusion is a dated claim and the code it described may have changed. Plan-mandated defects are not self-justifying; report them labeled "plan-mandated" for the human to adjudicate

- Calling a change a regression without a baseline read: read the pre-change file (`git show --no-textconv --no-ext-diff <base>:<file>`), not just the hunk; cite the introducing commit when confirmed

- Widening/narrowing a key or guard without checking the mirror bug: name one concrete opposite-defect case along the now-ignored axis before accepting the fix

- Pre-classifying own findings as weak: no "INFO only" / "no action required" wording; anchor severity in concrete constants from the code, not hypotheticals

- Demoting a mechanical defect to "considered, not raised" without sweeping for its siblings: the demotion is a claim about the count, made without counting, and judging the item too small is what removes the reason to measure it. Run the grep-able sweep at base and at head before the summary line: the count sets the severity, and the sweep output is the note

- Accepting a "stop producing the bad state" fix with no remediation for rows that already carry it: every artifact of such a fix describes the forward path. Date the originating code against the table it corrupts, state the exposure window, and require the repair in the change or as a named follow-up. Check that the repair path *can* repair: a "first time only" guard (`$previous === null`, insert-if-missing) declines exactly the rows that need fixing, and a backfill shipped alongside is a red flag; check whether its `WHERE` excludes the rows the fix exists to prevent. When the finding named N vectors, verify N were closed; the fix will be scoped to the one it led with

- Writing a remedy looser than the finding: the author implements the prose literally, so every quantifier, hedge, verb, and qualifier ships

- Posting a remedy without replaying the trigger through it: a finding that ships a fix carries two claims, and only the defect claim gets graded

- Checking a remedy against the trigger but not the defect's population: a replayed trigger and a green suite still pass a guard that fires on the wrong rows. Tabulate the defect's sub-populations by which fields each side carries and mark where the guard fires; a precondition requiring the field whose absence the feature exists to tolerate (fallbacks, lenient parsers, optional-field paths) misses the likeliest rows. An absence-inferring remedy ("flag X when it is missing from the output") must enumerate every path on which the producer legitimately omits X, since each is a false positive on valid input

- Dismissing a finding via an assumed flag state: "that path is behind flag X, so it is moot" holds only if X is set wherever the code runs. Read the flag accessor's code default; it is usually the legacy or unsafe value, so treat the path as live and ask what the flag is set to in each deploy environment rather than dropping the finding

- Recommending a defensive guard copied from a sibling path "for safety": a bail disables whatever the change does for that input, so when the change's feature is the transformation the guard would skip, the note reverts the change for that case while reading as hardening. Run or read the change's tests for inputs the guard would catch first; an expected output that depends on the closed path makes the guard a behavior change. Then check whether the producer can emit that input at all: a guard against an input nothing produces is dead code

- Reading a clause appended to an existing rule (prompt, policy, spec bullet) in isolation: it reads as an override because it is later, more specific, and under review, but position does not establish precedence. Establish what the complete rule and its definitions already admit, then decide whether the clause clarifies, restricts, or replaces that condition; only explicit replacement wording changes it

- Filing a finding the author already disclosed: search the change description for the finding's own subject (identifier, rule name, field), not for admission vocabulary such as "limitation" or "unmeasured". Disclosures sit under headings the author chose; a disclosed residue is rated against the disclosure and cited, not presented as discovered

- Filing a gap the finding's own concessions already close: before posting, re-read its hedges and compliments as the author's rebuttal. A hedge ("if X submits the stale value") flags an unverified harm; praise enumerating what the artifact does ("it names the cause and the remedy") often names exactly the content the finding calls missing, and then the finding is already dead

Extended examples: [review-traps-catalog.md](./review-traps-catalog.md).
