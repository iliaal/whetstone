# Severity Levels and Confidence Rubric

Load this reference when classifying findings. Severity describes impact; confidence describes the supporting evidence. Assess them separately.

## Severity Levels

- **Critical**: blocks merge: a reachable failure with severe impact, such as substantial data loss, privilege compromise, or loss of a core service with no adequate recovery.
- **Important**: should fix before merge: a concrete, material failure of intended behavior, reliability, security, or performance under supported conditions.
- **Medium**: should fix, non-blocking: a bounded defect or maintainability/reliability problem with a demonstrated near-term consequence.
- **Minor**: optional. Naming, style preferences, minor simplifications. Skip if linters already cover it.

Tie every finding to concrete code evidence (file path, line number, specific pattern). Never fabricate references. A citation that was not measured is fabricated whether or not it was invented: line numbers inherited from another pass, from a tool counting within a diff hunk, from an earlier note, or from a windowed read are unmeasured; re-derive each by grepping the exact source text at the ref being cited. Identifiers derived by convention (a table name inferred from a class name) are guesses wearing a lookup's costume, and they fail silently. Bounds-check for free: a cited line in a file the change creates must not exceed that file's length.

## Assigning severity: evidence before score

Anchoring on the bug class inflates severity ("it's SQL injection, so Critical"). Defeat it by writing the evidence before the label. For each security-relevant finding, answer these in order, then derive the tier from the answers; do not assign the tier first and justify backward:

1. **Reachability**: can an attacker reach this from a real entry point, or only from internal/trusted callers?
2. **Attacker control**: does untrusted input reach the sink intact, or is it sanitized/constrained upstream?
3. **Preconditions**: what must hold for it to trigger (non-default config, a specific flag, a narrow timing window)?
4. **Authentication**: unauthenticated, an authenticated user, or admin-only?
5. **Blast radius**: one user/tenant, or all of them; userland or privileged?
6. **Magnitude**: when impact scales with a value, measure the threshold and compare it against the range the application actually reaches. A downstream stage often absorbs small values, so a binary finding can be no defect under the application's cap and a defect over the top third. Grade both directions; the under-threshold side often fails silently.

**Reachability, defined.** Reachability counts only when a path runs from a public interface (a route, a CLI argument, a file the process reads, a message consumer) to a first-party sink. Reach that exists only from tests, from an internal helper with no external caller, or from vendored code the host never invokes is not reachability.

**Precondition-subsumes-conclusion check.** Compare the attacker's initial and resulting capabilities. Suppress only when there is no gain; a constrained file write can become code execution under a more privileged identity, so file write and execution are not interchangeable.

Derive severity from the demonstrated consequence, exposure, likelihood under supported conditions, and available recovery. Do not count preconditions or map authentication/local reach to a fixed tier: several routine preconditions may still expose every tenant, while an unauthenticated cosmetic failure can be Minor. Explain the conditions that materially change the impact. A threat model supplies evidence about relevant actors and assets, not an automatic tier boost.

**Grade a transient consequence at its terminal state.** "The record stays at status S" reads as latency and is true, which stops the next question: who watches S, and what do they write when they give up? Compare the recovery window against the watcher's retry budget: when the window exceeds the budget, the record reaches the failure branch with a misleading cause, not a slow correct state. Deferrals banked against a follow-up have the same shape.

**Spec silence is not a downgrade reason.** A specification states what the software must do; it does not enumerate every input. For behavior the spec is silent on, grade the finding by its effect on a reasonable user of the software, not by whether the spec mentions the triggering input. This governs the severity of a defect already found in the changed code; it does not authorize findings against deliberately deferred scope or an explicitly stated non-goal. Invoking that carve-out requires a pointer to where the deferral or non-goal is stated: a quoted spec line, a quoted PR-description line, or a linked issue. Silence is not a stated non-goal, and an uncited "that was out of scope" does not lower severity.

## Confidence Rubric

State the evidence supporting confidence:

| Evidence | Disposition |
|----------|-------------|
| Reproduced with the actual trigger and a controlled comparison | Report; name the tested scope |
| Concrete source path traced through callers and relevant guards | Report; state any untested runtime assumption |
| Plausible harm but a consequential premise is unverified | Residual Risks; name the missing check |
| Disproved or no concrete failure path | Omit; retain material disproof evidence when needed |

If a caller or schema requires a 0.0-1.0 score, label it **uncalibrated reviewer judgment**, not a probability or measured certainty. A decimal threshold does not decide truth, and agreement among agents does not earn an automatic numerical increment. Confidence changes when evidence changes.

