# Review judgment and scope traps

Read when reviewing test/gate changes, classifying a disputed issue, handling a prior fix, or prescribing remediation. These checks preserve the distinction between evidence, convention, and opinion.

- Nitpicking style when linters exist -- defer to automated tools

- "While you're at it..." scope creep -- open a separate issue

- Blocking on personal preference -- approve with a Minor comment

- Skipping Stage 1 -- never review code quality before verifying spec compliance; rubber-stamping without reading is not a review

- Recommending fix patterns without checking currency -- verify the pattern is current for the project's framework version; prefer newer built-in alternatives

- Fighting documented overrides -- a rationale-backed bypass (`CLAUDE.md`, `AGENTS.md`, inline comment) is owner-blessed: honor it, don't re-raise; if the rationale is missing, suggest documenting one. Plan-mandated defects are not self-justifying — report them labeled "plan-mandated" for the human to adjudicate

- Calling a change a regression without a baseline read -- read the pre-change file (`git show <base>:<file>`), not just the hunk; cite the introducing commit when confirmed

- Widening/narrowing a key or guard without checking the mirror bug -- name one concrete opposite-defect case along the now-ignored axis before accepting the fix

- Pre-classifying own findings as weak -- no "INFO only" / "no action required" wording; anchor severity in concrete constants from the code, not hypotheticals

- Demoting a mechanical defect to "considered, not raised" without sweeping for its siblings -- the demotion is a claim about the count, made without counting, and judging the item too small is what removes the reason to measure it. Run the grep-able sweep at base and at head before the summary line: the count sets the severity, and the sweep output is the note

- Accepting a "stop producing the bad state" fix with no remediation for rows that already carry it -- every artifact of such a fix describes the forward path. Date the originating code against the table it corrupts, state the exposure window, and require the repair in the change or as a named follow-up. Check that the repair path *can* repair: a "first time only" guard (`$previous === null`, insert-if-missing) declines exactly the rows that need fixing, and a backfill shipped alongside is a red flag -- check whether its `WHERE` excludes the rows the fix exists to prevent. When the finding named N vectors, verify N were closed; the fix will be scoped to the one it led with

- Writing a remedy looser than the finding -- the author implements the prose literally, so every quantifier, hedge, verb, and qualifier ships

- Posting a remedy without replaying the trigger through it -- a finding that ships a fix carries two claims, and only the defect claim gets graded

Extended examples: [review-traps-catalog.md](./review-traps-catalog.md).
