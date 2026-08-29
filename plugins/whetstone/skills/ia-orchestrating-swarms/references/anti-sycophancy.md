# Anti-Sycophancy Patterns

Load this reference when dispatching judge panels, running parallel reviewers, or iterating on subjective evaluations. Multi-agent swarms can converge on wrong answers through groupthink — these patterns prevent agents from anchoring on each other's outputs.

## Cold-start agent isolation

Each agent in a swarm receives only the task description and fresh context. No session history, no prior agent outputs until an explicit synthesis phase. When running parallel reviewers or evaluators, the orchestrator holds all outputs until every agent has submitted independently, then passes the collected results to a synthesis agent.

## Fresh instances on every re-dispatch round

When re-running reviewers across iterations (QA retry loop, re-review after fixes, multi-round evaluation), spawn a completely fresh agent each round — never reuse the same instance. Reviewers carrying memory from a prior round anchor on their earlier verdicts and miss regressions introduced by the fix. A reviewer who said "this is fine" in round 1 will rationalize back toward that verdict in round 2 even when a bad change has landed. Cold-start applies to every round, not just the first.

## Label randomization for judge panels

When multiple candidates are evaluated (e.g., parallel implementations, competing approaches), judges see randomized labels — X/Y/Z, not A/B or "original"/"improved." Re-shuffle labels each evaluation round. This prevents anchoring on position ("A is always the baseline") or naming ("the synthesis must be better").

## Never reveal the passing threshold to a judge

A judge told "3.5 passes" anchors on the boundary and drifts scores toward it. The judge prompt carries the rubric and the scale; the orchestrator holds the threshold and applies it to the returned score. The same applies to consequences — "if this fails, the run aborts" is pressure toward leniency, not context.

## Judge biases and countermeasures

Structural isolation (the patterns above) does not remove per-judgment biases. Name the countermeasure in the judge prompt for the biases the task invites:

| Bias | Failure mode | Countermeasure |
|------|--------------|----------------|
| Sycophancy | Scores drift up because output "looks like effort" | Require one named defect per candidate before any score; score-only replies are invalid |
| Length | Longer output read as more thorough | Instruct scoring on criteria coverage; state that unrequested length is a cost, not a merit |
| Authority | "The senior agent / the spec author wrote this" inflates trust | Strip authorship and provenance from candidate labels |
| Completion | Finishing read as succeeding | Judge against acceptance criteria, not against "did it produce something" |
| Effort | Visible struggle (retries, long reasoning) earns charity | Judge only the artifact; process narration is excluded from the packet |
| Recency | Last-read candidate scores higher | Randomize read order per judge (extends label randomization above) |
| Familiarity | Approaches resembling the judge's own style score higher | Require the verdict to cite criterion text, not style preference |

## Convergence detection

Track an incumbent (current best candidate). If the same candidate wins N consecutive evaluation rounds (default: 3), stop iterating — the swarm has converged. This prevents infinite iteration on subjective tasks where no clear winner emerges and additional rounds just burn tokens.
