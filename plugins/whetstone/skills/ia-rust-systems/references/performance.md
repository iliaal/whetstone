# Hot-Path Performance

Load this reference when profiling shows allocation, copy, or syscall overhead on a hot path. These are optimizations — profile first. `Vec`/`String` on a cold path isn't the bottleneck.

## Reducing hot-path heap allocations

Use stack-or-inline collections when the typical size is small and known:

- `smallvec::SmallVec<[T; N]>` — inline for ≤N items, spills to heap beyond. Good for "usually 1-8 items" cases like parsed tag lists, lookup keys, small event batches.
- `arrayvec::ArrayVec<T, CAP>` — fixed capacity, never heap-allocates. Returns an error when full. Good for bounded message buffers or per-request scratch space.
- String interning for repeatedly-seen strings (enum-like values parsed from config, tenant IDs, route keys): `dashmap::DashMap<String, &'static str>` with `Box::leak` on miss gives `&'static str` comparisons without per-call allocations.

## Zero-copy buffer slicing

`bytes::Bytes` for zero-copy slicing of shared immutable buffers — network parsers, frame decoders, protocol handlers. `BytesMut` for building buffers that `split_to` / `split_off` into `Bytes` without reallocation. Prefer `Bytes` over `Arc<Vec<u8>>` when slicing is the dominant access pattern.

## Vectored writes

`write_vectored` + `std::io::IoSlice` coalesce many buffers — interleaved headers and payloads — into a single syscall when flushing a batch of messages to a socket; the kernel does the gather. Only for measured syscall-bound flush paths; a single `write_all` is fine elsewhere.
