---
name: adr
description: Create Architecture Decision Records with format selection and lifecycle management
argument-hint: "[title or 'list' to view existing ADRs]"
---

# Architecture Decision Records

Create, list, or update ADRs in `docs/decisions/`.

**Input:** #$ARGUMENTS

## Process

### 1. Determine action

- If input is `list` or empty: scan `docs/decisions/` and present existing ADRs with status
- If input is a title or topic: create a new ADR

### 2. Choose format

Ask which format fits the decision:

| Format | When to use | Size |
|--------|------------|------|
| **Y-statement** | Quick, uncontroversial decisions | 1 line |
| **Lightweight** | Clear decisions with minimal context needed | ~20 lines |
| **Full MADR** | Significant decisions with multiple alternatives | ~50 lines |
| **RFC** | Decisions needing broad input or discussion | ~80 lines |
| **Deprecation** | Superseding a previous ADR | ~30 lines |

### 3. Gather context

Ask about:
- What decision was made (or needs to be made)
- What alternatives were considered
- What constraints drove the choice
- What consequences are accepted

For deprecation ADRs: which ADR is being superseded and why.

### 4. Generate the ADR

**Directory**: `docs/decisions/` (create with `mkdir -p` if needed)

**Naming**: `NNNN-kebab-case-title.md` where NNNN is the next sequential number. Check existing files to determine the next number.

**Lifecycle states**: proposed, accepted, deprecated, superseded

### Templates

**Y-statement** (for quick captures):
```markdown
---
status: accepted
date: YYYY-MM-DD
---
# NNNN. Title

In the context of [situation], facing [concern], we decided [decision], to achieve [quality], accepting [downside].
```

**Lightweight**:
```markdown
---
status: accepted
date: YYYY-MM-DD
---
# NNNN. Title

## Context

[What is the issue that we're seeing that is motivating this decision?]

## Decision

[What is the change that we're proposing and/or doing?]

## Consequences

[What becomes easier or more difficult to do because of this change?]
```

**Full MADR**:
```markdown
---
status: proposed
date: YYYY-MM-DD
deciders: [names]
---
# NNNN. Title

## Context and Problem Statement

[Describe the context and problem in 2-3 sentences]

## Decision Drivers

- [Driver 1]
- [Driver 2]

## Considered Options

1. [Option 1]
2. [Option 2]
3. [Option 3]

## Decision Outcome

Chosen option: "[Option N]", because [justification].

### Positive Consequences

- [e.g., improvement of quality attribute]

### Negative Consequences

- [e.g., trade-off accepted]

## Pros and Cons of the Options

### [Option 1]

- Good, because [argument]
- Bad, because [argument]

### [Option 2]

- Good, because [argument]
- Bad, because [argument]
```

**Deprecation**:
```markdown
---
status: deprecated
date: YYYY-MM-DD
superseded-by: NNNN-new-decision.md
---
# NNNN. [Original Title] [DEPRECATED]

Superseded by [NNNN. New Decision](NNNN-new-decision.md).

## Original Context

[Brief summary of the original decision]

## Why Deprecated

[What changed that invalidates the original decision]

## Migration Plan

- [ ] [Step to migrate away from the old decision]
- [ ] [Update affected code/config]
- [ ] [Verify migration complete]
```

### 5. Review checklist

Before saving:
- [ ] Context is complete -- a reader unfamiliar with the discussion can understand why
- [ ] Alternatives were genuinely considered (not just the chosen option)
- [ ] Consequences state real trade-offs, not just benefits
- [ ] Status is correct (proposed if needs review, accepted if decided)

## Constraints

- Never modify existing accepted ADRs without asking -- create a deprecation ADR instead
- Keep ADRs focused on one decision each
- Link related ADRs to each other when relevant
