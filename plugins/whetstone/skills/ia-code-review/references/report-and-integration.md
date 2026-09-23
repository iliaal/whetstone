# Review report and integration

Read when producing a standalone review report or routing its recommendations into another workflow. Caller-specified output contracts take precedence.

## When to Stop and Ask

- Fixing the issues would require an API redesign beyond the PR's scope
- Intent behind a change is ambiguous: ask rather than assume
- Missing validation tooling (no linter, no tests): flag the gap, don't guess

## Output Format

```
## Review: [brief title]
Profiles: [review unit -> primary skill (+ supplemental), or generic]

### Critical
- **CR-001.** [file:line] `quoted code` -- [issue]. Confidence: [evidence and remaining assumptions]. [Impact if not fixed]. Fix: [concrete suggestion].

### Important / ### Medium
- (same shape; Important adds Consider: [alternative approach])

### Minor
- **CR-004.** [file:line] -- [observation].

### What's Working Well
- [specific positive observation with why it's good]

### Residual Risks
- [unresolved assumptions, areas not covered, open questions]
- Set aside as out of scope: [one line per behavior considered and consciously set aside as outside the change's scope or spec, with the reason; or "no declined scope"]

### Verdict
Ready to merge / Ready with fixes / Not ready -- [one-sentence rationale]
```

Number findings `CR-001`, `CR-002`... sequentially across severities for stable IDs. Cap 10 per severity; note any overflow and show the highest-impact ones.

**Declined scope is not uninspected scope:** the set-aside list above records a pass that ran and declined; the budget-exhausted `uninspected` state in [severity-and-confidence.md](./severity-and-confidence.md) records a pass that did not run. Report them as separate states: an uninspected item also blocks a complete coverage ledger, a declined one does not.

**Secret redaction:** when a finding's subject is a live credential (API key, token, password, private key), cite `file:line` and describe the pattern (`AWS access key ID assigned to a constant`); never reproduce the value in `quoted code` or anywhere else in the report. Reports are posted to PRs and captured in transcripts, both of which outlive the credential's rotation.

**Markdown safety:** in table cells, escape literal `|` as `\|`; code excerpts with pipes (`a | b`, `string | null`) split rows silently. Bullet output is pipe-safe.

Multi-agent consolidation: apply the merge algorithm in [deep-review.md](./deep-review.md) (root-cause dedupe, evidence-based severity, `NEEDS DECISION`, cross-lens agreement provenance).

**Clean review (no findings):** a valid outcome, not insufficient effort. Say so explicitly and summarize what was checked.

## References

References load at their point of use above. Additionally: [security-test-coverage.md](./security-test-coverage.md) (security-audit deliverable checklist); [false-positive-suppression.md](./false-positive-suppression.md) (framework-idiom and test-specific FP categories); [external-review-subprocess.md](./external-review-subprocess.md) (external-CLI reviewer protocol: heartbeat tolerance, run-until-clean-or-capped, frozen-diff binding, egress consent, provider-independence labeling).

## Integration

- `ia-receiving-code-review`: inbound side. Tier map: `safe_auto` ≈ AUTO-FIX, `gated_auto` ≈ ESCALATE-for-approval, `manual` ≈ ESCALATE, `advisory` ≈ FYI
- `ia-kieran-reviewer` agent: persona-driven Python/TypeScript deep quality review
- `/ia-review`: full ceremony (worktrees, ultra-thinking); deep review here is lighter: parallel specialists, no worktrees
- `/ia-resolve-pr` command: batch-resolve PR comments with parallel agents
- `ia-security-sentinel` agent: deep security audit; threat-model mode for new trust boundaries
