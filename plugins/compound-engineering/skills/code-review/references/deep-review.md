# Deep Review Process

Multi-agent review that dispatches parallel specialist agents, each analyzing the same diff through a single lens. Produces a unified, deduplicated report.

## Specialist Agents

Dispatch all agents in parallel (read-only, safe to parallelize). Each receives the full diff, the PR description/intent, and the scope resolution results.

| Agent | Lens | Focus | Model |
|-------|------|-------|-------|
| correctness | Logic & behavior | Intent alignment (code matches stated PR intent), edge cases, off-by-ones, error paths, type safety, null handling, async ordering, state management | default |
| security | Attack surface | Injection vectors (SQL, XSS, CSRF, SSRF, command), auth/authz gaps, secrets exposure, trust boundaries, race conditions. Load [security-patterns.md](./security-patterns.md) | default |
| testing | Coverage gaps | Untested code paths, missing edge case tests, mock quality, behavioral vs implementation testing, regression test coverage | haiku |
| maintainability | Long-term health | Coupling, naming, complexity, API surface changes, SRP violations, leaky abstractions, dead code | haiku |
| performance | Efficiency | N+1 queries, unbounded collections, missing indexes, unnecessary allocations, cache opportunities, algorithmic complexity | haiku |
| reliability | Failure resilience | Error handling completeness, timeout/retry logic, circuit breakers, resource cleanup on error paths, graceful degradation. Load [reliability-patterns.md](./reliability-patterns.md) | haiku |
| cloud-infra | Infrastructure | Terraform/IaC review, cloud architecture, cost implications, disaster recovery. Only dispatch when diff touches infrastructure files (*.tf, Dockerfile, docker-compose.*, CI/CD configs). Use `cloud-architect` agent. | haiku |
| api-contract | API surface | Breaking changes (removed fields, type changes, new required params), versioning strategy, error response consistency, backwards compatibility, documentation drift. Only dispatch when diff touches public endpoints, exported interfaces, or API route files. | haiku |
| data-migration | Migration safety | Reversibility (can it roll back?), data loss risk, lock duration on large tables, backfill strategy, index creation timing, multi-phase safety (deploy code first, then migrate). Only dispatch when diff includes migration files. Use `database-guardian` agent. | default |

### Agent Prompt Template

Each specialist receives:

```
Review this diff as a {lens} specialist. Focus exclusively on {focus area}.

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
- **testing**, **maintainability**, **performance**, **api-contract**: use haiku (pattern-matching tasks that don't require deep reasoning)

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

After all agents return:

1. **Deduplicate** -- same file:line appearing in multiple agents' findings: keep the highest-severity version, note which lenses flagged it (cross-lens agreement increases confidence)
2. **Cross-lens boost** -- if 2+ agents independently flag the same location, bump confidence by 0.10 (capped at 1.0). Convergent findings from independent perspectives are more trustworthy.
3. **Apply confidence rubric** -- suppress findings below threshold per the main skill's rubric
4. **Apply FP suppression** -- remove false positives per the main skill's categories
5. **Sort by severity** (Critical > Important > Medium > Minor), then by confidence within each level
6. **Cap total findings** at 20 across all agents. If more exist, note the overflow count.

## Output Format

Same as the standard review output format, with an additional header:

```
## Review: [brief title] (deep)
Agents: correctness, security, testing, maintainability, performance, reliability [+ conditional: api-contract, data-migration, cloud-infra] [+ red-team if triggered]
Cross-lens agreements: N findings flagged by 2+ agents

### Critical
...
```

## When Deep Review Adds Less Value

- Pure documentation/markdown changes -- single-pass is sufficient
- Mechanical refactors (renames, moves) with no logic changes -- single-pass catches drift
- Single-file changes under 50 lines -- multi-agent overhead isn't justified
- The user explicitly requested a quick review

In these cases, fall back to standard single-pass even if complexity signals triggered.
