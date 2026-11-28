# Driving a long-running external reviewer subprocess

When a review is delegated to an external CLI that runs as a subprocess and can
take many minutes (`codex` review, `claude -p`, a slow test/`--parallel-tests`
reviewer, a `/code-review ultra` cloud run), the failure mode is operational, not
analytical: the reviewer gets killed or re-run prematurely.

## Heartbeat tolerance: don't kill a quiet-but-alive review

Treat progress lines like `review still running: elapsed=… pid=…` as healthy, not
a hang. A long reviewer goes quiet for minutes between heartbeats while a model
call or a test suite runs. Do **not** SIGKILL it just because:

- it has been quiet for 2-5 minutes, or
- it is still running under its declared time budget (e.g. a 30-minute cap).

Inspect or kill only after: multiple *missed* expected heartbeats, the budget is
exceeded, or the subprocess has obviously failed (nonzero exit, broken pipe).
Capture stdout/stderr to a file so a quiet tail isn't mistaken for a dead process.

## Closeout loop: run until clean or capped, then stop

- Keep iterating (fix → re-run the external review) until it returns **no
  accepted/actionable findings**: a structured exit 0, not a prose "looks good".
- Treat a finding with a verified `FP-*` disposition or an explicitly
  owner-approved `ACCEPTED-RISK` tradeoff under `ia-receiving-code-review` as
  non-actionable for closeout. Bind
  that disposition to the frozen diff bundle; a repeat of the same finding
  without new evidence does not require another fix-and-review round. Reassess
  when new evidence or changed bytes invalidate the disposition. Report retained
  risks explicitly; an accepted risk is not proof that no defect exists.
- Stop as soon as it exits clean. Do **not** run one extra review just to get a
  nicer "all clear" summary; that burns time/tokens and risks new churn.
- Keep the comparison base and selected scope stable across the loop. After
  each authorized fix, freeze a fresh diff bundle using the new head SHA or
  workspace-content fingerprint. Bind that iteration's findings and verdict to
  those exact bytes; an earlier snapshot cannot verify a later fix. Reconcile
  changed paths before dispatch, and return any required scope expansion to the
  caller instead of silently widening the review.
- If a failure diagnostic proves the peer never reviewed the diff (usage/session
  quota, an unsupported CLI option), report `unavailable` immediately without a
  retry. Otherwise report the observed failure without claiming whether review
  occurred.
- **For other failures, cap the loop at two consecutive `unavailable` results**: the initial run
  plus one retry. "Clean" is not the only exit: a reviewer broken for a reason
  unrelated to the diff (auth outage, vendor incident, tool bug) returns
  `unavailable` forever, so stop after the second failure instead of iterating.
  Report the external review as unavailable, naming the reviewer attempted, the
  number of attempts, and what happened on each (exit status, elapsed time, the
  first line of any error output). Giving up does not convert the result: an
  `unavailable` pass is still never "clean" and never an input to a
  merge-readiness verdict.
- **An `incomplete` pass (see below) gets one re-run** with the missing context
  supplied or the packet partitioned. A second consecutive `incomplete`, or any
  mix of `incomplete` and `unavailable` results reaching two in a row, stops the
  loop. Report the uncovered scope by path; `incomplete` is never "clean" and
  never an input to a merge-readiness verdict.

## A failed external review is not a clean one

An external reviewer's output counts as a completed pass only when it carries
the completion markers its own contract defines: a structured verdict, a
severity set, or a recommendation line. Refusal, empty output, malformed output,
a timeout, or a nonzero exit makes the pass `unavailable`: never "clean", never
"PASS", and never an input to a merge-readiness verdict. Distinguish an
operator's explicit `disabled` opt-out from a failure-driven `unavailable`; both
are reported, and neither is a pass. On failure, do not silently substitute a
different external provider; report which reviewer was attempted and what
happened (exit status, elapsed time, the first line of any error output).
When this skill writes the reviewer's prompt, require it to end with exactly
`VERDICT: CLEAN` or `VERDICT: FINDINGS` as its last line, and read a clean pass
only from the raw last non-empty line. A missing verdict line (a prose
no-findings sentence in its place), any text after the verdict line, or
`VERDICT: CLEAN` beside listed findings makes the pass `unavailable`.

