---
name: ia-agent-native-audit
description: Score each of the 5 agent-native principles (parity, granularity, composability, emergent capability, improvement-over-time) against a codebase and report gaps
argument-hint: "[optional: specific principle to audit]"
disable-model-invocation: true
---

# Agent-Native Architecture Audit

Conduct a comprehensive review of the codebase against agent-native architecture principles, launching parallel sub-agents for each principle and producing a scored report.

**Target:** #$ARGUMENTS

**Modes:**
- `quick` -- single-pass review: capability map, parity checklist, findings by severity, agent-native score. No parallel sub-agents.
- (default) -- deep 8-principle parallel audit with numeric scoring per principle.
- A specific principle name (e.g., `action parity`) -- audit only that principle in depth.

## Quick Mode

When `$ARGUMENTS` is `quick` or contains `quick`:

Follow the `ia-agent-native-architecture` skill for principle definitions. Produce a single-pass review:

1. Explore the codebase: UI actions, agent tools, system prompt construction, context injection
2. Build a capability map: `| UI Action | Location | Agent Tool | Prompt Ref | Status |`
3. Check all 5 core principles: Action Parity, Context Parity, Shared Workspace, Primitives over Workflows, Dynamic Context Injection
4. Report findings by severity (Critical/Warning/Observation) with file:line references
5. Score: `X/Y capabilities are agent-accessible -- Verdict: PASS/NEEDS WORK`

## Deep Mode (default)

### Principles Audited

Full principle definitions and test criteria live in the `ia-agent-native-architecture` skill and its `references/core-principles.md`. This command audits eight principles in parallel:

1. **Action Parity** — whatever the user can do, the agent can do
2. **Tools as Primitives** — tools provide capability, not business logic
3. **Context Injection** — system prompt includes dynamic app state
4. **Shared Workspace** — agent and user operate on the same data
5. **CRUD Completeness** — every entity has full Create/Read/Update/Delete
6. **UI Integration** — agent actions immediately reflected in UI
7. **Capability Discovery** — users can find what the agent can do
8. **Prompt-Native Features** — features defined as prompts, not hardcoded logic

## Workflow

### Step 1: Launch Parallel Sub-Agents

Launch 8 parallel sub-agents using the Task tool with `subagent_type: Explore`, one for each principle. Each sub-agent receives this prompt template (substitute `{PRINCIPLE_NAME}` and `{PRINCIPLE_NUMBER}`):

```
Audit this codebase for principle {PRINCIPLE_NUMBER}: {PRINCIPLE_NAME}.

1. Load the `ia-agent-native-architecture` skill and read the specific section for this principle in references/core-principles.md (if it exists) or the Architecture Review Checklist subsection matching this principle's domain.

2. Enumerate ALL relevant instances in the codebase:
   - Action Parity: user-facing actions (API calls, buttons, forms) and their agent-tool counterparts
   - Tools as Primitives: agent tool files; classify as primitive vs workflow
   - Context Injection: what IS injected into the system prompt vs what should be
   - Shared Workspace: data stores and who reads/writes them
   - CRUD Completeness: entities and their agent-accessible Create/Read/Update/Delete operations
   - UI Integration: how agent writes propagate to the frontend (streaming, polling, events)
   - Capability Discovery: onboarding, help, hints, slash commands, suggested prompts, empty states, self-description
   - Prompt-Native Features: feature definitions — prompt-driven vs hardcoded logic

3. Score as "X out of Y (percentage%)" with specific items counted.

4. Output format:
   ## {PRINCIPLE_NAME} Audit
   ### Inventory
   | Item | Location | Status/Type | Notes |
   ### Score: X/Y (percentage%)
   ### Gaps
   ### Recommendations
```

Dispatch all 8 agents in a single message. Wait for all to return before Step 2.

### Step 2: Compile Summary Report

After all agents complete, compile a summary with:

```markdown
## Agent-Native Architecture Review: [Project Name]

### Overall Score Summary

| Core Principle | Score | Percentage | Status |
|----------------|-------|------------|--------|
| Action Parity | X/Y | Z% | ✅/⚠️/❌ |
| Tools as Primitives | X/Y | Z% | ✅/⚠️/❌ |
| Context Injection | X/Y | Z% | ✅/⚠️/❌ |
| Shared Workspace | X/Y | Z% | ✅/⚠️/❌ |
| CRUD Completeness | X/Y | Z% | ✅/⚠️/❌ |
| UI Integration | X/Y | Z% | ✅/⚠️/❌ |
| Capability Discovery | X/Y | Z% | ✅/⚠️/❌ |
| Prompt-Native Features | X/Y | Z% | ✅/⚠️/❌ |

**Overall Agent-Native Score: X%**

### Status Legend
- ✅ Excellent (80%+)
- ⚠️ Partial (50-79%)
- ❌ Needs Work (<50%)

### Top 10 Recommendations by Impact

| Priority | Action | Principle | Effort |
|----------|--------|-----------|--------|

### What's Working Excellently

[List top 5 strengths]
```

### Step 3: Persist Report

Write the compiled report to `docs/audits/YYYY-MM-DD-agent-native-audit.md`. Commit to git.

## Success Criteria

- [ ] All 8 sub-agents complete their audits
- [ ] Each principle has a specific numeric score (X/Y format)
- [ ] Summary table shows all scores and status indicators
- [ ] Top 10 recommendations are prioritized by impact
- [ ] Report identifies both strengths and gaps

## Optional: Single Principle Audit

If $ARGUMENTS specifies a single principle (e.g., "action parity"), only run that sub-agent and provide detailed findings for that principle alone.

Valid arguments:
- `action parity` or `1`
- `tools` or `primitives` or `2`
- `context` or `injection` or `3`
- `shared` or `workspace` or `4`
- `crud` or `5`
- `ui` or `integration` or `6`
- `discovery` or `7`
- `prompt` or `features` or `8`
