# Anti-Sycophancy Patterns

Load this reference when dispatching judge panels, running parallel reviewers, or iterating on subjective evaluations. Multi-agent swarms can converge on wrong answers through groupthink — these patterns prevent agents from anchoring on each other's outputs.

## Cold-start agent isolation

Each agent in a swarm receives only the task description and fresh context. No session history, no prior agent outputs until an explicit synthesis phase. When running parallel reviewers or evaluators, the orchestrator holds all outputs until every agent has submitted independently, then passes the collected results to a synthesis agent.

## Fresh instances on every re-dispatch round

When re-running reviewers across iterations (QA retry loop, re-review after fixes, multi-round evaluation), spawn a completely fresh agent each round — never reuse the same instance. Reviewers carrying memory from a prior round anchor on their earlier verdicts and miss regressions introduced by the fix. A reviewer who said "this is fine" in round 1 will rationalize back toward that verdict in round 2 even when a bad change has landed. Cold-start applies to every round, not just the first.

## Label randomization for judge panels

When multiple candidates are evaluated (e.g., parallel implementations, competing approaches), judges see randomized labels — X/Y/Z, not A/B or "original"/"improved." Re-shuffle labels each evaluation round. This prevents anchoring on position ("A is always the baseline") or naming ("the synthesis must be better").

## Convergence detection

Track an incumbent (current best candidate). If the same candidate wins N consecutive evaluation rounds (default: 3), stop iterating — the swarm has converged. This prevents infinite iteration on subjective tasks where no clear winner emerges and additional rounds just burn tokens.
