---
name: adr
description: Create Architecture Decision Records with format selection and lifecycle management
argument-hint: "[title or 'list' to view existing ADRs]"
---

# Architecture Decision Records

Create, list, or update ADRs in `docs/decisions/`.

**Input:** #$ARGUMENTS

## Argument handling

- **Empty** (no argument): scan `docs/decisions/` and present existing ADRs as a numbered list with status, title, and date. Then ask: "Create a new ADR? Provide a title."
- **`list`**: same as empty — scan and list existing ADRs. Do not create anything.
- **A short title** (≤8 words): create a new ADR with that title. Ask the user to pick a format (Y-statement, Lightweight, Full MADR, RFC, Deprecation) before generating.
- **A longer topic or question** (>8 words): treat as context for a Full MADR or RFC. Extract the decision subject from the input, confirm the extracted title with the user, then proceed.
- **`deprecate <NNNN>`**: create a Deprecation ADR superseding the referenced ADR number. Read the superseded ADR first to capture its context.

## Process

### 1. Determine action

- If input is `list` or empty: scan `docs/decisions/` and present existing ADRs with status
- If input is a title or topic: create a new ADR
- If input starts with `deprecate`: create a Deprecation ADR (see Argument handling above)

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

Use the template for the chosen format from [adr-templates.md](references/adr-templates.md).

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
