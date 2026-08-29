# C correctness traps that pass review

Bug classes that survive code review, compile clean, and often pass their own tests, because the failing case is a locale, a short read, an extreme input, or a platform the author never ran. Load when reviewing or writing code that formats numbers for machines, reads from a stream, derives a range from user input, or hands an integer to a foreign API.

Distinct from [memory-safety.md](./memory-safety.md): several of these end in memory corruption, but the root cause is arithmetic, environment, or an API contract rather than a lifetime or bounds mistake.

## Locale-dependent float formatting corrupts machine-parsed output

The whole `printf` float family (`%f`, `%g`, `%e`) honours `LC_NUMERIC`'s `decimal_point`. Under a comma-decimal locale (`de_DE`, `fr_FR`, `nl_NL`) `12.5` formats as `12,5`.

The locale is **process-global and shared across threads**. One `setlocale(LC_NUMERIC, ...)` anywhere in the process — application i18n, a library, a neighbouring request in a shared worker — flips it for every subsequent format call. The code that breaks never opts in and gets no error.

This is catastrophic where the output is machine-parsed, because a comma is a *structural* separator in the target grammar:

| Format | What a comma does |
|---|---|
| SVG | Coordinate separator. `points="12,5 30,8"` silently re-segments into four numbers instead of two `(x,y)` pairs: corrupted geometry, no parse error |
| JSON | Syntax error, or a different value |
| CSS, numeric config | Syntax error or silent misparse |

Human-facing **label text** is the opposite case: there `12,5` is correct localised display. The rule is per-purpose, not global. Machine-parsed numerics always emit `.`; display strings may localise.

Two fixes:

1. **Format then normalise.** Emit with `snprintf` as before, then rewrite the decimal separator to `.`. A fixed-notation result is `[-]digits<sep>digits`, so the separator is the lone run of bytes outside `[-0-9]`; collapse that run to a single `.`, which also handles a multi-byte separator. Rounding stays `snprintf`'s, so C-locale output is byte-identical and exact-string tests do not churn.
2. **Hand-roll** integer and fraction emission with `.` hardcoded. Also removes the `printf` parse from a hot path.

**Trap on composite formats.** Never run a whole `rgba(%d,%d,%d,%.3f)` result through a separator normaliser: the argument-separator commas are indistinguishable from the decimal comma. Emit the integer channels separately and pass only the fraction through.

Detection, since there is usually no `setlocale` call anywhere to find and the *absence* is the bug:

```bash
grep -nE '"[^"]*%[-+ 0-9.*]*[fgeFGE]' -r src/
```

Triage each hit by whether it feeds machine-parsed output (must be `.`) or display text (may localise).

## Read loops: index the destination by bytes, not by the running count

`&buf[n]` on a **typed** pointer scales by `sizeof(*buf)`. A chunked read loop that advances a typed pointer by its byte count writes far past the buffer:

```c
gdFont *font = malloc(sizeof(gdFont));
size_t b = 0;
while (b < hdr_size && (n = stream_read(s, (char *)&font[b], hdr_size - b)) > 0)
    b += n;                       /* BUG: &font[b] is font + b*sizeof(gdFont) */
```

`font` is `gdFont *`, so `(char *)&font[b]` is `(char *)font + b * 24` on LP64, not `+ b` bytes. Fix by casting first, then adding: `(char *)font + b`.

**The bug hides on a single full read**, because `b` jumps straight to `hdr_size` and the loop never iterates again. It only fires on a short read, where iteration 2 writes at `font + b*24`. If a sibling read in the same function already indexes a `char *` correctly, that asymmetry is the tell.

### Short reads are deliverable, so write the loop for them

Do not assume a read returns the full requested size until EOF. A partial read (`0 < n < requested`) is a normal outcome for network sockets, pipes, and any pluggable stream layer, and some implementations loop-to-fill for *some* backends only, which makes the partial case look impossible in local testing while remaining reachable in production. Every read loop must be correct under `0 < n < requested`, not just `n == size` or `n == 0`.

### A read returning zero or less is two different events

`n <= 0` collapses "the stream ended" and "the stream failed". A loop that breaks on it falls through to whatever completion code follows, so a failure part-way through commits the partially parsed prefix as though the input had ended there, silently and successfully. Classify before leaving the loop: negative is an error, and zero is an error unless the stream separately reports EOF. Layers below are not consistent about which they return, and a pluggable or user-supplied stream commonly reports failure as zero, so the EOF query is the only thing that separates them. Only a fault-injecting stream reproduces it; no real file will.

