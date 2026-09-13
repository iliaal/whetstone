# Operator Approval Loop for External Sends

> When to read: an agent drafts something that leaves the system once sent (a PR comment, a post, an email, a ticket update) and a human must approve it first. The UI side of approval is in [product-implications.md](./product-implications.md); this covers the durable contract that makes "approved" mean "exactly this text, once".

## Approval binds to content, not to a draft slot

Store the approved text with a content hash and an epoch (an `updated_at` or monotonically increasing revision). The approval record references both. Any edit to the draft after approval produces a new epoch and hash, which invalidates the approval; the item returns to "needs approval" rather than carrying the old decision forward. A decision whose epoch does not match the current draft is stale and releases nothing. This is the same content-binding idea as the attestation pattern in [durability-and-attestation.md](./durability-and-attestation.md): the human approved bytes, not an intention.

## Single-winner claim before transport

Dispatch is a two-step operation. First, a claim step re-validates the current approved epoch, recomputes the hash over the exact text about to be sent, checks the destination against the approved destination, and records a unique claim in the ledger. Only the worker holding the claim proceeds to transport. A uniqueness conflict on the claim stops the worker before it sends anything, so two workers picking up the same approved item cannot both deliver it. Validation happens inside the claim, not before it, because the draft can change between a read and a write.

## Unknown is terminal

Once transport begins, three outcomes are possible: a receipt was persisted, a definite failure was persisted, or nothing is known (the process crashed, the request timed out, or the receipt write failed after the send). Record the third case as `unknown`. It never expires, never reopens for another attempt, and never auto-retries: the message may already be in the recipient's inbox, and a retry doubles it. A human inspects the destination and closes the attempt as sent or failed by hand. Timeouts are not failures; they are unknowns.

## The ledger is the proof

The record of what was sent is the ledger row with its claim, hash, destination, and terminal status, not the chat transcript and not the agent's memory. Reporting "sent" without a persisted receipt is a claim, not evidence. Any later question ("did we post this?", "which version went out?") is answered from the ledger alone.

## Checklist

- [ ] Approval record stores content hash and epoch; edits after approval invalidate it
- [ ] Claim step validates epoch, hash, and destination and writes a unique claim before transport
- [ ] Concurrent workers cannot both pass the claim for one item
- [ ] Crash, timeout, or failed receipt persistence after dispatch starts produces a terminal `unknown` with no auto-retry
- [ ] "Sent" is asserted only from a persisted receipt
