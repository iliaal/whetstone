# What to Check — Review Category Checklists

Load this reference during the line-by-line review step. Use the category lists to structure your reading and ensure nothing slips through. Each category corresponds to a class of defect that surfaces repeatedly in production code.

## Correctness

- Edge cases (null, empty, boundary values, concurrent access)
- Error paths (are failures handled or swallowed?)
- Type safety (implicit conversions, `any` types, unchecked casts)
- New enum/status/type values — trace through ALL consumers (switch/case, filter arrays, allowlists). Read code outside the diff. Missing handler = wrong default at runtime.

## Maintainability & Readability

- Naming — variables, functions, and classes convey purpose without needing surrounding context
- Function length — long functions that force scrolling; prefer extractable blocks with clear names. Split by responsibility, not line count
- Nesting depth — more than 3 levels of indentation signals a need for early returns, guard clauses, or extraction
- Comment quality — comments explain WHY (constraints, workarounds, non-obvious decisions), not WHAT. Flag comments that restate code or will rot as the code changes
- God classes / SRP violations — class with unrelated responsibilities. Split into focused classes
- Leaky abstractions — implementation details exposed in interfaces or public APIs
- Structural remedy — when flagging a structural problem, name the move that fixes it (extract a helper, collapse duplicate branches, separate orchestration from logic, replace a conditional chain with a typed dispatcher), not just the smell. Then test the proposed refactor: does it *reduce* the concepts a reader must hold, or just *relocate* complexity elsewhere? Prefer deleting an abstraction over polishing one
- File size — total file size is an inspection signal separate from diff size; ~1000 total lines in one file is a soft boundary (not a hard cap). A small diff can still push an already-large file past it — ask whether to decompose first, then add

## Performance

- N+1 queries (loop with query per item — use batch/join instead)
- Unbounded collections (arrays/maps without size limits)
- Missing indexes on queried columns

## Adversarial (red-team pass)

- Silent failures — `.catch(() => [])` or log-and-forget patterns that swallow errors and return success
- Trust assumption exploits — frontend-validated data not re-validated on the backend; internal service inputs treated as trusted
- Edge cases under pressure — max input size, zero items, first-run-ever, double-click within 100ms, concurrent identical requests
- Partial completion — operations that can crash mid-way leaving state inconsistent (no rollback, no cleanup)

## AI-generated code lens

Apply when the code is LLM-authored (most diffs are):

- **Over-engineering**: gratuitous defensive checks for cases the type system or framework already prevents; unnecessary abstraction for a single call site; premature generalization of one concrete case into a generic utility
- **Defensive noise**: `try/catch` around operations that cannot throw; null checks on values the signature guarantees non-null; input validation on internal code boundaries already validated upstream
- **Cost bloat**: long chains of model-cost-inducing work (recursive agent dispatch, per-item API calls, unbounded loops) where a single batch or deterministic routine would suffice
- **Scope drift**: "while I'm here" edits to unrelated files; rename refactors piggybacking on a bug fix; formatting churn that dwarfs the real change

Flag these as simplification findings, not bugs. The fix is usually deletion, not addition. For a deeper YAGNI pass on an AI-heavy diff, dispatch `ia-code-simplicity-reviewer` — its six named traps (while-I'm-here, for-future-flexibility, defensive-coding, modernization, consistency, cleanup) map onto this lens and produce a structured simplification report.
