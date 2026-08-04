# C legibility: the deep rules and a worked refactor

Supplement to the SKILL.md body. Load when refactoring existing C, when a review needs a rule stated precisely, or when deciding how far to push a decomposition.

Adapted from [write-legible-c](https://github.com/7etsuo/write-legible-c) by 7etsuo (MIT), with the repository-level and formatting sections dropped and the decomposition guard strengthened.

## Why these rules exist

Every rule targets one cost: the tokens and working memory needed to reason about any region of code. A rule earns its place by making a symbol greppable to few sites, keeping an edit local, or removing a path the reader must simulate.

The empirical case, briefly:

- Stripping identifiers degrades model performance even on execution tasks that should depend only on structure, so naming is a semantic channel and not decoration (arXiv 2510.03178). Human comprehension studies attribute up to a 30 percent effect to good names (Feitelson et al., ICPC).
- Models generate better against precise concise identifiers than verbose composites (arXiv 2508.06414).
- Model-perceived complexity, driven by semantic hierarchy depth and branching breadth, correlates with task performance after controlling for code length; semantics-preserving rewrites that reduce it improve downstream results (arXiv 2602.07882).
- Standard complexity metrics predict whether generated code passes, which is why the function budget below is numeric rather than a feeling (arXiv 2505.23953).

Bounded loops, the recursion restriction, the assert-density rule, smallest scope, and checking every return come from Gerard Holzmann's Power of 10 (NASA/JPL, 2006). Three of its rules are deliberately weakened here, because they are flight-software law rather than general practice: the ban on dynamic allocation after initialization is not adopted at all; the two-assertions-per-function floor is reduced to one assert per state-mutating leaf; and the statically-bounded-loop rule is scoped to loops driven by external input, since ordinary I/O and container traversal in hosted C is bounded dynamically.

MISRA C and CERT C are adopted in spirit: no reliance on undefined behavior, every warning an error. Their single-exit-point rule is rejected, because early returns are what keep branch depth low.

## The decomposition guard

State this before any splitting rule, and apply it as a filter on every proposed helper:

> If the most honest name for a candidate helper merely paraphrases its body, inline it and stop.

A helper earns existence by naming a concept, owning an error value, or isolating a side effect. Nothing else counts. Applied late, the line-count and nesting rules below produce ravioli code, where a hundred two-line functions turn every read into a pointer chase, and the cure is worse than the disease.

The one sanctioned exception is a pair of accessors that own every touch of one storage layout, so an indexing or locking convention lives in two adjacent lines and "what mutates this" greps to one answer. That is isolating a side effect, not paraphrasing a body, but it is the only shape where a one-line accessor survives the test.

## Cognitive complexity budget

Target 8 per function, hard cap 15, measured by the Sonar rules that charge each break in linear flow and charge nesting progressively with depth (G. Ann Campbell, SonarSource, 2017/2023). Code that already conforms to the depth cap and the decomposition guard sits far under budget. The metric is a tripwire, not a goal, and a function that trips it is asking for a name, not a `#pragma`.

## Full pre-delivery checklist

Run against the final diff. This is a gate, not a substitute for reading each section.

Two standing exemptions, because a metric must never drive an interface change. The numeric items below are tripwires for new or substantially rewritten *internal* code; they do not license restructuring untouched legacy code that a scoped fix merely passes through. And no item here justifies altering a frozen public signature — a released API, an ABI-stable export, a wire contract, or generated code. Where a rule and a frozen boundary collide, the boundary wins and the deviation gets a comment at the declaration.

1. Any literal that is not 0 or 1? Name it.
2. Any function over 40 lines, or nested past depth 2? Split it.
3. Any contract comment containing "and"? Split the function.
4. Any `goto` the repo does not already sanction? Decompose, or justify at the label.
5. Every fallible call checked and propagated?
6. Prototypes at the top of the file, matching every definition?
7. Each new error value: how many producers? Reduce toward one.
8. Any logic pasted twice? Extract it.
9. Any parameter list past 4? Struct it.
10. Header exposes only what callers need?
11. Any function mixing helper calls with inline logic? Push the logic into a leaf.
12. Any helper whose name paraphrases its body? Inline it.
13. Parameters out of context, outputs, inputs order? Reorder.
14. Any loop driven by external input without a named bound, or a nonterminating loop without a marker? Bound or mark it.
15. Any recursion reachable from external input? Convert to a bounded worklist.
16. Any state-mutating leaf with zero asserts? State the invariant.
17. Any pointer parameter not written through that lacks `const`?

## Worked refactor: good but not good enough

Most C written by a model fails subtly, not grossly. The function below passes generic review: short, flat, guarded, no magic numbers. It still fails.

```c
uint16_t map_eat(map_t *map, map_pos_t pos)
{
    map_cell_t cell;
    if (map == NULL)
        return 0;
    if (!map_is_inside(pos))
        return 0;
    cell = map->cells[pos.row][pos.col];
    if (cell == MAP_CELL_PELLET) {
        map->cells[pos.row][pos.col] = MAP_CELL_EMPTY;
        map->pellet_count--;
        return MAP_SCORE_PELLET;
    }
    if (cell == MAP_CELL_POWER) {
        map->cells[pos.row][pos.col] = MAP_CELL_EMPTY;
        map->pellet_count--;
        return MAP_SCORE_POWER;
    }
    return 0;
}
```

The tells, in order of weight:

1. **The consume block is pasted twice.** Clearing the cell and decrementing the count is one concept written in two places. The moment the second branch was written, `map_consume_cell` should have been born. An editor later adding a side effect to consumption, a sound cue or a dirty flag, patches one copy and misses the other, because nothing links them.
2. **The branches encode data as control flow.** Cell type to score is a mapping, not logic. A mapping belongs in one lookup leaf, where the next cell type costs one line instead of one pasted block.
3. **Three concepts interleave in one body**: deciding edibility, awarding score, and mutating the map. No single question about this function has a single home.
4. **`map_cell_t cell;` sits uninitialized above the guards.** Declare at the point where the first valid value exists.

### Stage one: decompose, signature preserved

```c
/* True when the cell can be eaten. Pure. */
static bool map_cell_is_edible(map_cell_t cell);

/* Score for consuming a cell. Zero for inedible cells. Pure. */
static uint16_t map_cell_score(map_cell_t cell);

/* Empties the cell and updates pellet accounting. */
static void map_consume_cell(map_t *map, map_pos_t pos);

uint16_t map_eat(map_t *map, map_pos_t pos)
{
    if (map == NULL)
        return 0;
    if (!map_is_inside(pos))
        return 0;

    map_cell_t cell = map->cells[pos.row][pos.col];
    if (!map_cell_is_edible(cell))
        return 0;

    map_consume_cell(map, pos);
    return map_cell_score(cell);
}

static bool map_cell_is_edible(map_cell_t cell)
{
    return cell == MAP_CELL_PELLET || cell == MAP_CELL_POWER;
}

static uint16_t map_cell_score(map_cell_t cell)
{
    switch (cell) {
    case MAP_CELL_PELLET:
        return MAP_SCORE_PELLET;
    case MAP_CELL_POWER:
        return MAP_SCORE_POWER;
    default:
        return 0;
    }
}

static void map_consume_cell(map_t *map, map_pos_t pos)
{
    map->cells[pos.row][pos.col] = MAP_CELL_EMPTY;
    map->pellet_count--;
}
```

**The proof is change cost, not line count.** Add a fruit cell: the original grows a third pasted block and the next editor patches two of three copies. The refactor grows one line in `map_cell_is_edible` and one in `map_cell_score`. Grep improves the same way, because "what mutates cells" now has exactly one answer.

If edibility is exactly "scores nonzero", both pure leaves collapse into one `static const` score table indexed by cell type, with zero branches. State that invariant in a comment above the table when taking that step.

### Stage two: separate failure from result

Stage one kept one violation deliberately: the signature fuses failure with score, returning 0 for a NULL map, an out-of-bounds position, and an ordinary empty cell alike. A caller cannot distinguish a bug from a normal move.

```c
/* Consumes the cell at pos if edible. Writes the score awarded,
 * zero when nothing edible is there. Fails with MAP_ERR_ARG on a
 * NULL pointer and MAP_ERR_BOUNDS on an out-of-range position. */
map_status_t map_eat(map_t *map, uint16_t *out_score, map_pos_t pos);
```

```c
/* Consumes the cell at pos if edible. Returns the score awarded,
 * zero otherwise. */
static uint16_t map_consume_at(map_t *map, map_pos_t pos);

/* True when the cell can be eaten. Pure. */
static bool map_cell_is_edible(map_cell_t cell);

/* Score for consuming a cell. Zero for inedible cells. Pure. */
static uint16_t map_cell_score(map_cell_t cell);

/* Empties the cell and updates pellet accounting. */
static void map_consume_cell(map_t *map, map_pos_t pos);

/* The only two functions that touch cell storage. */
static map_cell_t map_cell_at(const map_t *map, map_pos_t pos);
static void map_set_cell(map_t *map, map_pos_t pos, map_cell_t cell);

map_status_t map_eat(map_t *map, uint16_t *out_score, map_pos_t pos)
{
    if (map == NULL || out_score == NULL)
        return MAP_ERR_ARG;
    if (pos.row >= (size_t)MAP_ROWS || pos.col >= (size_t)MAP_COLS)
        return MAP_ERR_BOUNDS;

    *out_score = map_consume_at(map, pos);
    return MAP_OK;
}

static uint16_t map_consume_at(map_t *map, map_pos_t pos)
{
    map_cell_t cell = map_cell_at(map, pos);
    if (!map_cell_is_edible(cell))
        return 0;

    map_consume_cell(map, pos);
    return map_cell_score(cell);
}

static void map_consume_cell(map_t *map, map_pos_t pos)
{
    assert(map->pellet_count > 0);
    map_set_cell(map, pos, MAP_CELL_EMPTY);
    map->pellet_count--;
}

static map_cell_t map_cell_at(const map_t *map, map_pos_t pos)
{
    return map->cells[pos.row][pos.col];
}

static void map_set_cell(map_t *map, map_pos_t pos, map_cell_t cell)
{
    map->cells[pos.row][pos.col] = cell;
}
```

`map_cell_is_edible` and `map_cell_score` are declared above and carried over unchanged from stage one; their bodies are omitted here only to keep the listing focused.

What the final stage bought, item by item:

- Every failure has a name and exactly one producing site, and normal gameplay no longer wears an error's clothes: an empty cell is `MAP_OK` with score zero.
- `map_cell_at` and `map_set_cell` own every touch of cell storage, so the row-major indexing convention lives in two adjacent lines. This is the sanctioned accessor exception from the decomposition guard above, and it is the only reason those one-line helpers survive the name test.
- `map_consume_cell` asserts the accounting invariant instead of re-validating, because the public boundary already proved the arguments.
- Parameter order follows context, outputs, inputs throughout.

Stage two also forced two amendments to the function rules: orchestrators may branch on named predicates, and leaves may call the module's own accessors. That is the meta-lesson. A standard is grown by feeding it code that breaks it, and each break becomes a rule or an amendment. Apply the same process to any codebase adopting this document.

### When to stop

Stage two is not automatically the target. Choose the stage by the task's scope:

| Situation | Stop at |
|---|---|
| Bug fix inside an existing function | The smallest behavior-preserving decomposition that removes the duplication causing the bug |
| Feature work touching the function | Stage one |
| The module's public API is being designed or is not yet frozen | Stage two |
| The signature is frozen by ABI, a wire format, or generated code | Stage one, with a deviation comment above the declaration |
