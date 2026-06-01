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
