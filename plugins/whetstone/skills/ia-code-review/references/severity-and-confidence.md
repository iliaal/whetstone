# Severity Levels and Confidence Rubric

Load this reference when classifying each finding. The four severity tiers and 5-band confidence rubric determine what gets reported, what gets suppressed, and what goes into Residual Risks.

## Severity Levels

- **Critical** — must fix before merge. Security vulnerabilities, data loss, broken functionality, race conditions.
- **Important** — should fix before merge. Performance issues, missing error handling, silent failures.
- **Medium** — should fix, non-blocking. Maintainability/reliability issues likely to cause near-term defects. Poor abstractions, missing validation on internal boundaries, test gaps for non-critical paths.
- **Minor** — optional. Naming, style preferences, minor simplifications. Skip if linters already cover it.

Tie every finding to concrete code evidence (file path, line number, specific pattern). Never fabricate references. A citation that was not measured is fabricated whether or not it was invented: line numbers inherited from another pass, from a tool counting within a diff hunk, from an earlier note, or from a windowed read are unmeasured -- re-derive each by grepping the exact source text at the ref being cited. Identifiers derived by convention (a table name inferred from a class name) are guesses wearing a lookup's costume, and they fail silently. Bounds-check for free: a cited line in a file the change creates must not exceed that file's length.

## Assigning severity: evidence before score

Anchoring on the bug class inflates severity ("it's SQL injection, so Critical"). Defeat it by writing the evidence before the label. For each security-relevant finding, answer these in order, then derive the tier from the answers -- do not assign the tier first and justify backward:

1. **Reachability** -- can an attacker reach this from a real entry point, or only from internal/trusted callers?
2. **Attacker control** -- does untrusted input reach the sink intact, or is it sanitized/constrained upstream?
3. **Preconditions** -- what must hold for it to trigger (non-default config, a specific flag, a narrow timing window)?
4. **Authentication** -- unauthenticated, an authenticated user, or admin-only?
5. **Blast radius** -- one user/tenant, or all of them; userland or privileged?
6. **Magnitude** -- when impact scales with a value, measure the threshold and compare it against the range the application actually reaches. A downstream stage often absorbs small values, so a binary finding can be no defect under the application's cap and a defect over the top third. Grade both directions; the under-threshold side often fails silently.

**Reachability, defined.** Reachability counts only when a path runs from a public interface -- a route, a CLI argument, a file the process reads, a message consumer -- to a first-party sink. Reach that exists only from tests, from an internal helper with no external caller, or from vendored code the host never invokes is not reachability.

**Precondition-subsumes-conclusion check.** Reject a finding whose stated precondition already requires the capability the sink would grant -- "an attacker who can write arbitrary files can cause RCE via this include" is circular, because arbitrary file write already is the RCE.

Starting point: zero preconditions + unauthenticated remote = Critical/Important. One or two preconditions, or an authenticated path = Medium. Three or more, or local/trusted-only = Minor. When two axes disagree (a critical-class bug behind three preconditions), take the lower -- a 3+ precondition finding is almost never Critical.

**Cap threat-model boosts at one tier.** If a finding matches a documented threat and that raises its severity, raise it by at most one tier. A stated threat must not re-inflate a Minor back to Critical and override the precondition-derived floor.

**Grade a transient consequence at its terminal state.** "The record stays at status S" reads as latency and is true, which stops the next question: who watches S, and what do they write when they give up? Compare the recovery window against the watcher's retry budget -- when the window exceeds the budget, the record reaches the failure branch with a misleading cause, not a slow correct state. Deferrals banked against a follow-up have the same shape.

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

### Quote-or-downgrade

A finding that cannot quote the verbatim line motivating it is capped in the Speculative band (0.30-0.59), where it is suppressed unless the Critical-at-0.50-or-above or protected-subject exception above already applies to it. When the symbol is generated by a metaclass, ORM, or codegen layer -- Eloquent magic attributes and casts, Django `Meta`, SQLAlchemy `relationship`, Prisma's generated client, TypeORM decorators -- quote the meta-construct that defines the symbol, not the literal name; grepping for the name and not finding it is not verification. The gate kills four recurring false-positive classes: "field doesn't exist on model", "may be None", "save() may lose fields", and "update_fields may miss X".

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