## Bounds arithmetic: validate before deriving

`end = start + count - 1` is undefined behavior when `start` is extreme, **even if** a later validation would have rejected it. The overflow happens first; the check never runs.

Correct shape for range writes and slice APIs:

1. Validate the start coordinate.
2. Compare the count, as an unsigned value, against the remaining capacity after the validated start.
3. Only then compute the end coordinate, now proven in range.

The same rule covers the mirror image, a guard that subtracts: every assertion or guard macro containing a subtraction of unsigned operands is a candidate for this audit, and because an unsigned wrap is defined behavior, no sanitizer flags the ones that slip through.

Probe with the type's extremes (`INT_MIN`/`INT_MAX`, `SIZE_MAX`) plus a multi-element input, under UBSan. A function that correctly returns "invalid" can still have signed-overflow UB on the way there.

## Wide integers narrowing into a foreign API

A 64-bit value that passes a `>= 0` check can still narrow to something entirely different in a call taking `int`. `4294967296` passes a sign check and arrives as `0`, selecting or destroying the wrong object.

Require `0 <= value <= INT_MAX` at every site where a wide integer crosses into a foreign `int`, enum, or ID parameter. Three refinements that each cost a review round when skipped:

- **Grep the vendor's enum header for negative members before applying a blanket `0..INT_MAX` guard.** Negative sentinels are usually valid inputs, and a naive guard rejects an API's own documented default. Where one exists, use `value < -1 || value > INT_MAX`, or check the parameter's declared default first.
- **The boundary is every crossing site, not the setters.** Constructors, `add*`/builder methods, rule and enum parameters all reach the same foreign `int`. Define the boundary as a predicate up front and fix every site in one pass; a constructor that throws needs the throwing form of the check, not the one that returns an error.
- **Listing call sites is not auditing them.** Script it. Parse each function body, collect the wide-integer variables, find those passed by value into a foreign call, and flag any whose body lacks an *upper* bound for that variable. A sign-only `< 1` or `<= 0` check must not count as validated. Run to zero and keep the script with the review notes, because eyeballing which sites are "already guarded" is what turns one review into six.

## A decoder's accept set must match its conversion arithmetic

A hand-rolled decoder makes two independent decisions, "is this byte acceptable" and "what does it decode to", and both must agree on the exact character set. A case-insensitive accept check (`isxdigit`, an `[0-9a-fA-F]` class) in front of a conversion branching on one case boundary (`c >= 'A' ? c - 0x37 : c - 0x30`) accepts more than the arithmetic handles: every byte in the gap passes validation and decodes to the wrong value, with no error, no rejection, and no crash. Lowercase hex is the usual gap, and encoders that emit uppercase by specification do not stop real input from arriving lowercase.

This is the opposite of over-lenient validation, which drops characters. Here validation is correct and the transform is narrow, so the corruption is silent and the round trip is what exposes it. Prefer the project's shared digit helper to a re-rolled magic-offset ternary, since the helper already covers every case; where one must be written, check the accept set against every case the arithmetic can be handed.

## NUL truncation is accidental protection, and removing it resurrects the injection

A value carried as a NUL-terminated `char *` loses everything from the first embedded NUL, so a reader splicing it into protocol text never sees a payload hidden behind one. That truncation masks injection rather than preventing it, and nothing in the code says so.

Converting such a value to a length-carrying type for fidelity is the moment the masked surface goes live, and it needs two changes, not one. Replace `strcspn`-style scanning, which stops at the first NUL and therefore under-scans a length-carrying value, with `memchr` over the real length, taking the earliest terminator found. Then audit every reader of the value, classifying each by which append form it uses rather than by the field name: a length-aware append and a `strlen`-bounded one differ by one token and read as type cleanup in review. Each reader either gains the length-bounded scan or deliberately keeps the truncating form.

The test that proves the conversion did work carries a NUL before the terminator sequence. On the old code the value truncates, nothing fires, and the test is genuinely red before and green after; without that case the change looks like a no-op refactor. Before calling any such delta a regression, check whether the same sink is fed by other sources that were already length-aware and already unguarded: consistency with an unguarded sibling is a smaller finding than a fresh hole.