Ask the reviewer to state its scope coverage. A structured verdict that reports
missing context, inaccessible inputs, truncated input, or an unfinished
assessment is `incomplete`, never clean; when the reviewer says nothing about
coverage, treat coverage as unverified rather than complete. The reviewer's
sandbox starts empty, so supply the unchanged files each change depends on, and
never truncate or cap the packet silently: partition a large input so every
change is reviewed against all the context it needs.

Before dispatch, when the transport exposes measurable limits, check that a
plan covering the full selected scope fits both the encoded request limit and
the authorized pass count. Measure complete requests, including framing and
repeated context. Repartition while preserving each change's required context.
When no complete plan fits, record the pass as `incomplete` and name the
uncovered scope.

When a verdict must bind to an exact packet digest, verify the digest from
the bytes received at the reviewer boundary. A sender-side hash alone leaves
transport transformations unverified. Use a byte-preserving transport and mark
the pass `incomplete` for that contract if the received bytes cannot be verified.

## Egress consent: the packet leaves this machine

Before each dispatch, check that the caller's explicit approval covers the
frozen packet and its provider. Approval can cover an identified set of packets
or retries of the same packet when the recipient, bytes, and dispatch limits
match. Treat a rebuilt packet after a fix, added review context, or a provider
change as a new approval decision unless the caller already approved that
packet. Tool configuration establishes availability only.

When approval is missing, name the provider, files, and whether the packet
includes full file bodies, diff hunks, logs, or fixtures. Identify any project
restrictions that apply to the proposed contents. Ask through the channel the
main skill establishes (`AskUserQuestion` in Claude Code, `request_user_input` in
Codex, numbered options in chat as the fallback).
An answer that auto-continued on idle, or a result saying the user may be away
or nobody answered, is not consent: send nothing, report the dispatch as
awaiting a decision, and re-ask when the user returns.

**Hard exclusion of credential-bearing paths.** Exclude known credential-bearing
paths from any external dispatch, unconditionally. Unlike ordinary noise
exclusions (lockfiles, vendored or generated code), a user override cannot
re-admit them. This exclusion is specific to egress: the local coverage ledger
in [scope-resolution.md](./scope-resolution.md) still selects these paths for
local review. The set:

- the `.env` family (`.env`, `.env.*`), except template variants
  `.env.example`, `.env.sample`, and `.env.template`
- SSH private keys: `**/.ssh/**`, `id_rsa`, `id_dsa`, `id_ecdsa`, `id_ed25519`,
  `id_ecdsa_sk`, `id_ed25519_sk`, `id_xmss`, and any extensionless name ending
  in `_rsa` or `_ed25519`
- `.netrc`, `.npmrc`, `.pypirc`, `.dockercfg`, `.pgpass`, `.git-credentials`
- a file named exactly `credentials` (the AWS and gcloud CLI convention)
- Claude Code's exact basenames `.credentials.json` and `.claude.json` at any
  path depth; these can contain sign-in tokens, saved API keys, or MCP server secrets

Decide on the path alone; never read the file's content to make the call. For a
rename or copy, test the old path as well as the new one: a file moved away from
a secret-shaped name still carries the secret.
Report each excluded path in the packet description so the operator knows it
was withheld.

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
[deep-review.md](./deep-review.md) applies to inline lens execution (a reviewer
that is not independent earns no confidence boost and is named as such in the
report), but the test differs. There, independence means a separate dispatched
context; here it means a separate model family behind a separate vendor. The label
produced here is also not an input to that file's merge algorithm, which sizes
groups by dispatched context and never reads a provider field: carry this
judgement in the report prose, not as a boost the merge rules will apply.
