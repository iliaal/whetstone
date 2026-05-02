# ADR Templates

## Y-statement (quick captures)

```markdown
---
status: accepted
date: YYYY-MM-DD
---
# NNNN. Title

In the context of [situation], facing [concern], we decided [decision], to achieve [quality], accepting [downside].
```

## Lightweight

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

## Full MADR

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

## Deprecation

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

## RFC

Use for decisions needing broad input. Same structure as Full MADR plus:
- **Discussion** section for recording input from stakeholders
- **Timeline** with proposal, review, and decision dates
- **Stakeholders** list of people whose input is needed
