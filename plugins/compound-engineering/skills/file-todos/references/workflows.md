# Todo Workflows

## Creating a New Todo

**To create a new todo from findings or feedback:**

1. Determine next issue ID: `ls todos/ | grep -o '^[0-9]\+' | sort -n | tail -1`
2. Copy template: `cp assets/todo-template.md todos/{NEXT_ID}-pending-{priority}-{description}.md`
3. Edit and fill required sections:
   - Problem Statement
   - Findings (if from investigation)
   - Proposed Solutions (multiple options)
   - Acceptance Criteria
   - Add initial Work Log entry
4. Determine status: `pending` (needs triage) or `ready` (pre-approved)
5. Add relevant tags for filtering

**When to create a todo:**
- Requires more than 15-20 minutes of work
- Needs research, planning, or multiple approaches considered
- Has dependencies on other work
- Requires manager approval or prioritization
- Part of larger feature or refactor
- Technical debt needing documentation

**When to act immediately instead:**
- Issue is trivial (< 15 minutes)
- Complete context available now
- No planning needed
- User explicitly requests immediate action
- Simple bug fix with obvious solution

## Triaging Pending Items

**To triage pending todos:**

1. List pending items: `ls todos/*-pending-*.md`
2. For each todo:
   - Read Problem Statement and Findings
   - Review Proposed Solutions
   - Make decision: approve, defer, or modify priority
3. Update approved todos:
   - Rename file: `mv {file}-pending-{pri}-{desc}.md {file}-ready-{pri}-{desc}.md`
   - Update frontmatter: `status: pending` -> `status: ready`
   - Fill "Recommended Action" section with clear plan
   - Adjust priority if different from initial assessment
4. Deferred todos stay in `pending` status

**Use slash command:** `/triage` for interactive approval workflow

## Managing Dependencies

**To track dependencies:**

```yaml
dependencies: ["002", "005"]  # This todo blocked by issues 002 and 005
dependencies: []               # No blockers - can work immediately
```

**To check what blocks a todo:**
```bash
grep "^dependencies:" todos/003-*.md
```

**To find what a todo blocks:**
```bash
grep -l 'dependencies:.*"002"' todos/*.md
```

**To verify blockers are complete before starting:**
```bash
for dep in 001 002 003; do
  [ -f "todos/${dep}-complete-*.md" ] || echo "Issue $dep not complete"
done
```

## Updating Work Logs

**When working on a todo, always add a work log entry:**

```markdown
### YYYY-MM-DD - Session Title

**By:** Claude Code / Developer Name

**Actions:**
- Specific changes made (include file:line references)
- Commands executed
- Tests run
- Results of investigation

**Learnings:**
- What worked / what didn't
- Patterns discovered
- Key insights for future work
```

Work logs serve as:
- Historical record of investigation
- Documentation of approaches attempted
- Knowledge sharing for team
- Context for future similar work

## Completing a Todo

**To mark a todo as complete:**

1. Verify all acceptance criteria checked off
2. Update Work Log with final session and results
3. Rename file: `mv {file}-ready-{pri}-{desc}.md {file}-complete-{pri}-{desc}.md`
4. Update frontmatter: `status: ready` -> `status: complete`
5. Check for unblocked work: `grep -l 'dependencies:.*"002"' todos/*-ready-*.md`
6. Commit with issue reference: `feat: resolve issue 002`

---

## Integration with Development Workflows

| Trigger | Flow | Tool |
|---------|------|------|
| Code review | `/workflows:review` -> Findings -> `/triage` -> Todos | Review agent + skill |
| PR comments | `/resolve-pr-parallel` -> Individual fixes -> Todos | gh CLI + command |
| Code TODOs | `/resolve-todo-parallel` -> Fixes + Complex todos | Agent + skill |
| Planning | Brainstorm -> Create todo -> Work -> Complete | Skill |
| Feedback | Discussion -> Create todo -> Triage -> Work | Skill + slash |
