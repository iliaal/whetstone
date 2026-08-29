# Isolation and Sandbox Traps

Test-isolation checks whose passing result does not mean what it claims to mean, moved from the SKILL.md Anti-Patterns section.

## Bounding a containerized command with an outside `timeout`

**Symptom:** `timeout N docker exec <container> <test command>` returns 124 and the run looks bounded. `timeout` signalled the client, not the process inside the container, which keeps running -- and an orphaned test holds its transaction or lock, so every later run against the same database hangs for reasons unrelated to the code under test. The symptom looks like the *new* tests hanging.

**Fix:** put the timeout inside the container (`docker exec <container> timeout N <cmd>`) or bound the runtime itself. After any aborted containerized run, sweep for orphans (`ps -eo pid,etime,args` inside the container) before trusting the next result -- an `etime` far larger than any run you know about is the tell. Better still, assert the function returns within the test rather than racing a wall clock against a suspected infinite loop.

## The harness sandboxes the subject in the primitive under test

**Symptom:** A probe about commit durability runs under a transaction-wrapping test trait (Laravel `RefreshDatabase`, Rails `use_transactional_tests`, a pytest rollback fixture). The `COMMIT` under test becomes a savepoint, the write never becomes durable, and "did the row survive the failure?" is unanswerable -- but the probe still returns a plausible, well-formed answer. Sometimes there is a loud tell (on Postgres, `SQLSTATE 25P02` refusing every later statement); when the injected failure does not poison the connection, or the assertion reads state captured before the failure, there is no tell at all, and a wrong commit-ordering result gets quoted downstream as measured evidence.

**Fix:** Before trusting a probe, ask what the harness wraps the subject in and whether that is the same mechanism the question is about. Drop the trait for that one probe and assert a control proving the removal happened -- print the transaction nesting depth and require 0. Without the control the probe is unfalsifiable: a nested run and a clean run produce output of the same shape. Same test for a filesystem probe run under a chroot of the path under test, or any sandbox built from the primitive being measured.

## Global before/after snapshots as an isolation check

**Symptom:** the isolation fixture hashes an entire shared directory, ledger, or registry before and after the run and requires it unchanged. The assertion cannot name a writer, so any legitimate concurrent process flips it and the test implicates itself. Retrying to green then hides a real fixture leak exactly as easily as it hides the unrelated write.

**Fix:** assert on a per-run canary instead -- a unique token or uniquely-named artifact only this run can produce. Assert it lands in the disposable location and that the shared one holds zero copies. Verify both directions: an unrelated mutation elsewhere in the shared tree must leave the fixture green. If a leaked canary must be cleaned up, remove that one derived path, never sweep the shared directory.

## Relocating an environment variable and calling it isolation

**Symptom:** the suite points `HOME`, `TMPDIR`, or a state-root variable at a temp directory and concludes the code under test is sandboxed. The relocation only redirects paths derived from that variable *at call time*; anything anchored to the executable's own location, a compile-time constant, or the current uid still resolves to the real one. The fixture is green either way, because reading the real file usually succeeds -- the tell is absent by construction.

**Fix:** enumerate the anchors (the running binary's neighbours, baked build-time paths, uid-derived paths, literal `/tmp/` prefixes) and pin each with a planted decoy plus a positive control. Run the suite a second time against *installed* binaries in a real install layout: a build-tree-only run cannot observe any defect whose trigger is the install layout, and no amount of fixture review closes that gap.
