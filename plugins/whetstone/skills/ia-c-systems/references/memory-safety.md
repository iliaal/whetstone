# C memory safety and undefined behavior

Load when writing or reviewing code that allocates, parses untrusted input, does pointer arithmetic, or recurses. This covers the failure modes the legibility rules do not address: a perfectly legible function can still be a heap overflow.

## Sanitizers

```bash
# Default test build. ASan and UBSan compose; MSan does not compose with ASan.
cc -g -O1 -fno-omit-frame-pointer -fsanitize=address,undefined ...

export ASAN_OPTIONS=detect_leaks=1:detect_stack_use_after_return=1:abort_on_error=1
export UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1
```

- **UBSan is non-fatal by default.** It prints a diagnostic and keeps going, so the process still exits 0 and the suite still passes green with undefined behavior in it. Set `halt_on_error=1`, or compile with `-fno-sanitize-recover=undefined`, or the sanitizer is decoration.
- **MSan (`-fsanitize=memory`) requires every linked dependency to be instrumented**, libc++ included. An uninstrumented library produces false positives that waste more time than the bug. Reach for it only in a fully instrumented build.
- **Valgrind where ASan cannot link** (a plugin loaded by an uninstrumented host, or a preloaded allocator). Slower, catches uninitialized reads ASan misses, and needs no rebuild.
- A custom pooling allocator hides bugs from both tools. Disable it for sanitizer runs, or the clean report means nothing.
- **GCC's `-fsanitize=undefined` group omits `float-cast-overflow`; clang's includes it.** Converting an out-of-range or NaN `double` to an integer type is undefined, and x86-64 `cvttsd2si` and arm64 `fcvtzs` saturate quietly instead of trapping, so the bug is invisible at runtime until an optimizer acts on the assumed-in-range value. Add `-fsanitize=float-cast-overflow` explicitly anywhere externally supplied numbers drive coordinate, index, or size arithmetic, and confirm the check is live against a one-line `(int)1e300` program before trusting a green run.
- **A clean sanitizer run is evidence only against a positive control.** Before reading a report-free run as absence of the bug, add a deliberate fault of the same class, allocate then free then read one byte, and confirm the run aborts on it. A mismatched allocator, an uninstrumented object, or a runtime that failed to interpose reports nothing for the real bug and nothing for the planted one, and the two look identical from the outside.
- **A shared object loaded into a sanitized host is checked only where it was itself compiled with the sanitizer.** The host's runtime still reports the stack overflow, because the signal handler is process-global, but a heap use-after-free executed by an instruction inside an uninstrumented plugin passes silently even though the freeing code poisoned the block correctly. Build the plugin with the same flags and verify with `nm <plugin> | grep -c __asan_`, which is zero on an uninstrumented build.
- **ASan and Valgrind cannot both instrument one process.** An ASan-linked binary aborts under Valgrind at shadow-memory setup, before any program code runs, and the whole suite then reports as leaks. Check the binary with `nm -D <bin> | grep -c __asan` before starting a Valgrind pass. On a machine carrying several builds, an install path's name says nothing about its instrumentation.
- **Match the sanitizer runtime family across a `dlopen` boundary.** A plugin built with one compiler's ASan will not load into a host linked against the other's, and preloading the shared runtime over a host that linked it statically aborts at startup with an incompatible-runtimes error. Read the host's family from `ldd` and build to match. Do not copy a flag string written for the other compiler either: `-fno-sanitize=function` and `-fno-sanitize=vptr` are clang spellings that GCC rejects, and inside a configure script that surfaces as the unrelated "C compiler cannot create executables".
- **Prefer a narrow leak-suppression list to disabling leak detection.** One-time registration tables and a vendored library's process-lifetime singletons report as leaks and tempt a blanket `detect_leaks=0`, which then hides every leak introduced afterwards. Suppress the known frames by substring instead, and silence the suppression summary: the leak checker prints it to stderr by default, where any test comparing exact output folds it in and fails on the extra lines, which reads as a leak failure and misdirects debugging effort.
- **`detect_stack_use_after_return` is off unless the harness sets it**, so a fix whose only observable is a stale read of a returned frame has no red-before signal in any lane that leaves the default. Find the leak co-located on the same faulty path and assert that instead; leak detection is on whenever ASan is linked, so it is the reliable red-on-unpatched signal.
- **When observation makes the bug vanish, stop observing through I/O.** A timing- or layout-sensitive fault that reproduces under the real harness, exits clean under a debugger, and disappears the moment a `printf` or a verbose dump enters the hot path is being perturbed by the instrument's own syscalls and allocation timing. Record into a preallocated static array with plain stores, and dump it only at the fault from `__asan_set_error_report_callback`, where I/O is free. Carry an invocation counter in each entry: it separates a re-dispatch inside one call from a fresh call seeded by an earlier one, which is the difference between a control-flow bug and a stale-state bug.

