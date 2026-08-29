# Cross-Run Coordination

> When to read: designing a multi-agent pipeline that dedupes items across reruns by ID, or that serializes access to one shared resource (a checkout, a test database) across one-shot subprocesses and short-lived subagents.

## Identifier minting

**The orchestrator mints identifiers; workers never do.** When a pipeline tracks items across runs by ID (findings, tickets, work units), two failure modes destroy dedupe. Models cannot compute hashes -- a prompt asking for "the first 8 hex characters of `hash(...)`" returns fabricated plausible hex, and nothing guarantees a tool was used even with shell access, so every rerun mints fresh IDs and exact-match dedupe silently never fires. And hashing any model-authored field (title, summary) forks identity on a model, temperature, or wording change, duplicating the whole backlog when you swap reviewers. Compute the ID in the merge step from model-independent fields only; let workers return raw tuples and echo a prior ID only when one was supplied. Absorb the residual instability with fuzzy prior-matching (same file and category within a small line window keeps the prior ID), and grep each item's quoted evidence against the cited file before persisting -- that kills hallucinated items at zero model cost and keeps the ID inputs honest.

## TTL lease file

**Serialize a shared resource with a TTL lease file, not a coordination daemon.** When the participants are one-shot subprocesses and short-lived subagents rather than pollers, a message bus is a daemon where a lock is needed; the real concurrency is session-against-session on one checkout or one test database. Four design points decide whether the lease works:

- A file-lock cannot express the lifetime. A round spans many separate invocations, so lock only the read-modify-write of a lease *file* stamped with the session id, and write it by rename from a temp file so a reader never sees a torn lease.
- Process liveness is not a staleness signal. The acquiring shell exits immediately, so keying staleness on the recorded pid reads every live lease as breakable; expiry is TTL plus explicit release, and the pid is diagnostic only.
- Expiry outranks ownership. Check the TTL *before* holder equality, or a session's own expired lease reports as held-by-me -- the exact false confidence the lease exists to remove.
- Size the TTL above the work's realistic maximum and renew it while the work is alive. A TTL set exactly equal to the expected duration has no margin: the one run that overshoots frees the lease under itself and admits a second concurrent holder.

Scope it honestly: the lease is advisory for the work. It removes one destructive collision and serializes one resource; it does not stop an agent that never asks.
