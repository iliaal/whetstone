# Deep Review Process

Multi-agent review that dispatches parallel specialist agents, each analyzing the same diff through a single lens. Produces a unified, deduplicated report.

## Specialist Agents

Dispatch all agents in parallel (read-only, safe to parallelize). Each receives the full diff, the PR description/intent, and the scope resolution results.

| Agent | Lens | Focus | Model |
|-------|------|-------|-------|
| correctness | Logic & behavior | Intent alignment (code matches stated PR intent), edge cases, off-by-ones, error paths, type safety, null handling, async ordering, state management | default |
| security | Attack surface | Injection vectors (SQL, XSS, CSRF, SSRF, command), auth/authz gaps, secrets exposure, trust boundaries, race conditions. Load [security-patterns.md](./security-patterns.md) | default |
| testing | Coverage gaps | Untested code paths, missing edge case tests, mock quality, behavioral vs implementation testing, regression test coverage | opus |
| maintainability | Long-term health | Coupling, naming, complexity, API surface changes, SRP violations, leaky abstractions, dead code | opus |
| performance | Efficiency | N+1 queries, unbounded collections, missing indexes, unnecessary allocations, cache opportunities, algorithmic complexity | opus |
| reliability | Failure resilience | Error handling completeness, timeout/retry logic, circuit breakers, resource cleanup on error paths, graceful degradation. Load [reliability-patterns.md](./reliability-patterns.md) | opus |
| cloud-infra | Infrastructure | Terraform/IaC review, cloud architecture, cost implications, disaster recovery. Only dispatch when diff touches infrastructure files (*.tf, Dockerfile, docker-compose.*, CI/CD configs). Use `ia-cloud-architect` agent. | opus |
| api-contract | API surface | Breaking changes (removed fields, type changes, new required params), versioning strategy, error response consistency, backwards compatibility, documentation drift. Only dispatch when diff touches public endpoints, exported interfaces, or API route files. | opus |
| data-migration | Migration safety | Reversibility (can it roll back?), data loss risk, lock duration on large tables, backfill strategy, index creation timing, multi-phase safety (deploy code first, then migrate). Only dispatch when diff includes migration files. Use `ia-database-guardian` agent. | default |

### Agent Prompt Template

Each specialist receives:

```
Review this diff as a {lens} specialist. Focus exclusively on {focus area}.

DO:
- Read the actual code line-by-line. Trace logic through the diff, not around it.
- Compare every claim made in the PR description against what the diff actually does.
- Quote the specific code that triggers each finding so the author can locate it.
- Treat the PR description as a claim to verify, not a truth to accept.

DON'T:
- Take the author's summary at face value. "Refactored X" may hide behavioral changes.
- Accept "this is covered by tests" without checking the test files in the diff.
- Rubber-stamp sections you didn't open. If you didn't read it, you didn't review it.
- Extrapolate from the description when the code contradicts it -- the code wins.

DIFF:
{full diff content}

PR INTENT:
{PR description or task spec}

SCOPE:
{files list with change types: Added/Modified/Deleted}

Return findings in this format:
- **[file:line]** `quoted code` -- [issue]. Confidence: [0.0-1.0]. [Impact]. Fix: [suggestion].

Only report findings in your domain. Do not comment on other dimensions.
Apply the confidence rubric: suppress anything below 0.60 confidence.
Limit to 10 findings, highest severity first.
```

### Model Selection

- **correctness**, **security**, **data-migration**: use default model (these require deeper reasoning about logic, attack surfaces, or data safety)
- **testing**, **maintainability**, **performance**, **reliability**, **cloud-infra**, **api-contract**: use opus (reasoning about absence -- untested paths, missing error handling, breaking changes -- requires deep code comprehension)

Override: if the diff touches auth, payments, or crypto, upgrade security to opus.

### Red-Team Pass (Second Phase)

After the parallel specialists return, dispatch a single red-team agent that receives the diff AND the combined specialist findings. This agent looks for what the specialists missed:

- Happy-path assumptions that break under load or unusual input sequences
- Silent failures where errors are swallowed without logging or alerting
- Trust boundary violations (user input flowing into privileged operations without re-validation)
- Cross-category issues that fall between specialist domains
- Integration boundary gaps where two systems meet

Dispatch the red-team pass when: diff >200 lines, OR any specialist found a Critical finding. Skip for small/simple diffs where the parallel pass is sufficient.

Red-team findings merge into the main report with a `[red-team]` tag. Use default model.

## Merge Algorithm

After all agents return, apply these rules in order. Each consolidated finding carries its original `CR-XXX` ID from the first agent that reported it so PR threads can reference specific findings unambiguously.

**Preamble — fingerprint first.** Before applying any numbered rule, group findings across agents by fingerprint `path:line:issue_class`. The rules below operate on these groups: a group of size 1 is handled by rule 5 (single-agent hit), a group of size 2 by rule 6, a group of size 3+ by rule 7. Confidence boosts apply once per group, not per matching rule — use rule 7 if applicable, otherwise rule 6.

1. **Same file:line + same issue class** → merge into one finding. Keep the higher-severity rating and the more actionable fix text.
2. **Same file:line + different issue class** → keep both. Tag as "co-located" in the output so the author sees they share a line.
3. **Conflicting severity on the same merged finding** → always take the higher severity. Do not average.
4. **Conflicting recommendations** → present both and mark as `NEEDS DECISION`. Do not silently pick one.
5. **One agent flags, others don't** → keep the finding if confidence ≥0.70; suppress otherwise. A single agent's low-confidence hit is usually noise.
6. **Two agents agree (2+)** → fingerprint findings as `path:line:issue_class`; when two specialists hit the same fingerprint, tag the merged finding `MULTI-SPECIALIST CONFIRMED ({s1} + {s2})` and boost confidence by +0.05 (capped at 1.0). Two-agent overlap is evidence-worthy even when it's below the 3-agent threshold.
7. **All agents agree (3+)** → boost confidence by 0.10 (capped at 1.0). Convergent findings from independent perspectives are more trustworthy. Tag as `MULTI-SPECIALIST CONFIRMED ({s1} + {s2} + {s3}...)`.
8. **Apply confidence rubric** → suppress findings below threshold per the main skill's rubric.
9. **Apply false-positive suppression** → remove entries matching the categories in the main skill.
10. **Sort by severity** (Critical > Important > Medium > Minor), then by confidence within each level.
11. **Cap total findings** at 20 across all agents. If more exist, note the overflow count.

## Output Format

Same as the standard review output format, with an additional header:

```
## Review: [brief title] (deep)
Agents: correctness, security, testing, maintainability, performance, reliability [+ conditional: api-contract, data-migration, cloud-infra] [+ red-team if triggered]
Cross-lens agreements: N findings tagged MULTI-SPECIALIST CONFIRMED (K at 3+, M at 2)

### Critical
...
```

Include the count of multi-specialist-confirmed findings in the header so reviewers can scan for convergent signal without reading every finding.

## When Deep Review Adds Less Value

- Pure documentation/markdown changes -- single-pass is sufficient
- Mechanical refactors (renames, moves) with no logic changes -- single-pass catches drift
- Single-file changes under 50 lines -- multi-agent overhead isn't justified
- The user explicitly requested a quick review

In these cases, fall back to standard single-pass even if complexity signals triggered.
