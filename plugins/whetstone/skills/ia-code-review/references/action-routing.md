# Action Routing — 4-Tier Fix Classification

Load this reference when classifying how each finding's fix should be applied. The binary AUTO-FIX/ASK split is a special case of the 4-tier taxonomy below — the tiers prevent "mechanical fix across a risky boundary" from sliding into AUTO-FIX.

| Tier | When it applies | Action |
|------|-----------------|--------|
| `safe_auto` | Deterministic, local, behavior-preserving fix (dead code, unused import, stale comment, magic number, formatting, null-check on a clearly-nullable local) | Apply directly. No prompt. |
| `gated_auto` | A concrete fix exists, but the change crosses a behavior, contract, permission, or API boundary (auth header cleanup, retry at a new layer, error-message rewording surfaced to users) | Present the fix, wait for explicit human sign-off before applying. |
| `manual` | Actionable hand-off work: the author needs to make a call, rewrite logic, or redesign something (missing validation in an ambiguous code path, performance refactor that needs benchmarking) | Flag with the fix intent; do not auto-apply. |
| `advisory` | Report-only learning or risk signal (pattern concern, maintenance debt, future-proofing observation) | Record in the "Residual Risks" section. No expected action. |

**Conflict-resolution rule**: when multiple agents disagree on tier for the same finding, always take the more conservative route (`safe_auto` → `gated_auto` → `manual` → `advisory` is the escalation direction). Never promote a `gated_auto` to `safe_auto` because one agent classified it loosely — that's how security fixes ship unreviewed.

**Tier decision rule**: if a senior engineer would apply the fix without discussion AND the change doesn't cross a behavior/contract/permission boundary, it's `safe_auto`. When in doubt, escalate to `gated_auto`.
