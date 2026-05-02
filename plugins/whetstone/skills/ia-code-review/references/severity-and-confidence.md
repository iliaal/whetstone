# Severity Levels and Confidence Rubric

Load this reference when classifying each finding. The four severity tiers and 5-band confidence rubric determine what gets reported, what gets suppressed, and what goes into Residual Risks.

## Severity Levels

- **Critical** — must fix before merge. Security vulnerabilities, data loss, broken functionality, race conditions.
- **Important** — should fix before merge. Performance issues, missing error handling, silent failures.
- **Medium** — should fix, non-blocking. Maintainability/reliability issues likely to cause near-term defects. Poor abstractions, missing validation on internal boundaries, test gaps for non-critical paths.
- **Minor** — optional. Naming, style preferences, minor simplifications. Skip if linters already cover it.

Tie every finding to concrete code evidence (file path, line number, specific pattern). Never fabricate references.

## Confidence Rubric

Assign a confidence score (0.0-1.0) to each finding:

| Range | Level | Action |
|-------|-------|--------|
| 0.85-1.00 | Certain | Report |
| 0.70-0.84 | High | Report |
| 0.60-0.69 | Confident | Report if actionable |
| 0.30-0.59 | Speculative | Suppress (except Critical security at 0.50+) |
| 0.00-0.29 | Not confident | Suppress |

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