`-fsanitize=fuzzer` plus a corpus is the highest-yield tool for any function parsing untrusted bytes. One overnight run finds what a review will not.

## Integer rules

Signed overflow is undefined; the optimizer is entitled to assume it never happens, which is how `if (x + 1 < x)` gets deleted. Unsigned overflow wraps, which is defined and still usually a bug.

- **Check before the operation, never after.** `if (b != 0 && a > SIZE_MAX / b) return ERR;` before `a * b`, or use `__builtin_mul_overflow(a, b, &out)` / `__builtin_add_overflow`. The `b != 0` guard is not optional when `b` is itself derived from input; the division traps otherwise.
- **Every size computed from input is a multiply waiting to wrap.** `malloc(count * sizeof(elem))` with attacker-controlled `count` is the classic heap overflow. Use an overflow-checked helper for every allocation whose size is not a compile-time constant.
- `size_t` is 32-bit on 32-bit builds. A `uint64_t` length field from the wire truncates silently on assignment. Validate against `SIZE_MAX` before narrowing.
- Integer promotion turns `uint16_t * uint16_t` into `int` arithmetic wherever `int` can represent every `uint16_t` value, which is every ordinary 32-bit-`int` target. The product can then overflow *signed* even though both operands were unsigned. Cast one operand to a sufficiently wide unsigned type before multiplying, not after.
- Build with `-Wconversion`. Most truncation bugs announce themselves there and nowhere else.

## Undefined behavior worth memorizing

| Pattern | Fix |
|---|---|
| Type-punning through a cast (`*(float *)&i`) | `memcpy` into the target type; the compiler elides it |
| Unaligned load through a cast pointer | `memcpy`, or a `packed` struct where the ABI guarantees it |
| Shift by a count `>=` the type width, or a negative count | Mask or check the count first |
| Left-shifting a signed value into or past the sign bit | Compute in the unsigned type. Keep the result unsigned, or range-check against the signed maximum before converting: an out-of-range unsigned-to-signed conversion stays implementation-defined through C23, which fixed the *representation* but not this conversion |
| Ordering (`<`, `>`) or subtracting pointers into different objects | Compare integer offsets instead. Equality (`==`, `!=`) between unrelated pointers is well-defined and needs no fix |
| Dereferencing one-past-the-end | Forming that pointer is legal; reading it is not |
| Passing `NULL` to `memcpy`/`memmove` with length 0 | Guard the call; UB even at zero length through C23 (C2y adopts N3322, which defines it) |
| `isalpha(c)` and the rest of `<ctype.h>` on a plain `char` | Cast through `unsigned char`: `isalpha((unsigned char)c)`. Every `ctype` function is defined only for values representable as `unsigned char` or `EOF`; plain `char` has implementation-defined signedness and is signed on x86 and x86-64, so any byte above 0x7F arrives negative. Unsigned-`char` targets such as ARM hide it, which is why this ships |
| Reaching `__builtin_unreachable()` / `std::unreachable()` | Not an assertion. It is a promise to the optimizer, so reaching it is UB on release and the compiler may fold the path into a neighbouring branch. Use `assert(0)` where a check is wanted |
| A non-`volatile` local modified between `setjmp` and `longjmp` | Declare it `volatile`. `-Wclobbered` (which rides on `-Wextra`) flags this, and the diagnostic is **function-scoped**: it covers every non-volatile local in a function that calls `setjmp`, not just statements lexically between the two, so hoisting code out of the guarded block does not silence it |

## Allocation and lifetime

