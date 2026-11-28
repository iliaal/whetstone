# Anti-Sycophancy Patterns

Load this reference when dispatching judge panels, running parallel reviewers, or iterating on subjective evaluations. Multi-agent swarms can converge on wrong answers through groupthink; these patterns prevent agents from anchoring on each other's outputs.

## Cold-start agent isolation

Each independent reviewer or evaluator receives the full task, target artifact, criteria, and operative instructions in fresh context. No implementer session history or prior verdicts until an explicit synthesis phase. In Codex use `fork_turns: "none"`. When running parallel reviewers or evaluators, the orchestrator holds all outputs until every agent has submitted independently, then passes the collected results to a synthesis agent. Implementers continuing their own unit may retain its context.

When judges exchange results through files, assign each judge a separate output directory in its brief. Before synthesis, prohibit reads of sibling output directories and the producer's self-check reports or notes; permit writes only to the judge's own directory.

## Fresh instances on every re-dispatch round

When re-running reviewers across iterations (QA retry loop, re-review after fixes, multi-round evaluation), spawn a completely fresh agent each round; never reuse the same instance. Reviewers carrying memory from a prior round anchor on their earlier verdicts and miss regressions introduced by the fix. A reviewer who said "this is fine" in round 1 will rationalize back toward that verdict in round 2 even when a bad change has landed. Cold-start applies to every round, not just the first.

Before dismissing a fresh reviewer's apparent false flag, check whether a gap or ambiguity in the brief caused it. Classify findings in this order: brief defect, valid, accepted trade-off, noise. If the brief caused the flag, correct the brief and dispatch a fresh reviewer.

## Label randomization for judge panels

When multiple candidates are evaluated (e.g., parallel implementations, competing approaches), judges see randomized labels: X/Y/Z, not A/B or "original"/"improved." Re-shuffle labels each evaluation round. This prevents anchoring on position ("A is always the baseline") or naming ("the synthesis must be better").

Freeze the questions before judging multiple candidates in one prompt, then repeat the comparison with candidate order reversed; a changed winner makes the round inconclusive. Inspect broad or near-even verdicts before deciding whether to revise anything; do not rewrite automatically to chase a score.

## Never reveal the passing threshold to a judge

A judge told "3.5 passes" anchors on the boundary and drifts scores toward it. The judge prompt carries the rubric and the scale; the orchestrator holds the threshold and applies it to the returned score. The same applies to consequences: "if this fails, the run aborts" is pressure toward leniency, not context.

The expected verdict is the same anchor. Briefing an evaluator with the outcome you anticipate ("we expect nothing here", "this probably duplicates ours") produces confirmation: the reader string-matches against the expectation and stops, missing gaps one abstraction level up. State the question and the comparison basis; hold the prior.

## Distinguish context independence from model diversity

Require fresh context for an independent review, as described above. Model diversity is a separate property: prefer a different model lineage when available and authorized, and disclose shared-lineage correlation limits when using the same family. A single-family harness can still provide context-independent review.

For an explicitly cross-model evaluation, require the evaluator to use a different model lineage from the producer. Exclude the producer's lineage from every fallback choice. If no eligible evaluator is available, report that the cross-model requirement remains unmet; do not silently substitute a same-lineage judge.

## Judge biases and countermeasures

Structural isolation (the patterns above) does not remove per-judgment biases. Name the countermeasure in the judge prompt for the biases the task invites:

| Bias | Failure mode | Countermeasure |
|------|--------------|----------------|
| Sycophancy | Scores drift up because output "looks like effort" | Require criterion-linked evidence before scoring each candidate: verified defects, or explicitly no defects found with checked scope and limitations. Never invent a defect to meet a quota; score-only replies are invalid |
| Length | Longer output read as more thorough | Instruct scoring on criteria coverage; state that unrequested length is a cost, not a merit |
| Authority | "The senior agent / the spec author wrote this" inflates trust | Strip authorship and provenance from candidate labels |
| Completion | Finishing read as succeeding | Judge against acceptance criteria, not against "did it produce something" |
| Effort | Visible struggle (retries, long reasoning) earns charity | Judge only the artifact; process narration is excluded from the packet |
| Recency | Last-read candidate scores higher | Randomize read order per judge (extends label randomization above) |
| Familiarity | Approaches resembling the judge's own style score higher | Require the verdict to cite criterion text, not style preference |

## Convergence detection

Track an incumbent (current best candidate). If the same candidate wins N consecutive evaluation rounds (default: 3), stop iterating: the swarm has converged; inconclusive comparisons do not count as wins. This prevents infinite iteration on subjective tasks where no clear winner emerges and additional rounds just burn tokens.
