# C++ legibility: the deep rules and a worked refactor

Supplement to the SKILL.md body. Load when refactoring existing C++, when a review needs a rule stated precisely, or when deciding how far to push a decomposition.

Adapted from [write-legible-c](https://github.com/7etsuo/write-legible-c) by 7etsuo (MIT), with the C-specific error model replaced by C++ vocabulary types and the decomposition guard strengthened.

## Why these rules exist

Every rule targets one cost: the tokens and working memory needed to reason about any region of code. A rule earns its place by making a symbol greppable to few sites, keeping an edit local, or removing a path the reader must simulate.

The empirical case, briefly:

- Stripping identifiers degrades model performance even on execution tasks that should depend only on structure, so naming is a semantic channel and not decoration (arXiv 2510.03178). Human comprehension studies attribute up to a 30 percent effect to good names (Feitelson et al., ICPC).
- Models generate better against precise concise identifiers than verbose composites (arXiv 2508.06414).
- Model-perceived complexity, driven by semantic hierarchy depth and branching breadth, correlates with task performance after controlling for code length (arXiv 2602.07882).
- Standard complexity metrics predict whether generated code passes, which is why the budget below is numeric rather than a feeling (arXiv 2505.23953).

## The decomposition guard

State this before any splitting rule, and apply it as a filter on every proposed helper:

> If the most honest name for a candidate helper merely paraphrases its body, inline it and stop.

A helper earns existence by naming a concept, owning an error value, or isolating a side effect. Nothing else counts. Applied late, the line-count and nesting rules produce a hundred two-line functions and turn every read into a pointer chase.

C++ adds a second failure mode the C original does not have: a helper extracted as a *private member function* also widens the class. Prefer a file-local function in an anonymous namespace, or a `static` member, unless the helper genuinely needs the object's state. Every private member is another thing a reader of the header must scan past.

## Function rules

- One job per function. A contract comment needing the word "and" means two functions.
- Target 15 lines, hard cap 40. Nesting depth 2, guard clauses first.
- Past 4 parameters, the list is a struct trying to exist. In C++ that struct is often a named options type, which also kills the call-site ambiguity of three consecutive `bool` arguments.
- Classify every function as orchestrator (calls helpers, checks results, branches on named predicates), leaf (straight-line logic calling only accessors and pure utilities), or adapter (wraps exactly one foreign call and translates its convention). Never a mix.
- Cognitive complexity target 8, hard cap 15, by the Sonar rules that charge each break in linear flow and charge nesting progressively (G. Ann Campbell, SonarSource). The metric is a tripwire, not a goal.

## Naming

- Functions are verb_object. Predicates start `is_`/`has_` and are never negated.
- Precise beats verbose: `retry_count`, not `number_of_connection_retry_attempts`.
- Name length scales with the distance between declaration and last use.
- Units live in the name: `timeout_ms`, `max_payload_bytes`.
- Follow the repo's case convention exactly. Consistency across the file beats any personal preference between `snake_case` and `camelCase`.

## Comments

- Above every public declaration: what it does, ownership and nullability of every pointer or reference parameter, the failure modes, and any thread-safety guarantee. Never restate the signature.
- Inside bodies: comment why, never what.
- No commented-out code. Version control remembers.
- Name the subject rather than "this" or "the above" when more than one antecedent is in scope.

## Full pre-delivery checklist

Two standing exemptions, because a metric must never drive an interface change. The numeric items are tripwires for new or substantially rewritten *internal* code, not a licence to restructure untouched legacy a scoped fix passes through. And none of them justifies altering a released signature or anything ABI-stable — where a rule and a frozen boundary collide, the boundary wins and the deviation gets a comment at the declaration.

1. Any literal that is not 0 or 1? Name it (`constexpr`, not `#define`).
2. Any function over 40 lines, or nested past depth 2? Split it.
3. Any contract comment containing "and"? Split the function.
4. Every failure path reported through the module's one error model?
5. Each new error type: how many throw or return sites? Reduce toward one.
6. Any logic pasted twice? Extract it.
7. Any parameter list past 4, or two adjacent same-typed parameters a caller could swap? Struct it.
8. Header exposes only what callers need? Any implementation detail promotable to the `.cpp`?
9. Any function mixing helper calls with inline logic? Push the logic into a leaf.
10. Any helper whose name paraphrases its body? Inline it.
11. Any class that gained a destructor? Review all five special members.
12. Any `string_view` or reference member outliving its backing store?
13. Any raw `new`/`delete`, or a `shared_ptr` where `unique_ptr` suffices?
14. Any `using namespace` at namespace scope in a header?
15. Any loop that a named `<algorithm>` call states more clearly?
16. Any recursion reachable from external input without an explicit depth bound?

## Worked refactor: good but not good enough

The function below passes generic review: short, flat, guarded, no magic numbers. It still fails.

```cpp
uint16_t Map::eat(Position pos)
{
    Cell cell;
    if (!isInside(pos))
        return 0;
    cell = cells_[pos.row][pos.col];
    if (cell == Cell::Pellet) {
        cells_[pos.row][pos.col] = Cell::Empty;
        pelletCount_--;
        return kScorePellet;
    }
    if (cell == Cell::Power) {
        cells_[pos.row][pos.col] = Cell::Empty;
        pelletCount_--;
        return kScorePower;
    }
    return 0;
}
```

The tells, in order of weight:

1. **The consume block is pasted twice.** Clearing the cell and decrementing the count is one concept in two places. An editor later adding a side effect to consumption patches one copy and misses the other, because nothing links them.
2. **The branches encode data as control flow.** Cell type to score is a mapping, not logic. The next cell type should cost one line, not one pasted block.
3. **Three concepts interleave**: deciding edibility, awarding score, and mutating the grid. No single question about this function has a single home.
4. **`Cell cell;` is left uninitialized above the guard.** Default-initializing a scoped enum with automatic storage leaves an indeterminate value, so the declaration carries no information at all until the assignment below it. Declare at the point where the first valid value exists.

### Stage one: decompose, signature preserved

```cpp
namespace {

bool isEdible(Cell cell)
{
    return cell == Cell::Pellet || cell == Cell::Power;
}

uint16_t scoreFor(Cell cell)
{
    switch (cell) {
    case Cell::Pellet: return kScorePellet;
    case Cell::Power:  return kScorePower;
    default:           return 0;
    }
}

} // namespace

uint16_t Map::eat(Position pos)
{
    if (!isInside(pos))
        return 0;

    const Cell cell = cellAt(pos);
    if (!isEdible(cell))
        return 0;

    consumeCell(pos);
    return scoreFor(cell);
}

void Map::consumeCell(Position pos)
{
    setCell(pos, Cell::Empty);
    pelletCount_--;
}
```

The anonymous-namespace block sits **above** its call site deliberately. Unlike a member function, a free function must be declared before it is used, and ADL does not rescue it in non-template code: defining these below `Map::eat` is a compile error, not a style preference.

`isEdible` and `scoreFor` are pure functions of a `Cell` and need nothing from the object, so they live in an anonymous namespace in the `.cpp` rather than widening the class.

**The proof is change cost, not line count.** Add a fruit cell: the original grows a third pasted block and the next editor patches two of three copies. The refactor grows one line in `isEdible` and one in `scoreFor`. If edibility is exactly "scores nonzero", both collapse into one `constexpr` lookup table with zero branches; state that invariant in a comment above the table.

### Stage two: separate failure from result

Stage one kept one violation deliberately: the return value fuses failure with score, returning 0 for an out-of-bounds position and for an ordinary empty cell alike. A caller cannot distinguish a bug from a normal move.

```cpp
/* Consumes the cell at pos if edible and returns the score awarded,
 * zero when nothing edible is there. Returns nullopt when pos is
 * outside the grid. */
std::optional<uint16_t> Map::eat(Position pos)
{
    if (!isInside(pos))
        return std::nullopt;

    const Cell cell = cellAt(pos);
    if (!isEdible(cell))
        return 0;

    consumeCell(pos);
    return scoreFor(cell);
}
```

This is where C++ diverges from the C original, which needs a status enum and an out-parameter to say the same thing. `std::optional` carries "no answer" in the type, so the caller cannot read a score that was never produced. Where the failure has more than one cause worth distinguishing, use `std::expected<uint16_t, MapError>` (C++23) or the project's equivalent instead, and give each error one construction site.

`cellAt` and `setCell` earn their existence by owning every touch of the grid storage, so the row-major indexing convention lives in two adjacent lines and "what mutates cells" greps to one answer. That is the sanctioned accessor exception from the decomposition guard, and the only shape where a one-line member survives the name test.

### When to stop

| Situation | Stop at |
|---|---|
| Bug fix inside an existing function | The smallest behavior-preserving decomposition that removes the duplication causing the bug |
| Feature work touching the function | Stage one |
| The public API is being designed or is not yet released | Stage two |
| The signature is frozen by ABI or a released header | Stage one, with a deviation comment above the declaration |

A standard is grown by feeding it code that breaks it, and each break becomes a rule or an amendment. Apply the same process to any codebase adopting this document.
