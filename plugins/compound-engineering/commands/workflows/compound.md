---
name: workflows:compound
description: Parallel-agent workflow to document a solved problem for team reuse. Use after debugging, fixing, or resolving a bug, incident, or tricky edge case worth capturing for future sessions.
argument-hint: "[optional: brief context about the fix]"
---

# /compound

**Context:** #$ARGUMENTS

Coordinate multiple subagents working in parallel to document a recently solved problem. If context was provided above, use it as the starting point for Phase 1.

## Purpose

Captures problem solutions while context is fresh, creating structured documentation in `docs/solutions/` with YAML frontmatter for searchability and future reference. Uses parallel subagents for maximum efficiency.

**Why "compound"?** Each documented solution compounds your team's knowledge. The first time you solve a problem takes research. Document it, and the next occurrence takes minutes. Knowledge compounds.

## Usage

```bash
/workflows:compound                    # Document the most recent fix
/workflows:compound [brief context]    # Provide additional context hint
```

## Execution Strategy: Two-Phase Orchestration

<critical_requirement>
**Only ONE file gets written - the final documentation.**

Phase 1 subagents return TEXT DATA to the orchestrator. They must NOT use Write, Edit, or create any files. Only the orchestrator (Phase 2) writes the final documentation file.
</critical_requirement>

### Phase 1: Parallel Research

<parallel_tasks>

Launch these subagents IN PARALLEL. Each returns text data to the orchestrator.

#### 1. **Context Analyzer**
   - Extracts conversation history
   - Identifies problem type, component, symptoms
   - Quantifies impact with concrete metrics: duration, affected users/requests, SLA or revenue impact. Prefer specific numbers ("~2,000 requests failed over 45 minutes") over vague descriptions ("some users were affected")
   - Reconstructs chronological timeline from first symptom to resolution (include timestamps where available)
   - Validates against schema
   - Returns: YAML frontmatter skeleton + impact summary + timeline section

#### 2. **Solution Extractor**
   - Analyzes all investigation steps
   - Identifies root cause using iterative "why" questioning (5 Whys): trace from the immediate failure through each contributing cause until reaching a systemic gap. "Deploy failed" → "Migration timed out" → "Table had 50M rows, no online DDL" → systemic cause: no migration size review process
   - Frame all findings as systemic gaps, not individual mistakes. "The deploy process lacks migration size checks" not "Engineer X forgot to check"
   - Extracts working solution with code examples
   - Returns: Solution content block with root cause chain

#### 3. **Related Docs Finder**
   - Searches `docs/solutions/` for related documentation
   - Identifies cross-references and links
   - Finds related GitHub issues
   - Returns: Links and relationships

#### 4. **Prevention Strategist**
   - Develops prevention strategies
   - Creates best practices guidance
   - Generates test cases if applicable
   - Produces concrete action items: each action needs an owner (person or team) and a deadline. Actions without owners don't get done
   - Returns: Prevention/testing content + action items list

#### 5. **Category Classifier**
   - Determines optimal `docs/solutions/` category
   - Validates category against schema
   - Suggests filename based on slug
   - Returns: Final path and filename

</parallel_tasks>

### Phase 2: Assembly & Write

<sequential_tasks>

**WAIT for all Phase 1 subagents to complete before proceeding.**

The orchestrating agent (main conversation) performs these steps:

1. Collect all text results from Phase 1 subagents into a single assembled payload (YAML frontmatter + timeline + impact + solution + root cause + prevention + path).
2. Invoke the `compound-docs` skill via an explicit Skill tool call (not a prose instruction):

   ```
   Skill({ skill: "compound-docs", args: "<assembled payload from step 1>" })
   ```

   The skill owns YAML frontmatter validation, category/path resolution, directory creation, file writing, and cross-reference linking. Do NOT reimplement any of those steps here — if the write behavior needs to change, update the skill.

</sequential_tasks>

### Phase 3: Optional Enhancement

**WAIT for Phase 2 to complete before proceeding.**

<parallel_tasks>