- State ownership at the interface: in the name (`_create` transfers, `_init` does not) and in the contract comment (who frees, and on which paths).
- Check every allocation unless the project's allocator is documented as non-returning on failure.
- `calloc` when the caller will read before writing every field. A `malloc` plus partial init leaks whatever was on the heap into whatever reads it.
- On realloc failure, the original pointer is still valid and must not be leaked: assign to a temporary, check, then commit.
- Set a pointer to `NULL` immediately after freeing it when the containing object outlives the free. A later use-after-free then becomes a NULL deref, which crashes honestly. Note the trade: a double free of the NULLed pointer becomes `free(NULL)`, a defined no-op, so the bug is absorbed silently and ASan can no longer see it. Nulling buys a loud use-after-free at the cost of a quiet double free.
- **Free on exactly one path.** A function that frees a resource on some error paths and hands ownership on to a callee on others is where double frees live. Decompose so the acquiring function is also the sole releasing function, or use the project's `goto cleanup` idiom with one label.
- **A deferred free relocates the free site.** Converting an immediate release into "release when the last holder drops it" moves the free into whatever call drains the deferral, so every caller still holding the pointer across such a call becomes a fresh use-after-free. Grep every caller of the draining functions and ask, per caller, whether it dereferences the same pointer afterwards; pin it across the call using the same counter the deferral already exposes, or re-check through a side channel. The test that proved the original bug reaches a different entry point and will not catch these.
- **A pointer into a container's backing store does not survive a call that can run foreign code.** Caching the base and end of the storage before a walk and then invoking a callback, a destructor, or any user-supplied hook inside the loop is a use-after-free the moment that code inserts into the same container and forces a reallocation. The freed slot usually still reads as plausible bytes, so the visible symptom is merely wrong output and only a sanitizer turns it into a hard failure. Take a reference on the container for the duration of the walk, which also forces a copy-on-write for the aliased case, or re-derive the cursor from an index after every reentrant call. The guard is one refcount pair per container, not per element, so it is not a measurable cost.
- **Pin the elements before iterating a set whose entries the loop can free.** Dropping a refcount inside the walk runs a destructor that can free a different element of the same set. Detach the set from its owner first so a reentrant removal is a no-op against a table nobody can reach, then make three passes: acquire a reference on every element, do the work, release every reference.
- **Unregister from an external registry while the handle is still valid, not at the registrant's own teardown.** Once the descriptor is closed it cannot be re-derived, and removing later by a remembered descriptor number cancels whoever inherited that number in the meantime. A kernel-side registration is the harder case: there is no userspace table to scan for a stale entry, and an interest registered against a descriptor that was later duplicated or inherited stays live after one copy is closed, so the registry keeps handing back a pointer to a freed registrant. Hook the resource's own free path and remove there, and cache the handle and the owning object directly on the registrant rather than re-deriving either at teardown, when the surrounding bookkeeping may already be invalidated.
- **A copy helper that deep-copies conditionally and a destroy helper that frees unconditionally do not compose.** The pair is correct only when the source dies with the copy. Where the source outlives the borrow, the copy shares whatever the condition declined to duplicate and the destroy frees it out from under the source, leaving a dangling field in a live object. Borrow by taking references on the individual owned fields instead of duplicating the aggregate, and save those pointers locally so the release still works if the source itself is destroyed during the call.
- **A container initialized with no element destructor owns nothing, and that is a contract binding every insertion site.** Destroying such a container releases its own storage and leaks every payload the entries point at, and an update against an existing key drops the previous value with no release at all, which is where the dangling alias comes from. The destructor argument and the insert call sites usually live in different files, which is why review misses the combination. Register a destructor, or prove all three: keys never collide, nothing owned is stored, and the container outlives every value in it.
- **When a fix closes a use-after-free, name which allocation was freed early and ask what else that same scenario can free.** "The object was freed" and "the container's storage was reallocated" are different roots needing different guards, and a reference on the object does not cover the reallocation. A regression test covers only the variant its mutation triggers, so removing an element and appending one are not interchangeable: write one test per root, and distrust any note claiming a class of bug is fixed and covered without naming the interleaving it covers.

## Bounds and string handling

- A buffer and its length travel together, buffer first, and the length is a count of bytes with no implied terminator.
- `snprintf` returns the length it *would* have written. `if (n >= sizeof buf)` is the truncation check; ignoring the return silently truncates.
- Never hand `snprintf`'s return value to a length-taking call against the same buffer. Because it is the length that would have been written, an overshoot makes the copy read past the array into adjacent stack memory and emit it, which is a disclosure rather than a formatting defect, and an exact fill copies the embedded terminator into the middle of the output. Clamp to `sizeof buf - 1`, or drop the fixed buffer and append the pieces directly. The shape only fires when a format field can grow, so audit the numeric and string fields fed by parsed values first.
- `strncpy` does not NUL-terminate when the source fills the buffer, and it zero-pads the remainder when it does not. Prefer explicit `memcpy` plus an explicit terminator, or the platform's `strlcpy`.
- Never compute a bound from the data being bounded. Validate the length field against the actual remaining buffer *before* using it to index.
- Classifying a multibyte lead byte proves what the encoder intended, not what is present. A decoder that reads and consumes N continuation bytes on the strength of the lead byte over-reads at a truncated sequence, and because it also advances past bytes that were never there, it steps over the terminator and keeps walking adjacent memory into its own output: a one-byte over-read becomes an unbounded disclosure. Gate each branch on the continuation bytes themselves, left to right, so short-circuit evaluation stops at the terminator, and treat a malformed lead as a single byte rather than emitting a replacement and advancing anyway. Codec bugs cluster, so audit the inverse conversion in the same translation unit before closing the finding.
- When an API carries both a buffer start and a validated-region start, every backward walk floors at the validated one. The bytes below it are exactly the ones the validator refused to certify, so an unbounded back-up that trusts them to be well-formed units runs off the front of the allocation. Compare with `<=` against the floor rather than `==`, because a back-up that decrements before the guard re-evaluates overshoots by one. Fix every backward-walking site and every caller passing a floor in one pass; fixing one re-discovers the rest on the next audit. Where the API has no validated-region concept, the buffer start is the validated floor and the check is already correct.

