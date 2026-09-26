# plan format

## Planning Files

Scaffold the `.plan/` directory with pre-populated templates using [init-plan.sh](../scripts/init-plan.sh):

```bash
SKILL_DIR="<absolute path of the directory containing this SKILL.md>"
bash "$SKILL_DIR/scripts/init-plan.sh" "Feature Name"
```

Substitute the real absolute path before running; never execute the command with the angle-bracket placeholder. The script refuses to overwrite a `task_plan.md` that still has unchecked tasks (the never-overwrite gate below); pass `--force` only after deciding which plan wins. Anchor the call to `SKILL_DIR` rather than a bare `init-plan.sh`: a relative path resolves against the caller's working directory, not the skill, and breaks from a subdirectory or under a non-Claude harness.

This creates `.plan/task_plan.md` and adds `.plan/` to `.gitignore`.

`.plan/` files are ephemeral working state; do not commit them. Old files are overwritten when starting a new feature. Before overwriting, check the existing `task_plan.md` for unchecked tasks: same work continuing means update in place, different work over an incomplete plan means stop and ask which plan wins. Never bulk-close or silently discard another plan's open items (the same rule applies to items mirrored into an external tracker). Within a multi-phase feature, use numbered intermediate files (`01-setup.md`, `02-phase1-complete.md`) to preserve state across phases. `docs/plans/` is the separate, committed home for a formal plan document; `.plan/` supports the work session.

| File | Purpose | Update When |
|------|---------|-------------|
| `.plan/task_plan.md` | Goal, decisions, next step, phases, discoveries that affect the plan, and errors that affect recovery | When a decision, phase state, or recovery point changes |

Do not create secondary findings or progress logs solely to prove activity. Add another planning artifact only when it carries state that `task_plan.md` cannot express clearly or when the user requested it as a deliverable.

## Test Discovery (Existing Projects)

For existing code, discover the test landscape before planning: find related test/spec files (`Glob("**/*test*")`, `Grep`), read the canonical test command from config (`package.json` scripts, `pytest.ini`, `phpunit.xml`, CI), and note coverage gaps. The plan should extend existing test patterns, not introduce new frameworks. Skip for greenfield projects with no tests yet.

## Reference Implementations

When an authorized reference implementation embodies target behavior, cite the source and plan to reimplement its *semantics*. Source reveals behavior more precisely than a summary, but does not override the user's specification or establish that existing bugs are requirements. Record a `ref:` pointer so the implementer reads the source; resolve conflicts against the governing requirements. Full guidance in [execution-and-methodology.md](./execution-and-methodology.md).

## Plan Template

```markdown
# Plan: [Feature/Task Name]

**Spec:** [optional -- path or URL to the spec/design doc this plan implements; distinct from a `ref:` pointer, which names a reference implementation to reimplement, not a spec to satisfy]

## Approach
[1-3 sentences: what and why]

## Scope
- **In**: [what's included]
- **Out**: [what's explicitly excluded]

## Global Constraints
[Binds every phase: version floors; naming/format rules; platform limits; security/compatibility invariants. Exact spec values verbatim, never paraphrased. Every task inherits these. Omit if none.]

## Key Decisions (review first)
[Decisions likeliest to change on review: data model shapes; new type/interface contracts; user-facing or UX flows. Per decision: choice, discarded alternative, one-line why. Listed first so review redirects design before mechanical work is planned around it; mechanical refactoring stays in the phases. Omit if no non-obvious choice was made.]

## File Structure
[ALL files created or modified, one-line responsibility each; locks decomposition before tasks are defined. Write for a zero-context engineer.]

| File | Action | Responsibility |
|------|--------|---------------|
| `path/to/file.ts` | Create | [what this file does] |
| `path/to/existing.ts` | Modify | [what changes and why] |

## Next Step
[one line: the phase and task to resume on]

## Phase 1: [Name]
**Status**: pending | in_progress | complete
**Files**: [specific files owned by this phase]
**Tasks**:
- [ ] [Verb-first atomic task] -- `path/to/file.ts`
- [ ] [Next task]
**Verify**: [specific test: "POST /api/users → 201", not "test feature"]
**Exit**: [clear done definition]

## Phase 2: [Name]
...

## Deferred to Implementation
- [Things intentionally left unspecified -- details that depend on what you find in the code]

## Open Questions
- [Only genuinely blocking unknowns]
```

### Plan Quality Rules

**Keep phase state current.** Changing a phase's `Status` also refreshes `## Next Step`. That one line is what the resume protocol reads after a compaction or a new session, so a stale `Next Step` is worse than none: it resumes work that already happened.

**Record decisions, not code bodies.** A test step names the test and its assertions, with the spec's exact values. A code step names the file, the exact signature, and the pinned values; include a body only for an algorithm the signature and tests leave undetermined. A verification step gives the command and its passing output. A step that depends on another task's work restates that task's interface (file and signature) instead of repeating its code.

**Proportion check.** After drafting, compare the plan's length to the spec it implements. A plan much longer than its spec, or one made mostly of code blocks, is an implementation transcript: replace bodies with signatures and assertions. Placeholders (below) are the opposite failure.

**No placeholders in tasks.** Every task must contain the concrete decision it carries: a signature, assertion, command, spec value, or file path. Forbid: "TBD", "TODO", "handle errors appropriately", "add validation", "implement as needed", "similar to above", "Similar to Task N", "See above." Tasks may be read out of order; repeat the spec value, signature, or file path in every task that needs it. A step that cannot be specified concretely needs further breakdown before it belongs in a plan.

**Type-consistency check.** After writing all tasks, scan for naming drift. If Task 3 says `clearLayers()` but Task 7 says `clearFullLayers()`, that's a bug in the plan. Function names, variable names, and file paths must be consistent across all tasks.

**No gold-plating.** Build exactly what the spec requires, with no features or "nice-to-haves" beyond it. Quote the exact spec requirements in the plan and flag any additions explicitly as scope expansion needing approval.

**Keep the deliverable ahead of the apparatus.** Every process or operations item names the capability or observed defect class it gates. Stop adding checks, matrices, or plan structure when the existing machinery is sufficient to keep implementation honest. Record deferred rigor as debt rather than building it speculatively.

**Do not edit the target down to the implementation.** A plan or specification change needs independent product or technical justification. A weaker acceptance criterion is not a fix for code that fails the original one.

**Keep closures vertical.** Internal plan steps may isolate one action, but a closable phase or external work item includes its implementation and tests and ends in runnable behavior. Do not turn types, implementation, tests, and documentation for one capability into separate completion credits.

**Front-load high-variance decisions.** Order the plan document by how likely each part is to change on review, not by execution order; the template's *Key Decisions* bracket defines what goes there. Execution order still governs the phases themselves.
