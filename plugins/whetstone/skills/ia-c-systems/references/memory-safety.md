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

## Bounds and string handling

- A buffer and its length travel together, buffer first, and the length is a count of bytes with no implied terminator.
- `snprintf` returns the length it *would* have written. `if (n >= sizeof buf)` is the truncation check; ignoring the return silently truncates.
- `strncpy` does not NUL-terminate when the source fills the buffer, and it zero-pads the remainder when it does not. Prefer explicit `memcpy` plus an explicit terminator, or the platform's `strlcpy`.
- Never compute a bound from the data being bounded. Validate the length field against the actual remaining buffer *before* using it to index.

## Untrusted input

Every parser reading a length-prefixed or nested format needs all four:

1. Validate the length prefix against the bytes actually remaining, before any read.
2. Validate any integer used as a size, index, or count against its real domain, before use.
3. Bound total allocation for one message, not just each field. A million valid 1KB fields is still a memory exhaustion.
4. Bound nesting depth explicitly, with a named constant.

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

## Verify

- Suite passes under `-fsanitize=address,undefined` with `halt_on_error=1`, zero reports
- Valgrind `--leak-check=full --error-exitcode=1` clean where the suite links under it
- Every allocation size derived from input goes through an overflow-checked computation
- Every length field from untrusted input validated against remaining bytes before use
- No recursion reachable from external input without an explicit depth bound
- `-Wconversion` clean
