# fix and handoff

## Implementation Order

After triaging all feedback:

1. **Clarify**: resolve all unclear items first
2. **Blocking issues**: fix things that break functionality
3. **Simple fixes**: quick wins that are clearly correct
4. **Complex fixes**: changes that need careful implementation

Test after each individual fix, not after implementing everything.

**Classify the fix before patching.** Accepting a finding as correct does not settle how far the fix reaches:

- **In-scope blocker**: same violated invariant, same owner boundary, fixable without changing the task's contract. Fix it now.
- **Follow-up**: real, but a different bug class, a different owner, or independent cleanup. File it; do not fix it in this round. This is the fix-side of [`FP-OUT-OF-SCOPE`](./evidence-and-disagreement.md#false-positive-taxonomy-for-dismissed-suggestions); reply with that tag and name where it will be tracked.
- **Stop-and-escalate**: needs a new protocol, config, storage, or public-API contract, or a design choice outside the original request. Report it; do not patch. Maps to `ESCALATE` in headless mode.

Scope is defined by the invariant and its owner. File counts and line multipliers are measurements, not stop conditions. Two review-triggered patch cycles that have not converged is itself the signal: pause and reclassify every remaining finding before another edit, and stop when the honest fix is "define the canonical contract first" rather than another local inference layer.

## When Your Pushback Was Wrong

State the correction factually: "Checked this, you're correct because [reason]. Implementing." No extended apology, no self-deprecation; just acknowledge and move on.

## GitHub PR Reviews

Draft replies first and obtain any required user authorization before posting or resolving threads. This procedure supplies no posting authority.

- Reply in the inline review thread. Set `PR_NUMBER` to the PR number and `COMMENT_ID` to the numeric REST ID of the thread's original top-level review comment, not a GraphQL node ID or a reply's ID. Write the exact approved reply to an invocation-owned file with a file-writing tool, then set `REPLY_FILE` to that path. Do not interpolate Markdown into shell arguments or heredoc source:

  ```bash
  gh api "repos/{owner}/{repo}/pulls/$PR_NUMBER/comments/$COMMENT_ID/replies" \
    -F body=@"$REPLY_FILE"
  ```

  `gh` resolves `{owner}` and `{repo}` from the repository context. Require a successful exit and a returned comment ID and URL as a creation receipt, then re-fetch the exact comment and compare its stored body with the approved reply. Verify the review comment's GraphQL `state` is `SUBMITTED` before reporting it as posted or resolving its thread; REST `node_id` identifies the comment for that readback. A `PENDING` comment remains a draft, so leave the thread open and report the pending state. Never submit or discard an existing user draft review without separate authority. If the result is uncertain, re-fetch before retrying to avoid duplicates.
- Reference specific lines when explaining why you disagree
- Mark conversations as resolved only after the fix is verified, any required push succeeded and the current PR head contains the fix, and the approved reply is verified as submitted. A reply-only disposition needs no push.
- If a suggestion spawns a larger discussion, suggest moving it to an issue
