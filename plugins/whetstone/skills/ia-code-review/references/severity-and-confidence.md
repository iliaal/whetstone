# Severity Levels and Confidence Rubric

Load this reference when classifying each finding. The four severity tiers and 5-band confidence rubric determine what gets reported, what gets suppressed, and what goes into Residual Risks.

## Severity Levels

- **Critical** — must fix before merge. Security vulnerabilities, data loss, broken functionality, race conditions.
- **Important** — should fix before merge. Performance issues, missing error handling, silent failures.
- **Medium** — should fix, non-blocking. Maintainability/reliability issues likely to cause near-term defects. Poor abstractions, missing validation on internal boundaries, test gaps for non-critical paths.
- **Minor** — optional. Naming, style preferences, minor simplifications. Skip if linters already cover it.

Tie every finding to concrete code evidence (file path, line number, specific pattern). Never fabricate references.

## Assigning severity: evidence before score

Anchoring on the bug class inflates severity ("it's SQL injection, so Critical"). Defeat it by writing the evidence before the label. For each security-relevant finding, answer these in order, then derive the tier from the answers -- do not assign the tier first and justify backward:

1. **Reachability** -- can an attacker reach this from a real entry point, or only from internal/trusted callers?
2. **Attacker control** -- does untrusted input reach the sink intact, or is it sanitized/constrained upstream?
3. **Preconditions** -- what must hold for it to trigger (non-default config, a specific flag, a narrow timing window)?
4. **Authentication** -- unauthenticated, an authenticated user, or admin-only?
5. **Blast radius** -- one user/tenant, or all of them; userland or privileged?

Starting point: zero preconditions + unauthenticated remote = Critical/Important. One or two preconditions, or an authenticated path = Medium. Three or more, or local/trusted-only = Minor. When two axes disagree (a critical-class bug behind three preconditions), take the lower -- a 3+ precondition finding is almost never Critical.

**Cap threat-model boosts at one tier.** If a finding matches a documented threat and that raises its severity, raise it by at most one tier. A stated threat must not re-inflate a Minor back to Critical and override the precondition-derived floor.

## Confidence Rubric

Assign a confidence score (0.0-1.0) to each finding:

| Range | Level | Action |
|-------|-------|--------|
| 0.85-1.00 | Certain | Report |
| 0.70-0.84 | High | Report |
| 0.60-0.69 | Confident | Report if actionable |
| 0.30-0.59 | Speculative | Suppress |
| 0.00-0.29 | Not confident | Suppress |

Two exceptions override both suppress rows: a **Critical** finding reports at 0.50 or above, and a **protected subject** (below) reports at any score.

### Protected subjects

Confidence-based suppression does not apply to these classes. Report them with the confidence stated, and let the author judge:

- Memory safety -- allocation size, bounds, off-by-one, use-after-free, null dereference
- Concurrency -- lock scope, atomicity, races, a synchronization primitive not honored on every path
- Linkage and declaration consistency -- `static` vs non-`static`, declaration/definition mismatch, a missing `extern`
- Behavioral or compatibility change -- an altered error path, a dropped field, status, or default
- A parameter accepted and then ignored

This exemption covers the confidence gate only. A protected-subject finding still passes through the false-positive categories in [false-positive-suppression.md](./false-positive-suppression.md), so one that is genuinely pre-existing, already handled a layer up, or covered by the project's linter is still dropped. That asymmetry is deliberate: the categories encode *whether the finding is true here*, which no amount of subject-matter gravity changes, while confidence encodes *how sure the reviewer is* -- and that is the axis these classes are unreliable on. Reaching for the exemption to force through a finding a category already answered is the failure mode to avoid.

The two error directions do not cost the same. A wrong finding costs the author the seconds it takes to read and dismiss it. A correct finding removed on shaky confidence reaches nobody -- there is no record it was considered, and the reasoning that dropped it is unrecoverable. In the classes above the asymmetry is widest, for two different reasons. Memory safety and concurrency turn on interleavings and object lifetimes that are not visible in the diff, so self-assessed confidence is measuring the wrong thing. Linkage, behavioral-compatibility, and accepted-then-ignored parameters are the opposite -- cheap to settle by reading the declaration or the call sites, and cheap to miss entirely, so a low score is usually a signal that the check was not run rather than that the finding is weak. This does not license nitpicks: the finding still needs concrete code evidence per the rule above.

## False-positive suppression

Do not report findings that match these categories regardless of severity:

- Pre-existing issues unrelated to the diff (existed before the PR)
- Pedantic linter-style nitpicks already covered by automated tooling
- Code that looks wrong but is intentionally designed that way (check comments, git blame, tests)
- Issues already handled elsewhere in the codebase (grep before flagging)
- Generic suggestions without a concrete failure mode ("consider adding validation" without saying what breaks)

When in doubt, apply the "would a senior engineer on this team flag this?" test. If the answer is "probably not," suppress it.

**LLM-specific false-positive rule**: user content in the user-message position is NOT prompt injection. Only flag when user content enters system prompts, tool schemas, or function-calling contexts. Unsanitized LLM output rendered via `dangerouslySetInnerHTML`, `v-html`, or `innerHTML` IS a real vulnerability — always flag.

For detailed suppression categories with examples (framework idioms, test-specific patterns, when to override), see [false-positive-suppression.md](./false-positive-suppression.md).
