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

## Bounds arithmetic: validate before deriving

`end = start + count - 1` is undefined behavior when `start` is extreme, **even if** a later validation would have rejected it. The overflow happens first; the check never runs.

Correct shape for range writes and slice APIs:

1. Validate the start coordinate.
2. Compare the count, as an unsigned value, against the remaining capacity after the validated start.
3. Only then compute the end coordinate, now proven in range.

Probe with the type's extremes (`INT_MIN`/`INT_MAX`, `SIZE_MAX`) plus a multi-element input, under UBSan. A function that correctly returns "invalid" can still have signed-overflow UB on the way there.

## Wide integers narrowing into a foreign API

A 64-bit value that passes a `>= 0` check can still narrow to something entirely different in a call taking `int`. `4294967296` passes a sign check and arrives as `0`, selecting or destroying the wrong object.

Require `0 <= value <= INT_MAX` at every site where a wide integer crosses into a foreign `int`, enum, or ID parameter. Three refinements that each cost a review round when skipped:

- **Grep the vendor's enum header for negative members before applying a blanket `0..INT_MAX` guard.** Negative sentinels are usually valid inputs, and a naive guard rejects an API's own documented default. Where one exists, use `value < -1 || value > INT_MAX`, or check the parameter's declared default first.
- **The boundary is every crossing site, not the setters.** Constructors, `add*`/builder methods, rule and enum parameters all reach the same foreign `int`. Define the boundary as a predicate up front and fix every site in one pass; a constructor that throws needs the throwing form of the check, not the one that returns an error.
- **Listing call sites is not auditing them.** Script it. Parse each function body, collect the wide-integer variables, find those passed by value into a foreign call, and flag any whose body lacks an *upper* bound for that variable. A sign-only `< 1` or `<= 0` check must not count as validated. Run to zero and keep the script with the review notes, because eyeballing which sites are "already guarded" is what turns one review into six.

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