Based on problem type, optionally invoke specialized agents to review the documentation:

- **performance_issue** → `performance-oracle`
- **security_issue** → `security-sentinel`
- **database_issue** → `database-guardian`
- **test_failure** → `writing-tests` skill
- Any code-heavy issue → `code-simplicity-reviewer`

</parallel_tasks>

## What It Captures

- **Problem symptom**: Exact error messages, observable behavior
- **Timeline**: Chronological sequence from first symptom to resolution, with timestamps where available. Captures the debugging path, not just the outcome
- **Investigation steps tried**: What didn't work and why
- **Root cause analysis**: 5 Whys chain from immediate failure to systemic gap, framed as process/system deficiencies (blameless)
- **Impact**: Concrete metrics -- duration, affected users/requests, SLA or revenue impact. Specific numbers ("~2,000 requests failed over 45 minutes") over vague descriptions ("some users were affected")
- **Working solution**: Step-by-step fix with code examples
- **Prevention strategies**: How to avoid in future
- **Action items**: Follow-up tasks with assigned owner (person or team) and deadline
- **Cross-references**: Links to related issues and docs

## Preconditions

<preconditions enforcement="advisory">
  <check condition="problem_solved">
    Problem has been solved (not in-progress)
  </check>
  <check condition="solution_verified">
    Solution has been verified working
  </check>
  <check condition="non_trivial">
    Non-trivial problem (not simple typo or obvious error)
  </check>
</preconditions>

## What It Creates

**Organized documentation:**

- File: `docs/solutions/[category]/[filename].md`

**Categories auto-detected from problem:**

- build-errors/
- test-failures/
- runtime-errors/
- performance-issues/
- database-issues/
- security-issues/
- ui-bugs/
- integration-issues/
- logic-errors/

## Common Mistakes to Avoid

| ❌ Wrong | ✅ Correct |
|----------|-----------|
| Subagents write files like `context-analysis.md`, `solution-draft.md` | Subagents return text data; orchestrator writes one final file |
| Research and assembly run in parallel | Research completes → then assembly runs |
| Multiple files created during workflow | Single file: `docs/solutions/[category]/[filename].md` |

## Success Output

```
✓ Documentation complete

Subagent Results:
  ✓ Context Analyzer: Identified performance_issue in brief_system
  ✓ Solution Extractor: 3 code fixes
  ✓ Related Docs Finder: 2 related issues
  ✓ Prevention Strategist: Prevention strategies, test suggestions
  ✓ Category Classifier: `performance-issues`

Specialized Agent Reviews (Auto-Triggered):
  ✓ performance-oracle: Validated query optimization approach
  ✓ code-simplicity-reviewer: Solution is appropriately minimal

File created:
- docs/solutions/performance-issues/n-plus-one-brief-generation.md

This documentation will be searchable for future reference when similar
issues occur in the Email Processing or Brief System modules.

What's next?
1. Continue workflow (recommended)
2. Link related documentation
3. Update other references
4. View documentation
5. Other
```

## The Compounding Philosophy

This creates a compounding knowledge system:

1. First time you solve "N+1 query in brief generation" → Research (30 min)
2. Document the solution → docs/solutions/performance-issues/n-plus-one-briefs.md (5 min)
3. Next time similar issue occurs → Quick lookup (2 min)
4. Knowledge compounds → Team gets smarter

The feedback loop:

```
Build → Test → Find Issue → Research → Improve → Document → Validate → Deploy
    ↑                                                                      ↓
    └──────────────────────────────────────────────────────────────────────┘
```

**Each unit of engineering work should make subsequent units of work easier--not harder.**

## Auto-Invoke

<auto_invoke> <trigger_phrases> - "that worked" - "it's fixed" - "working now" - "problem solved" </trigger_phrases>

<manual_override> Use /workflows:compound [context] to document immediately without waiting for auto-detection. </manual_override> </auto_invoke>

## Routes To

`compound-docs` skill

## Related Commands

- `/workflows:plan` - Planning workflow (references documented solutions)
