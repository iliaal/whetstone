# Hot-Path Performance

Load this reference when profiling shows allocation, copy, or syscall overhead on a hot path. These are optimizations; profile first. `Vec`/`String` on a cold path isn't the bottleneck.

## Reducing hot-path heap allocations

Use stack-or-inline collections when the typical size is small and known:

- `smallvec::SmallVec<[T; N]>`: inline for ≤N items, spills to heap beyond. Good for "usually 1-8 items" cases like parsed tag lists, lookup keys, small event batches.
- `arrayvec::ArrayVec<T, CAP>`: fixed capacity, never heap-allocates. Returns an error when full. Good for bounded message buffers or per-request scratch space.
- Intern only a measured repeated vocabulary. For tenant IDs or dynamic route keys, keep reclaimable `Arc<str>` entries and bound both entry count and input length. Serialize lookup/check/insert under one lock when shared across threads; a separate concurrent count check can exceed capacity. Reserve `Box::leak` for a fixed, explicitly bounded process-lifetime vocabulary.

```rust
use std::{collections::HashSet, sync::Arc};

#[derive(Debug, PartialEq, Eq)]
enum InternError { TooLong, Full }

fn intern(
    values: &mut HashSet<Arc<str>>,
    value: &str,
    max_entries: usize,
    max_bytes: usize,
) -> Result<Arc<str>, InternError> {
    if value.len() > max_bytes { return Err(InternError::TooLong); }
    if let Some(existing) = values.get(value) { return Ok(Arc::clone(existing)); }
    if values.len() >= max_entries { return Err(InternError::Full); }
    let entry: Arc<str> = Arc::from(value);
    values.insert(Arc::clone(&entry));
    Ok(entry)
}
```

Clearing or evicting a pool entry releases the pool's reference; the allocation is reclaimed when the last caller drops its `Arc`. Include outstanding callers in the application's memory budget. Verify duplicate reuse, full/oversized rejection, and reclamation after removing an entry and dropping its holders.

## Zero-copy buffer slicing

`bytes::Bytes` for zero-copy slicing of shared immutable buffers: network parsers, frame decoders, protocol handlers. `BytesMut` for building buffers that `split_to` / `split_off` into `Bytes` without reallocation. Prefer `Bytes` over `Arc<Vec<u8>>` when slicing is the dominant access pattern.

## Vectored writes

`write_vectored` + `std::io::IoSlice` coalesce many buffers (interleaved headers and payloads) into a single syscall when flushing a batch of messages to a socket; the kernel does the gather. Only for measured syscall-bound flush paths; a single `write_all` is fine elsewhere.