A verification or validation pass that runs out of budget marks every unreached finding as **uninspected** with the reason (for example `budget exhausted`); never fabricate a verdict for an item the pass did not inspect. An uninspected finding keeps its pre-pass severity and confidence and is reported under Residual Risks with the reason. A review or coverage ledger cannot be marked complete while any item is uninspected.

### Protected subjects

For these easily missed classes, preserve consequential unresolved candidates in Residual Risks rather than silently dropping them. Promote them to findings when the evidence bar above is met:

- Memory safety: allocation size, bounds, off-by-one, use-after-free, null dereference
- Concurrency: lock scope, atomicity, races, a synchronization primitive not honored on every path
- Linkage and declaration consistency: `static` vs non-`static`, declaration/definition mismatch, a missing `extern`
- Behavioral or compatibility change: an altered error path, a dropped field, status, or default
- A parameter accepted and then ignored
- Authentication and authorization: a missing, reordered, or fail-open check
- Injection: SQL, command, template, header, or path
- Secrets exposure: a credential in source, logs, traces, or a client bundle
- Cryptography: a weak primitive, reused nonce, or disabled verification
- Data loss or destructive operations: delete, overwrite, truncate, or an irreversible migration step

The bar is symmetric. A reviewer or validator may not mark a finding in one of these classes `rejected` without citing one of: a specific refuting `file:line`; version- or configuration-specific documentation; commit provenance; or a discriminating test result that names its revision, configuration, trigger, assertion, and observed result. A general passing suite is not disproof, and an assumed framework guarantee is not disproof. Absent that evidence the verdict is `unresolved`, never `rejected`. Lack of disproof is not confirmation either; an unresolved candidate stays in Residual Risks with the missing check named.

A rationale-backed owner override is a third disposition, not a failure to meet this bar. When the project documents the bypass with a reason (`CLAUDE.md`, `AGENTS.md`, a threat model or ADR marking the component out of scope, a project security file, an inline comment), record the finding as an owner override citing where the rationale lives, rather than forcing it to `rejected` (the evidence bar is unmet) or to `unresolved` (the question is answered for this venue). That disposition holds for diff review only; a full-repository security audit re-derives the rationale against current source. It also requires the rationale to exist at the review's base revision: a rationale the diff under review adds or widens is not an owner override but a finding labeled "override proposed in this diff". See the documented-overrides entry in [review-judgment-traps.md](./review-judgment-traps.md).

The subject does not override contrary evidence or review scope. Apply [false-positive-suppression.md](./false-positive-suppression.md) after tracing the relevant callers and guards.

### Quote-or-downgrade

A finding needs the source or observed artifact motivating it. When that evidence is unavailable, record a consequential candidate as unresolved rather than inventing a citation. When the symbol is generated by a metaclass, ORM, or codegen layer (Eloquent magic attributes and casts, Django `Meta`, SQLAlchemy `relationship`, Prisma's generated client, TypeORM decorators), quote the meta-construct that defines the symbol, not the literal name; grepping for the name and not finding it is not verification.

False positives consume investigation time and can motivate harmful edits; false negatives hide real defects. Preserve the distinction between a demonstrated finding and an unresolved risk instead of forcing either into a confidence threshold.

## False-positive suppression

Suppress candidates only when the evidence establishes one of these reasons; a category label does not decide the case:

- Pre-existing issues the change does not take part in (defined in [false-positive-suppression.md](./false-positive-suppression.md) category 1); list them under "Predates change" in Residual Risks
- Pedantic linter-style nitpicks already covered by automated tooling
- An intentional design whose stated rationale and actual behavior address the alleged failure (check base-revision comments, history, and tests; a rationale comment the diff adds is part of the change, per the owner-override disposition above). Report a newly demonstrated concrete consequence with that rationale as context; intentionality alone does not refute it.
- Issues already handled elsewhere in the codebase (grep before flagging)
- Generic suggestions without a concrete failure mode ("consider adding validation" without saying what breaks)

For unresolved cases, identify the missing evidence and the consequence it could change.

**LLM-specific rule**: an ordinary user request is not prompt injection merely because it reaches an LLM. Trace whether lower-trust content can redirect the task or privileged tools across an authorization boundary; a user-message role does not itself prevent that. For LLM output rendered as HTML, verify attacker influence, sanitization, and the rendering sink before filing XSS.

For detailed suppression categories with examples (framework idioms, test-specific patterns, when to override), see [false-positive-suppression.md](./false-positive-suppression.md).