## Untrusted input

Every parser reading a length-prefixed or nested format needs all five:

1. Validate the length prefix against the bytes actually remaining, before any read.
2. Validate any integer used as a size, index, or count against its real domain, before use.
3. Bound total allocation for one message, not just each field. A million valid 1KB fields is still a memory exhaustion.
4. Bound nesting depth explicitly, with a named constant.
5. Carry every partial token across a chunk boundary in parser state. A lookahead guarded by `i + 1 < len` that falls through to the default branch at the end of a chunk silently reinterprets the next chunk's first byte as ordinary content, and no whole-buffer test reaches it: the input has to be sized so the token straddles the read size exactly.

## Recursion to bounded worklist

Recursion over externally-supplied structure is a stack-exhaustion CVE waiting to be filed: a deeply nested document crashes the process before any length check fires. Convert it.

Two bounds are needed, and conflating them is the usual bug. **Nesting depth** is a property of the path from the root to the current node. **Worklist occupancy** is how many nodes are pending at once, which grows with *breadth*, not depth. A worklist of bare node pointers tracks only occupancy, so using its index as a depth limit rejects a flat tree with many children while letting a deep narrow one through. Carry the depth in the frame:

```c
enum {
	WALK_MAX_DEPTH   = 128,   /* longest root-to-node path */
	WALK_MAX_PENDING = 1024   /* nodes queued at once; bounds stack use */
};

typedef struct {
	node_t *node;
	size_t  depth;            /* 1 at the root */
} walk_frame_t;

/* Visits every node reachable from root. Fails with ERR_DEPTH when the
 * structure nests deeper than WALK_MAX_DEPTH, and ERR_CAPACITY when more
 * than WALK_MAX_PENDING nodes are pending at once. A NULL root visits
 * nothing and succeeds. */
static status_t walk_tree(node_t *root, visitor_fn visit, void *ctx)
{
	walk_frame_t stack[WALK_MAX_PENDING];
	size_t       pending = 0;

	if (root == NULL)
		return OK;

	stack[pending++] = (walk_frame_t){ .node = root, .depth = 1 };
	while (pending > 0) {
		const walk_frame_t frame = stack[--pending];

		status_t s = visit(frame.node, ctx);
		if (s != OK)
			return s;

		if (frame.node->child_count > 0 && frame.depth >= WALK_MAX_DEPTH)
			return ERR_DEPTH;

		for (size_t i = 0; i < frame.node->child_count; i++) {
			if (pending >= WALK_MAX_PENDING)
				return ERR_CAPACITY;
			stack[pending++] = (walk_frame_t){
				.node  = frame.node->children[i],
				.depth = frame.depth + 1,
			};
		}
	}
	return OK;
}
```

The conversion buys three things: stack use is a visible constant rather than a function of input, each limit is a named error instead of a crash, and the loop bound is statically evident. Where either cap must be large, allocate the worklist on the heap and keep both explicit bounds; dropping the occupancy bound just moves the exhaustion from the stack to the heap.

Bounding the walker does not bound the teardown. A depth guard on a recursive dump, encode, or validate says nothing about freeing the structure afterwards, and releasing a deeply nested one recurses on the same stack, so the process dies after every assertion has already passed and the failure looks like a harness fault rather than a missing guard. Free iteratively by unlinking from the head, because dropping the last reference on a linked node can route it to a deferred collector that then recurses anyway. Reproduce it on an ordinary machine with `ulimit -s 1024` instead of waiting for the small-stack platform to report it.

## Verify

- Suite passes under `-fsanitize=address,undefined` with `halt_on_error=1`, zero reports
- Valgrind `--leak-check=full --error-exitcode=1` clean where the suite links under it
- Every allocation size derived from input goes through an overflow-checked computation
- Every length field from untrusted input validated against remaining bytes before use
- No recursion reachable from external input without an explicit depth bound
- `-Wconversion` clean