## A zero-length token underflows the length arithmetic and stops forward progress

A generated lexer whose condition has no default rule backtracks, on unmatched input, to the nearest accept state, and that can be a zero-length accept: the cursor never moves and the token length is zero. Two failures then compound. Unsigned length arithmetic in the rule body, `len = token_len - prefix_len`, underflows to an enormous size and reaches the allocator, and the unmoved cursor makes the next call match zero length at the same offset forever.

Clamping the subtraction fixes only the first and converts the crash into an infinite loop emitting empty tokens, so the fix belongs at the accept: give the unmatched input a rule that consumes at least one byte, either a default rule for the condition or a narrow rule for the offending characters. An allocation size near `(size_t)-N` is the signature of an unsigned underflow rather than a real request, and the generator's undefined-control-flow warning names exactly which input strings reach the undefined state.

## Function-like macros must not shadow caller variables

A macro that declares its own locals can shadow a caller's variable of the same name, and the argument expression then silently reads the macro's variable instead of the caller's:

```c
#define RETURN_FORMATTED(b) do {                       \
    char *s = alloc(36);                               \
    format36((b), s);                                  \
    return s; } while (0)
```

A caller whose own input is named `s` passes `RETURN_FORMATTED(get_bytes(s))`. After expansion, the argument resolves against the macro's freshly-allocated, uninitialised `s`. The output is garbage, often the recycled contents of a previous call's buffer, and therefore **nondeterministic across runs**.

This is a wrong-data bug, not a memory-safety one: it writes 36 bytes into a 36-byte buffer, so sanitizers stay silent, and a naive exact-output test cannot pin non-deterministic garbage. A round-trip identity assertion catches it immediately (`decode(encode(x)) == x`).

Two rules for any function-like macro that declares locals:

- Prefix every internal name so it cannot collide with a caller's variable (`_mod_tmp`, not `s`).
- Evaluate arguments into locals **at the top**, before declaring anything that could shadow them.

## Portability checks worth running before release

- **32-bit is a different program.** `size_t` is 32-bit there, so a 64-bit length from the wire truncates on assignment. `time_t` can be 32-bit independently of any other type's width, so epoch arithmetic overflows on inputs a 64-bit build handles. A 32-bit container is real coverage; a cross-compile that never executes is not.
- **POSIX-only functions that MSVC lacks**: `timegm` is the classic (`_mkgmtime` is the documented equivalent, same semantics). Never substitute `mktime`, which interprets the `tm` as **local** time and silently shifts results by the runner's timezone.
- **Windows headers define `min` and `max` as macros**, which breaks any use of `std::min`/`std::max` and any templated code containing `(`. Define `NOMINMAX` before any Windows header, project-wide rather than per-file.
- **`a * b + c` is a fused-multiply-add candidate and `FP_CONTRACT` is on by default.** Whether the compiler emits one fused operation with a single rounding or a separate multiply and add with two is a property of the target, and the two results differ by a representable step at integer boundaries. A digit-accumulation parser (`v = 10.f * v + digit`) or any Horner-form evaluation therefore lands on a different value per machine, and a test asserting the specific branch that value selects fails only elsewhere. The fingerprint is a numeric test passing on older x86-64 baselines and failing on arm64 and on distributions that raised their baseline to require FMA. Reproduce it anywhere by toggling `-ffp-contract=off` against `-ffp-contract=fast`; the hardware is not needed to confirm the hypothesis. Assert the contract rather than the branch where both outcomes are correct, and pin contraction per translation unit only when a specific parsed value is load-bearing.
- **Hand-written ELF inline asm writes `call sym@PLT`, never a bare `call sym`.** Assemblers since binutils 2.31 emit a PLT-capable relocation for a bare branch, but some distributions carry a patch reverting that for branches, and the older relocation against a preemptible symbol cannot be resolved in a shared object: the link either demands a position-independent rebuild or produces a text relocation, which is a runtime segfault risk wherever indirect functions are in play. Compiler-generated code always emits the explicit form, so only hand-written asm is exposed, and the failure appears on one vendor's toolchain while every other CI lane stays green. The suffix changes the relocation and never the instruction encoding, so byte-pattern checks over the emitted sequence are unaffected and the object is identical on toolchains that already default to it.
