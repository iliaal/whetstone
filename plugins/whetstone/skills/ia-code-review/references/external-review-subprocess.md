# Driving a long-running external reviewer subprocess

When a review is delegated to an external CLI that runs as a subprocess and can
take many minutes (`codex` review, `claude -p`, a slow test/`--parallel-tests`
reviewer, a `/code-review ultra` cloud run), the failure mode is operational, not
analytical: the reviewer gets killed or re-run prematurely.

## Heartbeat tolerance -- don't kill a quiet-but-alive review

Treat progress lines like `review still running: elapsed=… pid=…` as healthy, not
a hang. A long reviewer goes quiet for minutes between heartbeats while a model
call or a test suite runs. Do **not** SIGKILL it just because:

- it has been quiet for 2-5 minutes, or
- it is still running under its declared time budget (e.g. a 30-minute cap).

Inspect or kill only after: multiple *missed* expected heartbeats, the budget is
exceeded, or the subprocess has obviously failed (nonzero exit, broken pipe).
Capture stdout/stderr to a file so a quiet tail isn't mistaken for a dead process.

## Closeout loop -- run until clean, then stop

- Keep iterating (fix → re-run the external review) until it returns **no
  accepted/actionable findings** -- a structured exit 0, not a prose "looks good".
- Stop as soon as it exits clean. Do **not** run one extra review just to get a
  nicer "all clear" summary -- that burns time/tokens and risks new churn.
- Bind the review to one frozen diff bundle (`base SHA … head SHA`) so every
  iteration reviews the same surface; don't re-derive scope mid-loop (see
  "Base-branch resolution for branch reviews" in the main skill).

## Egress consent -- the packet leaves this machine

Delegating to an external CLI sends the diff, and often surrounding source, to
another vendor's backend. The tool being configured is not consent to transmit a
particular packet. Before the first dispatch in a session, state what goes out --
which files, whether full file bodies or diff hunks only, whether logs or fixtures
are included -- and get an explicit go-ahead. Configuration is a capability;
approval is per-packet. If the diff touches anything the project treats as
restricted (customer data in fixtures, credentials in config, regulated content),
name that specifically rather than describing the packet by size. Ask through the
channel the main skill establishes (`AskUserQuestion` in Claude Code,
`request_user_input` in Codex, numbered options in chat as the fallback).

## Label independence honestly

An external reviewer is only a second opinion to the extent it is a different
model family behind a different vendor. Report the relationship, not just the tool
name:

| Host | External reviewer | Label |
|------|-------------------|-------|
| Anthropic model | OpenAI-backed CLI (or the reverse) | cross-provider |
| OpenAI model | OpenAI-backed CLI | same-provider |
| Unknown or unresolvable | either | provider relationship unverified |

A same-provider pass reported as an independent second opinion is a specific,
checkable false claim, and it inflates confidence exactly where the two reviewers'
blind spots overlap most. The consequence matches what
[deep-review.md](./deep-review.md) applies to inline lens execution -- a reviewer
that is not independent earns no confidence boost and is named as such in the
report -- but the test differs. There, independence means a separate dispatched
context; here it means a separate model family behind a separate vendor. The label
produced here is also not an input to that file's merge algorithm, which sizes
groups by dispatched context and never reads a provider field: carry this
judgement in the report prose, not as a boost the merge rules will apply.
