# Orchestrated simplification

## Orchestrator Mode (When Chained With Other Skills)

When this skill is invoked by an orchestrator that also runs `ia-code-review`, `ia-writing-tests`, or `ia-verification-before-completion` on the same scope, each sub-skill re-resolving scope independently wastes tokens and risks drift. Avoid this by resolving scope exactly once and passing a canonical block to every sub-skill.

**Resolved scope format** — the orchestrator builds this once, before dispatching any sub-skill:

```

## Resolved scope
Files:
- path/to/file-a.ts
- path/to/file-b.ts

Commit range: HEAD~3..HEAD (or "uncommitted")

Intent: [one-sentence description pulled from the user request or PR description]

Constraints:
- Preserve public API
- No behavior change
- [other constraints specific to this run]
```

Every chained sub-skill receives this block verbatim in its prompt and uses it as the source of truth — no re-running `git diff --name-only`, no re-parsing the user request, no independent scope resolution. Sub-skills accept `--no-verify --no-report` flags when chained so verification and reporting happen once at the end of the chain, not per-skill. The last sub-skill in the chain runs verification; the orchestrator trusts that result rather than re-verifying.

This prevents two failure modes: scope drift (sub-skill A simplifies one set of files, sub-skill B reviews a different set) and double work (every sub-skill rediscovers the same facts).
