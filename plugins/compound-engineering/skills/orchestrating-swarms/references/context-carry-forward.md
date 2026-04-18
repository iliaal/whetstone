# Context Carry-Forward Strategies

After each turn in an orchestrated session, five options exist for carrying context into the next step. The default "Continue" is rarely best — deliberately choose a strategy based on what just happened.

| Strategy | How | When to use |
|----------|-----|-------------|
| **Continue** | Do nothing; full prior context flows forward | Short sessions, when prior context is all directly relevant |
| **Rewind** | `Esc Esc` (double-escape); keeps the useful prefix, drops the tail | Recovering from a failed attempt. Drops the failure from context without losing the useful reads that came before it. Beats "correcting" in place because correction keeps the failed path visible. |
| **/compact** | Lossy summarization into a short digest | Long sessions where the earlier turns are no longer load-bearing but their conclusions are |
| **Subagent** | Spawn a subagent for the task; only the result returns to main context | Contained research, focused implementation, or anything that would balloon main-thread context |
| **/clear + brief** | Clear context; restart with a hand-written brief | Mode switch (different feature, different skill needed). Cleaner than compaction when you know what's still load-bearing. |

## Why Rewind is underused

When a session goes sideways after a bad tool call or misinterpretation, Rewind is strictly better than telling the assistant "no, that's wrong, do it differently." The latter leaves the failed path in context as a negative anchor — the assistant continues referencing what it did wrong. Rewind excises that from the window entirely.

## Subagent vs Continue — the orchestrator's default

For swarm orchestrators specifically: when a task would consume > 30% of remaining context if done in-thread, prefer Subagent. The tradeoff is serialization overhead (one message wait) vs protecting main-thread context for decisions that need it.

## Why clear+brief beats compaction on mode switches

`/compact` preserves everything lossy; the assistant keeps low-relevance fragments of prior tasks. `/clear` + a fresh brief produces cleaner context for a new mode because you control exactly what the assistant knows, rather than what `/compact` chose to preserve.
