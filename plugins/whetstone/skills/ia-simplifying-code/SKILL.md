---
name: ia-simplifying-code
class: discipline
description: >-
  Simplifies, polishes, and declutters code without changing behavior. Use when
  asked to simplify, clean up, refactor, declutter, remove dead code or AI slop,
  or improve readability. For analysis-only reports without code changes, use
  code-simplicity-reviewer agent.
---

# Simplifying Code

## Working rules

- Preserve behavior, interfaces, side effects, and domain intent; prove any unshipped-shape exception has no consumers outside scope.
- Before removing a guard for an external hazard, reproduce its precondition and show the hazard is handled; otherwise retain it.
- Verify standard-library substitutions on empty, null, no-match, ordering, and zero-value cases.

## Principles

| Principle | Rule |
|-----------|------|
| **Preserve behavior** | Output must do exactly what the input did, with no silent feature additions or removals. Specifically preserve: async/sync boundaries (do not convert sync to async or reverse), error propagation paths (do not alter strategy), logging/telemetry/guards/retries that encode operational intent, and domain-specific steps (do not collapse into generic helpers that hide intent). One carve-out: a shape that existed only in an earlier iteration of the current unshipped scope is not protected behavior. Verify it has no deployed, persisted, public, external, dependent-branch, or in-repo caller outside the resolved scope, and that every required caller update fits inside the edit boundary; otherwise keep the compatibility path. This narrow exemption is about shapes with provably zero consumers; it never licenses removing a guard, which is governed by the evidence bar under AI Slop Removal |
| **Explicit over clever** | Prefer explicit variables over nested expressions. Readable beats compact |
| **Simplicity over cleanliness** | Prefer straightforward code over pattern-heavy "clean" code. Three similar lines beat a premature abstraction |
| **Surgical changes** | Touch only what needs simplifying. Match existing style, naming conventions, and formatting of the surrounding code |
| **Surface assumptions** | Before changing a block, identify what imports it, what it imports, and what tests cover it. Edit dependents in the same pass |
| **Delete before simplifying** | Prefer deletion over simplification, simplification over optimization, and optimization over automation. A pass that finds nothing to change is a valid, complete result |

Changing an interface, exported name, persisted format, or path reaches past the import graph. Enumerate the producers, consumers, schemas, fixtures, generators, manifests, scripts and CI recipes, config references, and documents that carry the old identifier, and migrate them in the same pass. Close out by searching for the old identifier: zero hits, or one line accounting for each intentional remainder. Renames rot in the fixture holding the old key and the `.env.example` entry, neither of which any import graph contains. When the identifier is a public or exported API, Stop Conditions applies first: confirm with the user, then enumerate; the sweep runs unprompted only for internal identifiers.


## Process

1. **Read first**: understand the full file and its dependents before changing anything. Apply Chesterton's Fence: when code looks unnecessary but its reason is unclear, check `git blame` before removing it. First understand the reason, then decide if the reason still applies.
2. **Identify invariants**: what must stay the same? Public API, return types, side effects, error behavior
3. **Identify targets**: find the highest-impact simplification opportunities. Impact = readability and maintainability; prioritize: control flow -> naming -> duplication -> data shaping -> types (see Smell -> Fix table)
4. **Apply in order**: control flow → naming → duplication → data shaping → types. Structural changes first, cosmetic last
5. **Verify**: confirm no behavior change: tests pass, types check, imports resolve
6. **Pre-submit scope audit**: walk every changed line and ask "does the requested task explicitly require this line?" If no, revert it and list it as a follow-up under Residual Risks. For the pre-edit complement on ambiguous-scope requests ("simplify my project"), see `ia-verification-before-completion`'s Scope Confirmation gate.


## Stop Conditions

Stop and ask before proceeding when:
- Simplification requires changing a public API (function signatures, return types, exports)
- Behavior parity cannot be verified (no tests exist and behavior is non-obvious)
- Code is intentionally complex for domain reasons (performance-critical, protocol compliance)
- Scope implies a redesign rather than a simplification


## Constraints

- Only simplify what was requested; do not add features, expand scope, introduce new dependencies, or add speculative configurability or flexibility the request did not ask for
- Leave unchanged code untouched; do not add comments, docstrings, or type annotations to lines that were not simplified
- Do not bundle unrelated cleanups into one patch; each simplification should be a coherent, reviewable unit
- Do not introduce framework-wide patterns while simplifying a small local change
- Do not replace understandable duplication with opaque utility layers; three similar lines are better than a premature abstraction
- Keep comments that explain intent, invariants, or non-obvious constraints, and tool directives ([carve-outs](./references/simplification-patterns.md)). Remove comments that restate obvious code behavior. Fix stale comments only on lines this pass touches.
- If a simplification would make the code harder to understand, skip it
- Watch for over-simplification: inlining too aggressively removes names that gave concepts meaning; combining unrelated logic into one function hides distinct responsibilities; removing abstractions that exist for testability breaks the test suite
- When unsure whether a block is dead code, ask instead of deleting
- For artifacts whose value is self-containment (prompts, skill and agent instructions, per-service configuration, vendored policy files), duplication is cheaper than a shared dependency until edits actually drift. Extract only after coordinated changes have repeatedly gone out of sync, or a real consumer of the shared form exists


## Verify

- Tests pass and types check after changes
- No behavior change (same inputs produce same outputs)
- Scope limited to requested files; no drive-by cleanups
- Match test scope to the importer count surfaced in step 1 (Surface assumptions). Zero external importers: scoped tests on the changed paths. One or more external importers, or shared/utility code edited: run tests covering each importer. Run the full suite when the test runner has no path-scoping mechanism.


## Integration

- `ia-code-simplicity-reviewer` agent: analysis-only pass producing a simplification report (no code changes). Use before refactoring to identify targets.


## Output

After simplifying, report:
- **Scope touched**: files and functions modified
- **Key simplifications**: what changed and why (one line each)
- **Verification**: tests pass, types check, no behavior change
- **Residual risks**: assumptions made, areas not touched that may need attention

## Task-specific references

Read the relevant reference before implementing or reviewing the matching behavior:

- For identifying smells, removing AI-generated clutter, or eliminating a guard or workaround: [simplification-patterns.md](./references/simplification-patterns.md).
- When chained with other skills on a shared resolved scope: [orchestrated-simplification.md](./references/orchestrated-simplification.md).
